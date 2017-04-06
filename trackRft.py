#!/usr/bin/python
#
# trackRft.py
#
# visually track the retroflective tape targets
# output targeting info L/R, U/D, distance est.
# to UDP socket
#
# read command line parameters
# identify IP broadcast address
# identify USB sources for webcam, RealSense
# set brightness and contrast way down on camera
# read RealSense (1920x1080 at 30fps or 640x480 at 60fps)
#  or webcam (1280x720 at 30fps) or file input (any)
#  or Axis Cam (but not as well tested)
#    (only processes the middle 1/3 of image width, full height of 1920x1080 input, to keep up with 30fps)
#  use multi-threading for reading webcam using threaddedWebcamReader.py
# process for peg or boiler targets by
# hsv thresholding, identifying contours, use
# findTargets.py which uses
# minimum area bouding rectangles to choose contours
# that are approximately the right shape and
# distance apart, calculate L/R, U/D, dist 
# based on centroids of identified targets
#
# other options:
#   set port, IP address for output
#   only process specified number of images
#   write last-processed images to snapshot files
#   print target output to stdout
#   display images on screen
#   write all images to same file, for serving over web (not well tested)
#   write occasional images to snapshot files(not well tested)
#
# uses findTargets.py for
#   algorithms to pick targets from identified contours
# uses threaddedWebcamReader.py
#   to read webcam in its own thread 
#   because it blocks and it's slow
#   and provide image frames
# uses config.py
#   to hold many config parameters
#
# other notes:
#  filters/ignores outlier results in boiler targeting 
#    but this isn't well tested
#  algorithms, and especially parameters in config.py, converged on 
#    using the RealSense 640x480 for peg tracking
#    and using the WebCam 1280x720 for boiler tracking
#

from __future__ import division
import cv2
import numpy as np
import time
import socket
import sys
import os
import re
import math
import threading

# algorithms to pick targets from identified contours
import findTargets 

# config.py holds many config parameters
from config import lower, upper, RS_brightness, pegLower, pegUpper
from config import printDebug, sdTimingThresh

# 
# write snapshot files
#
def writeSnapshotDebug( pOrB, sdNextTime, img, imgMasked, sdLastOutString):
    ts = int( time.time())
    if( ts >= sdNextTime):
        sdNextTime = ts + sdTimingThresh
        cv2.imwrite( "/home/frc5933/steamworks2017/image-processing/calibrationFiles/{}_{}_color.jpg".format( pOrB, ts), img)
        cv2.imwrite( "/home/frc5933/steamworks2017/image-processing/calibrationFiles/{}_{}_mask.jpg".format( pOrB, ts), imgMasked)
        sDfp.write( "{}, {}\n".format( ts, sdLastOutString))
    return sdNextTime

#
# write files in separate thread for serving to web page
#
def imwriteInOwnThread( img):
    cv2.imwrite( "/tmp/pic.jpg", img)

#
# set default parameters
#
inFileName = ''
inDepthFileName = ''
frameLimit = -1
# set to True to show images, False to not
showImages = False
# set to True to print tracking to console, False to not
printToConsole = False
# get this many frames. 
framesToGrab = -1
# frame counter increment.  Set to zero to grab frames endlessly (infinite loop),
#   othersise set to 1
frameCounterInc = 1
# default port, allowed per 2017 Game Manual p. 91, Section 8, rule R65
port = 5800
# default ip - set to local broadcast address
f = os.popen( '/sbin/ifconfig |grep "cast"')
a = f.read()
a = re.search( 'cast[:\s](\d+\.\d+\.\d+\.\d+)', a)
try:
    ip = a.group(1)
except:
    ip = '127.0.0.1'
# use axis or web camera for input
useAxisCam = False
useWebCam = False

# write output files of last images, with target areas inscribed
writeSnapshotFiles = False

# set to True to write boiler webcam images to /tmp/pic.jpg at ~10 FPS
useMjpgStreamer = False
mjpgStreamerCtr = 0

