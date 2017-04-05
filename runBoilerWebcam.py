#!/usr/bin/python
#
# runBoilerWebcam.py
#
# try to run the trackRft.py.  If it succeeds it'll never return.  If it fails, try it again.
# Started by /etc/rc.local so the software will run indefinitely when the machine is started.

#

import os
import sys
import time
import datetime
import re

print "runBoilerWebcam.py: Starting at {}".format( datetime.datetime.now())

print "runBoilerWebcam.py: Checking for network connection..."
tryAgain = True
while( tryAgain):
    try:
        f = os.popen( "/sbin/ifconfig |grep inet")
        a = f.read()
        print a
        b = re.search( "192\.168\.", a)
        if( b != None):
            tryAgain = False
            print "runBoilerWebcam.py: Found network at {}".format( b.group(0))
        b = re.search( "10\.59\.33", a)
        if( b != None):
            tryAgain = False
            print "runBoilerWebcam.py: Found network at {}".format( b.group(0))
        if( tryAgain):
            print "runBoilerWebcam.py: could not find Network.  Waiting 2 seconds and trying again."
            time.sleep( 2)
    except:
        print "runBoilerWebcam.py: could not find Network.  Waiting 2 seconds and trying again."
        time.sleep( 2)


print "runBoilerWebcam.py: Checking for LifeCam..."
tryAgain = True
while( tryAgain):
    try: 
        f = os.popen( "ls -l /dev/v4l/by-id/*LifeCam*")
        a = f.read()
        print a
        b = re.search( "/video(\d+)\n", a)
        print b.group(1)
        webcamDevNum = int( b.group(1))
        print "runBoilerWebcam.py: found LifeCam at device number {}".format( webcamDevNum)
        tryAgain = False
    except:
        print "runBoilerWebcam.py: could not find LifeCam.  Waiting 2 seconds and trying again."
        time.sleep( 2)

print "runBoilerWebcam.py: Sleeping 5 seconds."
time.sleep(5)

while( 1):
    try:
        os.system( "/home/frc5933/steamworks2017/image-processing/trackRft.py --port 5800 --boiler --webcam")
    except:
        print "runBoilerWebcam.py: Problem at {}.  Waiting 2 seconds and trying again.".format( datetime.datetime.now())
        time.sleep( 2)

print "runBoilerWebcam.py: Done at {}".format( datetime.datetime.now())
