from djitellopy import Tello
import cv2
import pygame
from pygame.locals import *
import numpy as np
import time
import imutils as im

from orient_yaw import Orient as orient

# Speed of the drone
S = 60
# Frames per second of the pygame window display
FPS = 25

font = cv2.FONT_HERSHEY_COMPLEX


class FrontEnd(object):
    """ Maintains the Tello display and moves it through the keyboard keys.
        Press escape key to quit.
        The controls are:
            - T: Takeoff
            - L: Land
            - Arrow keys: Forward, backward, left and right.
            - A and D: Counter clockwise and clockwise rotations
            - W and S: Up and down.
    """

    def __init__(self,tello):
        # Init pygame
        # Init Tello object that interacts with the Tello drone
        self.tello = tello
        self.telloEulerAngles = np.zeros((1,3))

        self.rcOut=np.zeros(4)
        
        self.R = np.zeros((3,3))
        self.PoseFlag = 1
        self.ar = 0

        self.ARmean = np.array([0])
        self.ARqueue = np.zeros((7,1))

        self.telloPose = np.zeros((1,3))
        self.poseQueue = np.zeros((7,3))
        self.telloPoseVariance = np.zeros(3)
        self.telloPoseMean = np.zeros(3)
        self.telloPoseMean15 = np.zeros(3)
        
        self.cntErNrm = 0
        self.cntError = np.array([0,0,0])
        
        self.tello.TIME_BTW_RC_CONTROL_COMMANDS = 20

        self.frameCenter = np.zeros((1,2))


        # variables for shelf passing
        self.trigger = 0
        self.lastValue = 0
        self.lastValue1 = 0
        self.lastValue2 = 0
        self.lastValue3 = 0
        self.flag1 = 1
        self.distanceFrmRect = 0
        self.apprchFlowFlag =0
        self.passFromWindowModSccss = 0

        #variables for aligning with the window
        self.alnFlowFlag = 0
        self.alnFlowFlag2 = 0

        self.centerCounter = 0
        self.c = 0
        # self.telloPose = np.array([])
            # self.telloEulerAngles = EulerAngles

        self.orient = orient(self.tello)

    def run(self,yaw):

        self.orient.orient(yaw)

        frame_read = self.tello.get_frame_read()
        print("reached align_rect")

        should_stop = False

        Height = 100
        i=0
        # yaw = self.tello.get_yaw()
        while not should_stop:
            print(i)
            i=i+1
            if frame_read.stopped:
                frame_read.stop()
                break

            key,dst,mask = self.preproccessAndKey(frame_read)

            trigger = self.stateTrigger(key,"p")
            if 1:
                self.takeoffToShelf(trigger,key,mask,dst,yaw)
            else :
                self.manualRcControl(key)
                pass

            self.sendRcControl()

            cv2.imshow("rectified",dst) 
            # print(self.lastValue3)

            if key == ord("q"):
                break
            if key == ord("t"):
                try:
                    self.tello.takeoff()   
                except:
                    print("lol")    
            if key == ord("l"):
                self.tello.land()
                Height = 100

            if self.lastValue3 == 1:
                print("now exiting")
                cv2.destroyWindow("msk")
                cv2.destroyWindow("rectified")
                cv2.destroyWindow("Frame")
                return 1
                # break

            time.sleep(1 / FPS)

        # Call it always before finishing. I deallocate resources.
        # self.tello.end()

    def takeoffToShelf(self,trigger,key,mask,dst,yaw):
        frameH,frameW,arSet = 6,16,0.15
        cv2.imshow("msk",mask)
        self.PoseEstimationfrmMask(mask,dst,frameH,frameW,arSet)
        self.manualRcControl(key)
        trig = self.slideAndSearchRect(key)
        trig = self.interMtrigger(trig)
        trig = self.algnToFrame(trig,key,yaw)
        # print "Trigger",trig
        trig = self.interMtrigger3(trig)
        # self.algToSqr(trig,key)
        
        result = 0
        return result

    def clear(self):
        
        self.telloEulerAngles = np.zeros((1,3))

        self.rcOut=np.zeros(4)
        
        self.R = np.zeros((3,3))
        self.PoseFlag = 1
        self.ar = 0

        self.ARmean = np.array([0])
        self.ARqueue = np.zeros((7,1))

        self.telloPose = np.zeros((1,3))
        self.poseQueue = np.zeros((7,3))
        self.telloPoseVariance = np.zeros(3)
        self.telloPoseMean = np.zeros(3)
        self.telloPoseMean15 = np.zeros(3)
        
        self.cntErNrm = 0
        self.cntError = np.array([0,0,0])
        
        self.tello.TIME_BTW_RC_CONTROL_COMMANDS = 20

        self.frameCenter = np.zeros((1,2))


        # variables for shelf passing
        self.trigger = 0
        self.lastValue = 0
        self.lastValue1 = 0
        self.lastValue2 = 0
        self.lastValue3 = 0
        self.flag1 = 1
        self.distanceFrmRect = 0
        self.apprchFlowFlag =0
        self.passFromWindowModSccss = 0

        #variables for aligning with the window
        self.alnFlowFlag = 0
        self.alnFlowFlag2 = 0


    def slideAndSearchRect(self,key):
        thresh = 200
        speed = 20

        # print "aspectRatio",self.ARmean[0]

        # print "self.PoseFlag",self.PoseFlag

        con = self.ARmean[0] > 0.25
        con = con*1
        # print "con",con
        trig = self.interMtrigger2(con)

        if self.PoseFlag == 1 and con: 
            self.manualRcControl(key)
            return 1

        else :
            self.rcOut[0] = -20
            self.rcOut[1] = 0
            self.rcOut[2] = 0
            self.rcOut[3] = 0

            return 0


    def stateTrigger(self,key,char):
        if key == ord(char):
            value = 1
        else:
            value = 0

        trigger = value - self.lastValue
        self.lastValue = value

        return trigger 
    def interMtrigger(self,val):
        if val == 1:
            value = 1
        else:
            value = 0

        trigger = value - self.lastValue1
        self.lastValue1 = value

        return trigger

    def interMtrigger2(self,val):
        if val == 1:
            value = 1
        else:
            value = 0

        trigger = value - self.lastValue2
        self.lastValue2 = value

        return trigger

    def interMtrigger3(self,val):
        if val == 1:
            value = 1
        else:
            value = 0

        trigger = value - self.lastValue3
        self.lastValue3 = value

        return trigger

    
    def algnToFrame(self,val,key,yaw):
        # print "key",key,"Flag",self.alnFlowFlag
        if val == 1:
            self.alnFlowFlag = 1
            self.cntErNrm = 0
            
        if self.alnFlowFlag == 1:
            # print ("yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy")
            # print "ya1"
            # print "self.cntErNrm",self.cntErNrm

            if self.cntErNrm > 8 or self.cntErNrm ==0:
                # print "Norm ",self.cntErNrm
                
                self.PoseController(key,35,0,15,0.39)
                self.alnFlowFlag = 1
                # print "self.cntErNrm",self.cntErNrm
                if self.centerCounter > 16 and self.centerCounter < 180:                                # to update
                    self.rcOut = [0,-20,0,0]

                # print "ya2"
                return 0
            else:
                # print "self.cntErNrm",self.cntErNrm
                # print "ya3"
                self.alnFlowFlag = 0
                return 0
            if self.cntErNrm < 10 and self.cntErNrm != 0:
                self.alnFlowFlag = 0
                # print "self.cntErNrm",self.cntErNrm
                
                # print "ya4"
                return 1
            else:
                # print "self.cntErNrm",self.cntErNrm

                # print "ya5"
                return 0 
        else:
            if self.cntErNrm < 10 and self.cntErNrm != 0:
                # print "self.cntErNrm",self.cntErNrm
                # print "ya6"
                self.orient.orient(yaw)
                return 1
            else:
                # print "ya5"
                return 0

    def preproccessAndKey(self,frame_read):
        frameBGR = np.copy(frame_read.frame)
        frame2use = im.resize(frameBGR,width=720)
            
        frame = frame2use 

        key = cv2.waitKey(1) & 0xFF;

        dst = self.rectifyInputImage(frame2use)            
        mask = self.getRectMask(dst)

        return key,dst,mask

    def algnYawToFrame(self,key):
        pass
    def findMissingFrame(self,key):
        pass
    def shoot(self,key):
        pass

    def manualRcControl(self,key):
        if key == ord("w"):
            self.rcOut[1] = 50
        elif key == ord("a"):
            self.rcOut[0] = -50
        elif key == ord("s"):
            self.rcOut[1] = -50
        elif key == ord("d"):
            self.rcOut[0] = 50
        elif key == ord("u"):
            self.rcOut[2] = 50
        elif key == ord("j"):
            self.rcOut[2] = -50
        else:
            self.rcOut = [0,0,0,0]

        return

    def sendRcControl(self):
        # print "rcOut", self.rcOut
        self.tello.send_rc_control(int(self.rcOut[0]),int(self.rcOut[1]),int(self.rcOut[2]),int(self.rcOut[3]))
        self.rcOut = [0,0,0,0]

        return

    def rectifyInputImage(self,frame2use):