# default realsesne input image dimensions, in pixels
realsenseWidth = 1920
realsenseHeight = 1080
realsenseDepthWidth = 640
realsenseDepthHeight = 480
realsenseFPS = 30

# what to track.  Default = track the peg
trackPeg = True
trackBoiler = False

# keep snapshots while processing, if true
snapshotDebug = False
sdLastOutString = "No targets yet found"

#
# iterate command line parameters
#
i = 0
for a in sys.argv:
    if( a == '--images'): # display images on screen
        showImages = True
    elif( a == '--print'):  # print tracking info to console
        printToConsole = True
    elif( a == '--file'): # process this file instead of camera input
        inFileName = sys.argv[ i+1]
    elif( a == '--limit'): # process this many images
        framesToGrab = int( sys.argv[ i+1])
    elif( a == '--port'):  # write UDP to this port
        port = int( sys.argv[ i+1])
    elif( a == '--ip'): # write UDP to this IP address
        ip = sys.argv[ i+1]
    elif( a == '--axis'): # use axis IP camera
        useAxisCam = True
    elif( a == '--webcam'): # use HD3000 LifeCam on /dev/video3
        useWebCam = True
    elif( a == '--boiler'): # track the boiler instead of the peg
        trackBoiler = True
        trackPeg = False
    elif( a == '--mjpg-streamer'):  # write images to /tmp/pic.jpg to send as web page
        useMjpgStreamer = True
    elif( a == '--snapshots'): # write snapshot file of last image processed
        writeSnapshotFiles = True
    elif( a == '--snapshotDebug'): # write debug snapshot files while running
   	snapshotDebug = True
    elif( a == '--sdTimingThresh'): # write debug snapshot files this many seconds
	sdTimingThresh = int( sys.argv[ i+1])
    elif( a == '--640'): # use realsense 640x480 input, 60 fps
        realsenseWidth = 640
        realsenseHeight = 480
        realsenseDepthWidth = 640
        realsenseDepthHeight = 480 
        realsenseFPS = 60
    i += 1

if len( inFileName) > 0:
    print "Processing input file %s" % ( inFileName)
    framesToGrab = 1
elif( useAxisCam == False and useWebCam == False):
    print "Using RealSense camera for input"

if( framesToGrab < 1):
    framesToGrab = 1
    frameCounterInc = 0

# confirm snapshot debug is set to work, and set it up
if( sdTimingThresh <= 0):
    print "Warning: snapshotDebug timing threshold is {}, which is incorrect. Disabling snapshot debug."
    snapshotDebug = False
if snapshotDebug == True:
    pOrB = "p"
    if( trackBoiler == True):
      pOrB = "b"
    sDfp = open( "/home/frc5933/steamworks2017/image-processing/calibrationFiles/{}_{}_sd.txt".format( pOrB, int( time.time())), "a")
sdNextTime = time.time() - 1000

# import pyrealsense to use RealSense camera
pyrs = None
if( len( inFileName) == 0 and useAxisCam == False and useWebCam == False):
    try:
        import pyrealsense as pyrs
    except:
        pyrs = None


print 'Starting...'

#
# find USB 'address', start the RealSense camera 
#  or Axis IP cam or Microsoft LifeCam webcam
#  or read the input file
#
if pyrs:
    print "Identifying Microsoft LifeCam web cam device number..."
    webcamDevNum = 3
    try:
        f = os.popen( 'ls -l /dev/v4l/by-id/*LifeCam*')
        a = f.read()
        a = re.search( '\/video(\d+)\n', a)
        webcamDevNum = int( a.group(1))
    except:
        pass
    print 'Identifying RealSense device number...'
    try:
        f = os.popen( 'ls -l /dev/v4l/by-id/*RealSense*')
        a = f.read()
        a = re.search( '\/video(\d+)\n', a)
        camDevNum = int( a.group(1))
    except:
        print "Error: Could not find the RealSense.  Exiting."
        exit(-1)

    if( webcamDevNum == 0):
	camDevNum = 1
    else:
	camDevNum = 2

    print "Using RealSense on device {}...".format( camDevNum)
    
    # set the camera brightness way down
    os.system( "/usr/bin/v4l2-ctl -d " + str( camDevNum) + " --set-ctrl brightness={}".format( RS_brightness))

    # start RealSense
    pyrs.start( c_height=realsenseHeight, c_width=realsenseWidth, c_fps=realsenseFPS,
		d_height=realsenseDepthHeight, d_width=realsenseDepthWidth, d_fps=realsenseFPS)
    print "\nSleeping 2..."
    time.sleep(2)
