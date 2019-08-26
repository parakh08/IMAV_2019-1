import numpy as np
from djitellopy import Tello
import cv2
import imutils as im
from time import sleep     

import image_pb2

import zmq
import random
import sys
import time
import asyncio
import time

def fire_and_forget(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, *kwargs)

    return wrapped

@fire_and_forget
def velCallbaack(socks):
    while 1:
        data = socks.recv()
        rl = image_pb2.vel()
        rl.ParseFromString(data)
        print("vel: ", rl.vx, rl.vy, rl.vz, rl.rz)
        print("")

port = "5556"
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:%s" % port)


socket2 = context.socket(zmq.SUB)
socket2.bind("tcp://*:%s" % 5557)
socket2.setsockopt(zmq.SUBSCRIBE, bytes([]))

socket3 = context.socket(zmq.PUB)
socket3.bind("tcp://*:%s" % 5558)


velCallbaack(socket2)

imf = image_pb2.image()
dep = image_pb2.depth_m()
tello = Tello()
tello.connect()
tello.streamoff()
tello.streamon()

capture = tello.get_video_capture()
 
while 1:
    ret, frame = capture.read()
    frameBGR = np.copy(frame)
    frame2use = im.resize(frameBGR,width=720)
    imf.width = 720
    imf.height = frame2use.shape[0]
    imf.image_data  = frame2use.tobytes()
    data = imf.SerializeToString()
    socket.send(data)
    try:
        dep.d = float(tello.get_h())
        data = dep.SerializeToString()
        socket3.send(data)

    except Exception as e:
        print(e)
        pass
    cv2.imshow("haha",frame2use)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    #sleep(1/25)
tello.end()
capture.release()
cv2.destroyAllWindows()
tello.streamoff()