# 0.000000000000000000e+00,0.000000000000000000e+00,1.000000000000000000e+00
        K = np.array([[7.092159469231584126e+02,0.000000000000000000e+00,3.681653710406367850e+02],[0.000000000000000000e+00,7.102890453175559742e+02,2.497677007139825491e+02],[0.000000000000000000e+00,0.000000000000000000e+00,1.000000000000000000e+00]])
        dist = np.array([2.439122447395965926e-02,-1.174125872015051447e-01,-7.226737851943197850e-03,-2.109186754013973528e-03,6.156184110527554987e-01])
        K_inv = np.linalg.inv(K)

        h , w = frame2use.shape[:2]

        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(K,dist,(w,h),1,(w,h))

        mapx,mapy = cv2.initUndistortRectifyMap(K,dist,None,newcameramtx,(w,h),5)
        dst = cv2.remap(frame2use,mapx,mapy,cv2.INTER_LINEAR)

        x,y,w,h = roi
        dst = dst[y:y+h,x:x+w]

        return dst

    def getRectMask(self,frame):

        kernel = np.ones((5,5),np.uint8)#param 1

        blurred = cv2.GaussianBlur(frame, (7, 7), 0)#param 1

        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        h,s,v = cv2.split(hsv)

        dilS = cv2.dilate(s,kernel,iterations = 1)
        newS = dilS-s
        newS = cv2.equalizeHist(newS)
        # newS = cv2.GaussianBlur(newS, (11, 11), 0)


        dilV = cv2.dilate(v,kernel,iterations = 1)#param 1
        newV = dilV-v
        newV = cv2.equalizeHist(newV)

        dilH = cv2.dilate(h,kernel,iterations = 1)
        newH = dilH-h
        newH = cv2.equalizeHist(newH)


        sabKaAnd = cv2.bitwise_or(newS,newV)
        kernel2 = np.ones((3,3),np.uint8)#param 1
        sabKaAnd = cv2.erode(sabKaAnd,kernel2,iterations = 1)#param 1
        sabKaAnd = cv2.erode(sabKaAnd,kernel2,iterations = 1)#param 1

        sabKaAnd = cv2.dilate(sabKaAnd,kernel2,iterations = 1)#param 1
        sabKaAnd = cv2.GaussianBlur(sabKaAnd, (11, 11), 0)

        maskSab = cv2.inRange(sabKaAnd,120,255)#param 1****

        maskSab = cv2.erode(maskSab,kernel2,iterations = 1)
        maskSab = cv2.dilate(maskSab,kernel2,iterations = 1)

        maskSab = cv2.bitwise_and(maskSab,newV)
        maskSab = cv2.equalizeHist(maskSab)
        maskSab = cv2.inRange(maskSab,190,255)# param *****

        kernel2 = np.ones((2,2),np.uint8) #param ****
        maskSab = cv2.erode(maskSab,kernel2,iterations = 1)
        maskSab = cv2.dilate(maskSab,kernel2,iterations = 1)

        return maskSab
        
    def PoseEstimationfrmMask(self,mask,frame,frameH,frameW,arSet):

        print("pose estimation....")
        # Contours detection
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        oldArea = 300
        for cnt in contours:
            area = cv2.contourArea(cnt)
            approx = cv2.approxPolyDP(cnt, 0.012*cv2.arcLength(cnt, True), True) # 0.012 param
            x = approx.ravel()[0]
            y = approx.ravel()[1]

            

            if area > 300:#param
                # if len(approx) == 3:
                    # cv2.putText(frame, "Triangle", (x, y), font, 1, (0, 0, 0))
                if len(approx) == 4:
                    
                    ar = (np.linalg.norm(approx[0] - approx[1]) + np.linalg.norm(approx[2] - approx[3]))/(np.linalg.norm(approx[2]-approx[1])+np.linalg.norm(approx[0]-approx[3]))
                    if ar > 1:
                        ar=1/ar

                    hull = cv2.convexHull(cnt)
                    hull_area = cv2.contourArea(hull)
                    solidity = float(area)/hull_area

                    # print "Angle",angle
                    # print "solidity",solidity
                    # print "ar",ar
                    condition = ar < 0.4 and ar > 0.25
                    if solidity > 0.95 and condition:

                        self.ar = ar
                        # print "ar",self.ar

                        self.ARqueue = np.roll(self.ARqueue,1,axis = 0)
                        self.ARqueue[0,:] = [ar]

                        self.ARvar = np.var(self.ARqueue,axis=0)
                        self.ARmean = np.mean(self.ARqueue,axis = 0)

                        if area > oldArea:
                            cv2.drawContours(frame, [approx], 0, (0, 0, 0), 5)
                            #cv2.circle(frame,(int(cx),int(cy)), 3, (0,0,255), -1)
                            cv2.putText(frame, "Rectangle", (x, y), font, 1, (0, 0, 0))

                            cntMain = approx
                            rect = self.order_points(cntMain)
                            # print "rect",rect
                            
                            Pose = self.PoseEstimation(rect,frameH,frameW)
                            if self.PoseFlag == 1:
                                self.c = 1
                                self.centerCounter = 0
                                # print "PoseFlag",self.PoseFlag
                                self.telloPose = np.transpose(Pose)

                                self.poseQueue = np.roll(self.poseQueue,1,axis = 0)
                                self.poseQueue[0,:] = [Pose[0,0],Pose[0,1],Pose[0,2]]

                                self.telloPoseVariance = np.var(self.poseQueue,axis=0)
                                self.telloPoseMean = np.mean(self.poseQueue,axis = 0)
                                # print "PoseQueue",self.poseQueue
                                # print "PoseMean",self.telloPoseMean
                                # print "telloPoseVariance" , self.telloPoseVariance
                            varN = np.linalg.norm(self.telloPoseVariance)
                            oldArea =area
                    else:
                        if self.c == 1:
                            self.centerCounter = self.centerCounter + 1
                            # print "frameCenter",self.frameCenter 
                            # print "centerCounter",self.centerCounter  

        cv2.imshow("Frame", frame)
        #cv2.imshow("Mask", mask)

    

    def PoseEstimation(self,rect,frameH,frameW):

        K = np.array([[6.981060802052014651e+02,0.000000000000000000e+00,3.783628172155137577e+02],[0.000000000000000000e+00,6.932839845949604296e+02,2.823973488087042369e+02],[0.000000000000000000e+00,0.000000000000000000e+00,1.000000000000000000e+00]])
        # dist = np.array([-1.428750372096417864e-01,-3.544750945429044758e-02,1.403740315118516459e-03,-2.734988255518019593e-02,1.149084393996809700e-01])

        # K = np.array([[6.331284731799049723e+02,0.000000000000000000e+00,3.240546706735938187e+02],[0.000000000000000000e+00,6.276117931324869232e+02,2.404437048001034611e+02],[0.000000000000000000e+00,0.000000000000000000e+00,1.000000000000000000e+00]])
        K_inv = np.linalg.inv(K)
        crn = rect

        # print "crn",crn
        # crnVect = np.array([[crn[0]],[crn[1]],[1]])

        crnList = rect

        frameH = frameH/2 
        frameW = frameW/2

        src = np.array([[-1*frameH,-1*frameW],[frameH,-1*frameW],[frameH,frameW],[-1*frameH,frameW]])

        h, status = cv2.findHomography(src,crnList)

        det = np.linalg.det(h)

        if det != 0 :
            self.PoseFlag=1
            # print "PoseFlag flag changed"

            hInv = np.linalg.inv(h)

            h1h2h3 = np.matmul(K_inv,h)

            h1T = h1h2h3[:,0]
            h2T = h1h2h3[:,1]
            h3T = h1h2h3[:,2]
            

            h1Xh2T = np.cross(h1T,h2T)


            h1_h2_h1Xh2T = np.array([h1T,h2T,h1Xh2T])
            h1_h2_h1Xh2 = np.transpose(h1_h2_h1Xh2T)

            u, s, vh = np.linalg.svd(h1_h2_h1Xh2, full_matrices=True)

            uvh = np.matmul(u,vh)
            det_OF_uvh = np.linalg.det(uvh)

            M = np.array([[1,0,0],[0,1,0],[0,0,det_OF_uvh]])

            T = h3T/np.linalg.norm(h1T) # Translation Matrix
            r = np.matmul(u,M)
            R = np.matmul(r,vh) # Rotation matrix

            T_t = np.reshape(T,(3,1))
            neg_Rt_T = -1*np.dot(R.T,T_t)
            f = np.array([[0,0,0,1]])

            
            if neg_Rt_T[2,0] < 0:
                flag = -1
            else:
                flag = 1

            neg_Rt_T[2,0] = neg_Rt_T[2,0]*flag
            neg_Rt_T[0,0] = neg_Rt_T[0,0]*(-1)
            Pose = neg_Rt_T.T

            pX = Pose[0,0]
            pY = Pose[0,1]
            pZ = Pose[0,2]

            Pose[0,0] = pZ
            Pose[0,1] = -pX
            Pose[0,2] = -pY


        else:
            self.PoseFlag=0            
            Pose = np.array([[0,0,0]])

        return Pose


    def PoseController(self,key,xSetPt,ySetPt,zSetPt,kp):
        varN = np.linalg.norm(self.telloPoseVariance)
        # print "varN",varN
        Pose = self.telloPoseMean

        xEr = xSetPt - Pose[0]   
        yEr = ySetPt - Pose[1]
        zEr = zSetPt - Pose[2]

        self.cntError = np.array([xEr,yEr,zEr])
        norm = np.linalg.norm([xEr,yEr,zEr])
        self.cntErNrm = norm


        # if key == ord("e"): #press e to execute
        if True:
            if True: # put additional commands here
                
                MtnCmd = np.array([kp*xEr,kp*yEr,kp*zEr])

                MtnCmd[0] = -1*MtnCmd[0]
                self.rcOut = [MtnCmd[1], MtnCmd[0],MtnCmd[2],0]

                if self.rcOut[0] > 35:
                    self.rcOut[0] = 35
                elif self.rcOut[0] < -35:
                    self.rcOut[0] = -35

                if self.rcOut[1] > 35:
                    self.rcOut[1] = 35
                elif self.rcOut[1] < -35:
                    self.rcOut[1] = -35

                if self.rcOut[2] > 35:
                    self.rcOut[2] = 35
                elif self.rcOut[2] < -35:
                    self.rcOut[2] = -35

                # print "rcOut Inside", self.rcOut

        else :
            self.manualRcControl(key)

    def order_points(self,pts):

        pts = pts.reshape(4,2)
        # initialzie a list of coordinates that will be ordered
        # such that the first entry in the list is the top-left,
        # the second entry is the top-right, the third is the
        # bottom-right, and the fourth is the bottom-left
        rect = np.zeros((4, 2), dtype = "float32")
     
        # the top-left point will have the smallest sum, whereas
        # the bottom-right point will have the largest sum
        s = pts.sum(axis = 1)
        # print "dim",pts.shape
        # print "s",s 
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
     
        # now, compute the difference between the points, the
        # top-right point will have the smallest difference,
        # whereas the bottom-left will have the largest difference
        diff = np.diff(pts, axis = 1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
     
        # return the ordered coordinates
        return rect

def main():
    tello = Tello()
    frontend = FrontEnd(tello)

    yaw = tello.get_yaw()
    # run frontend
    frontend.run(yaw)


if __name__ == '__main__':
    main()