elif( useAxisCam == True):
    print "Using Axis Camera..."
    vc = cv2.VideoCapture()
    print vc.open( "http://10.59.33.48/mjpg/video.mjpg") # ("http:axis-00408c9dccca.local/mjpg/video.mjpg") # 'http://192.168.1.26/mjpg/video.mjpg')
elif( useWebCam == True):
    print "Identifying Microsoft LifeCam web cam device number..."
    try:
        f = os.popen( 'ls -l /dev/v4l/by-id/*LifeCam*')
        a = f.read()
        a = re.search( '\/video(\d+)\n', a)
        webcamDevNum = int( a.group(1))
    except:
        print "Error: Could not find the Microsoft LifeCam.  Exiting."
        exit(-1)

    print "Using LifeCam web cam on device {}, e.g. /dev/video{}...".format( webcamDevNum, webcamDevNum)
    
    vc = cv2.VideoCapture()
    # set brightness to LifeCam's minimum, set auto exposure to manual, set exposure to near minimum
    os.system( "/usr/bin/v4l2-ctl -d " + str( webcamDevNum) + " -c brightness=31,contrast=1,exposure_auto=1,exposure_absolute=5")
    time.sleep(2)
    print vc.open( webcamDevNum)
    vc.read()
    time.sleep(2)
    # set camera capture parameters,
    #  http://stackoverflow.com/questions/11420748/setting-camera-parameters-in-opencv-python
    vc.set( 3, 1280)  # 3 = set width of image capture
    vc.set( 4, 720)   # 4 = set height of image capture
    #vc.set( 10, 5)    # 10 = set brightness of image
    time.sleep(2)

    # using multithreaded camera reading
    import threaddedWebcamReader
    twr = threaddedWebcamReader.threaddedWebcamReader( vc)
    twr.startReadCamLoopThread()
else:
    imgIn = cv2.imread( inFileName) # read the input image from a file
    

# initialize UDP socet
s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt( socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
print( "\nWriting UDP to %s:%s" % ( ip, port))
print( "Output format is:\nLeft-Right from center, Up-Down from center, width in pixels, distance based on width, distance based on height, L/R/C\n")


if frameCounterInc == 1:
    print "Processing %d frames...\n" % ( framesToGrab)
else:
    print "Processing infinite loop...\n"

# tracking peg?  Use pegLower and pegUpper for hsv thresholds
if( trackPeg == True):
    lower = pegLower
    upper = pegUpper

if( useMjpgStreamer == True):
    print "Starting mjpg_streamer. Will display on frc5933-up.local:5802.\nSleeping for 2 seconds.\nNote: You'll have to kill the mjpg_streamer separately."
    os.system( 'LD_LIBRARY_PATH=/usr/local/lib mjpg_streamer -i "input_file.so -f /tmp -n pic.jpg" -o "output_http.so -w /usr/local/www -p 5802"&')
    time.sleep( 2)

#  TODO: confirm if doing this anywhere, or remove
# keep last 3 tracking data so can not write out very bad data points
"""
ctr2targetLRhistL = [0, 0, 0]
histLctr = 0
"""

#
# main loop
#
i = 0
imgNum = None
startTime = time.time() # to report fps processed
distBasedOnCentroidsLast = -1
while( i < framesToGrab):
    #
    # process image
    #
    if(1): # try:
        i += frameCounterInc
        
        if pyrs:  # read color image from RealSense camera
            imgIn = pyrs.get_colour()
        elif( useAxisCam == True): # read color image from Axis 
            retval, imgIn = vc.read()
        elif( useWebCam == True):  # read color image from web camera
 	    # get next available image from threaddedWebcamReader thread
	    if( imgNum != None):
		twr.imgStatusToReady( imgNum)
	    imgNum = None
	    while( imgNum == None):
	        imgNum = twr.getNewestImg()
		time.sleep(0.005)

 	    imgIn = twr.img[ imgNum]
            # retval, imgIn = vc.read()

	    # if using mjpg-streamer, write every 3rd image to /tmp/pic.jpg
	    if( useMjpgStreamer == True):
	        mjpgStreamerCtr +=1 
 	        if( mjpgStreamerCtr > 2):
		    mjpgStreamerCtr = 0
		    imwriteinownthread = threading.Thread( target=imwriteInOwnThread, args=(imgIn,))
		    imwriteinownthread.start()
		    #cv2.imwrite( "/tmp/pic.jpg", imgIn)

        imgH, imgW = imgIn.shape[:2]
        
        # only process the middle 1/3 of image width, full height.
	#  for 1080p input.  Leave 640x480 alone.
	widthMult = 1
    if( imgW > 1280): # processing 1920x1080 (1080p)
        img = imgIn[ 0:imgH, int(imgW/3.0) : int(imgW*2.0/3.0)]
    elif( imgW > 640):  # processing 1280x720 (720p)
	img = imgIn
        widthMult = 1/2.0
    else:  # processing 640x480
        img = imgIn
        widthMult = 1.0/3.0
    imgH, imgW = img.shape[:2]
        
    hsv = cv2.cvtColor( img, cv2.COLOR_BGR2HSV)

    # Threshold the HSV image to get mask of  desired colors
    mask = cv2.inRange( hsv, lower, upper)
    if( writeSnapshotFiles):
        cv2.imwrite( 'colorMasked.jpg', mask)
    if( snapshotDebug == True):
	imgMasked = mask.copy()
    
    # find contours in the masked image, which is black and white
    contours, hierarchy = cv2.findContours( mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # no contours? nothing to do!
    if( contours == None or len( contours) == 0):
        # write tracking instructions to socket
        outString = "No contours: -1, -1, -1, -1, C"
        if printToConsole: 
            print outString
        s.sendto( outString, ( ip, port))
	if( snapshotDebug == True):
	    sdNextTime = writeSnapshotDebug( pOrB, sdNextTime, img, imgMasked, sdLastOutString)
        continue
            
    if(1): # try:
        #
        # find LIFT PEG target retroflective tape
        #
        if( trackPeg == True):
            # construct the list of vertical bounding boxes
	    #  boundinRect() retuns the list [ x, y, w, h] with x,y the upper left corner
            boundingBoxes = [cv2.boundingRect(c) for c in contours]
        
            # sort them from bottom to top.  
	    #  Set reverse=False to sort top to bottom.
            (contours, boundingBoxes) = zip(*sorted(zip(contours, boundingBoxes), key=lambda b:b[1][1], reverse=True))

            # except:
            #continue
        
            ctr2targetLR, ctr2targetUD, outDistW, outDistH, trackDir, r, centroidTargetLR, centroidTargetUD, distBasedOnCentroids = findTargets.findPegCentroids( boundingBoxes, contours, imgW, imgH)
            outString = "Peg target "
            

        #
        # find BOILER target retroflective tape
        #
        if( trackBoiler == True):
            # construct the list of vertical bounding boxes
	    #  minAreaRect() returns [( x,y), ( w,h), angle]
            boundingMinRects = [cv2.minAreaRect(c) for c in contours]
            # sort them from top to bottom.  
	    #  Set reverse=True to sort bottom to bottom.
            (contours, boundingMinRects) = zip(*sorted(zip(contours, boundingMinRects), key=lambda b:b[1][1], reverse=False))

            if printDebug:
		print "bounding minimum rectangles:"
		for bmr in boundingMinRects:
		    print bmr
		print "----"

	    # use minimum area rectangles to find the target
	    # compute center of target and distances by computing centroids
            ctr2targetLR, ctr2targetUD, outDistW, outDistH, trackDir, r, centroidTargetLR, centroidTargetUD, distBasedOnCentroids = findTargets.findBoilerCentroids( boundingMinRects, contours, imgW, imgH)
            outString = "Boiler target "
            
	#
        # report target info
	#   report -1 if no target found
	#   suppress obviously erroneous results and report -2
	#
        if( ctr2targetLR == None):
            outString += "not found: -1, -1, -1, -1, -1, C"
	    distBasedOnCentroidsLast = -1
	    # write snapshot debug image files and text
	    if( snapshotDebug == True):
		sdNextTime = writeSnapshotDebug( pOrB, sdNextTime, img, imgMasked, sdLastOutString)
	# target found; check validity of new target find vs last one
	elif( distBasedOnCentroidsLast < 0 or ( distBasedOnCentroids < distBasedOnCentroidsLast * 2 and distBasedOnCentroids > distBasedOnCentroidsLast * 0.5)):
	    # good find. report target info from centroids
            outString += "with raw pixel box info {} {} {} {} at: {: 8.2f}, {: 8.2f}, {: 8.2f}, {: 8.2f}, {: 8.2f}, {:s}".format( r[0], r[1], r[2], r[3], centroidTargetLR * widthMult, centroidTargetUD, r[3], distBasedOnCentroids, distBasedOnCentroids, trackDir)

	    # save output string, to add to snapshot debug info
	    if( snapshotDebug == True):
	        sdLastOutString = str( round( time.time(), 3)) + ", " + outString

	    distBasedOnCentroidsLast = distBasedOnCentroids
	# target found but not valid based on last target
	else:
            outString += "with raw pixel box info {} {} {} {} but invalid centroid distance of {: 8.2f}: -2, -2, -2, -2, -2, C".format( r[0], r[1], r[2], r[3], distBasedOnCentroids)
	    distBasedOnCentroidsLast = -2
	    # write snapshot debug image files and text
	    if( snapshotDebug == True):
		sdNextTime = writeSnapshotDebug( pOrB, sdNextTime, img, imgMasked, sdLastOutString)

	# end if/else target found or not

    # end if(1), or try

    #
    # draw target areas and display
    #
    if( showImages):
        cv2.imshow( 'input color image', img)
        cv2.imshow( 'contours', mask)
        
    if( showImages or writeSnapshotFiles):
        # draw box around and circle center of target on image
        if( r != None):
            # draw box
            cv2.rectangle( img, (r[0],r[1]), (r[0]+r[2],r[1]+r[3]), (0,255,0), 2)
            # draw circle in center of target
            cv2.circle(img, (int(r[0]+r[2]/2),int(r[1]+r[3]/2)), 5, (0,0,255))
        
    if( showImages):
        cv2.imshow('input color image with targets',img)

    if printToConsole:
        print outString

    # write tracking instructions to socket
    if( outString == ''): outString = "-1, -1, -1, -1, C"
    s.sendto( outString, ( ip, port))

# end while( i < framesToGrab)

if( useWebCam == True):
    twr.imgStatusToReady( imgNum)
    twr.stopReadCamLoopThread()
    time.sleep( 0.07)

if( useAxisCam == True or useWebCam == True):
	vc.release()

print "Done. Processing rate was: %d fps" % ( framesToGrab / (time.time() - startTime))

if( snapshotDebug == True):
    sDfp.close()

if( writeSnapshotFiles):
    print "Saving last set of captured images..."
    cv2.imwrite( 'colorWithTargets.jpg', img)
    cv2.imwrite( 'colorWithContours.jpg', mask)

if( showImages):
    cv2.waitKey(0)
    cv2.destroyAllWindows()



