#
# config.py
#
# constants, fixed values

from __future__ import division
import numpy as np
import math

# port settings are expected by the RIO to be:
# Boiler at 5800
# Peg at 5801

# print helpful stuff or not
printDebug = False
# save snapshots while running, up to one every this many seconds
sdTimingThresh = 9

# define brightness value, to set 'exposure' on RealSense RGB camera
RS_brightness = 5

# which camera using for tracking RFT, 
#  either 'RealSense_640_480' or 'LifeCam_1280_720'
boilerCam = 'LifeCam_1280_720' # camera pointed at boiler
pegCam = 'RealSense_640_480' # cam pointed at peg

#
# define the color thresholds for isolating (masking) the target
#
# OpenCV uses ranges: hue 0-180, sat 0-255, val 0-255
# gimp uses ranges H = 0-360 degrees, S = 0-100% and V = 0-100%
# in Java OpenCV define the thresholds as: Scalar(0,0,80), new Scalar(240, 255, 255)
#
# white and/or very bright
lower = np.array([ 0, 0, 220])
upper = np.array([ 256, 110, 256])

# calibrating 2/20/17, white spotlight with lens, boiler, webcam
lower = np.array([ 0, 0, int( .80*255)])
upper = np.array([ 256, int( 0.5*255), 256])

# calibrating 2/24/17, white spotlight with lens, boiler, webcam
lower = np.array([ 0, 0, int( .40*255)])
upper = np.array([ 256, int( 0.25*255), 256])

# calibrating 2/25/17, white spotlight no lens, boiler, webcam
lower = np.array([ 0, 0, int( .20*255)])
upper = np.array([ 256, int( 0.30*255), 256])

# calibrating 2/25/17, white spotlight no lens, boiler, webcam, 16' from Rft
#  take HSV numbers from Gimp Color Picker and put in as first coefficient
lower = np.array([ round( 205*179.0/359.0), round( 0.25*255), round( 0.25*255)])
upper = np.array([ round( 245*179.0/359.0), round( 0.60*255), round( 0.50*255)])
# 15'
lower = np.array([ round( 200*179.0/359.0), round( 0.20*255), round( 0.25*255)])
upper = np.array([ round( 245*179.0/359.0), round( 0.60*255), round( 0.50*255)])
# 14'
lower = np.array([ round( 190*179.0/359.0), round( 0.00*255), round( 0.25*255)])
upper = np.array([ round( 245*179.0/359.0), round( 0.60*255), round( 0.50*255)])
# 13'
lower = np.array([ round( 0*179.0/359.0), round( 0.00*255), round( 0.10*255)])
upper = np.array([ round( 359*179.0/359.0), round( 0.60*255), round( 0.60*255)])

# calibration 3/9/17
lower = np.array([ round( 80*179.0/359.0), round( 0.20*255), round( 0.05*255)])
upper = np.array([ round( 200*179.0/359.0), round( 1.10*255), round( 0.40*255)])



#
# constants for identifying the LIFT PEG target retroflective tape
#

# calibrating 2/23 and 3/7/17, green LEDs, peg, RealSense
#  take HSV numbers from Gimp Color Picker and put in as first coefficient
pegLower = np.array([ round( 50*179/359.0), round( 0.5*255), round( 0.35*255)])
pegUpper = np.array([ round( 120*179/359.0), round( 1.1*255), round( 1.0*255)])


# number of pixels 'close enought' to on target
#  when the target is within (+/-) this many pixels of center the UDP and printout
#  will end in 'C' instead of 'L' or 'R'
pegCloseToCenter = 2

# L/R pixels from center of image where we want the peg target to be
#  when it's 'on target,' i.e. it's where the center of the gear handler hits
#  negative for left of center
pegCenterCalibration = 0

#  RealSense depth map is always 640w x 480h
#  640w x 480h FOV is 59deg w x 46deg h
#  see Alex's email to Jon 10/24/16, search on 'isosceles'
#  height of field of view of RealSense at distance d is
#  h = 2 * d * sin( 23deg) / sin( 67deg)
#    d = h / (2*sin()/sin())

# peg target RFT is two strips, each 5" tall and 2" wide,
#  outside perimeter around both is 10.25"
# so peg target height in pixels  = 5" * 480 * / h
#    h = 5*480/pegHeightPix
#    so d = (5*480)/(2*sin(23)/sin(67)) / pegHeightPix
#  pegCam is set at top of this file
if( pegCam == 'RealSense_640_480'):
    # pegPixHeightToDist = 5 * 480 / ( 2 * math.sin( 23 * math.pi/180) / math.sin( 67 * math.pi/180))
    # calibrating 2/23/17.  Is within +/- 3% if greater than 36"; about 10% off if < 36"
    pegPixHeightToDist = 3500.0
    #  target width in pixels  = 10.25" * 640 / ( 2 * d * sin( 29.5deg) / sin( 60.5deg))
    #pegPixWidthToDist = 2.0 * 640 / ( 2 * math.sin( 29.5 * math.pi/180) / math.sin( 60.5 * math.pi/180))
    # calibrating 2/23/17
    pegPixWidthToDist = 2*6774.0 / 10.25

elif( pegCam == 'LifeCam_1280_720'):
    # target pix/dist ratio for LifeCam webcam 1280x720:
    #   61deg horizontal by 34.3deg vertical
    pegPixHeightToDist = 5 * 720 / ( 2 * math.sin( 34.3/2 * math.pi/180) / math.sin( (90-34.3/2) * math.pi/180))
    #  target width in pixels  = 10.25" * 640 / ( 2 * d * sin( 29.5deg) / sin( 60.5deg))
    pegPixWidthToDist = 10.25 * 1280 / ( 2 * math.sin( 61.0/2 * math.pi/180) / math.sin( (90-61.0/2) * math.pi/180))

# compute a minimum size of contours to consider as peg targets
#  assume we won't be farther than wall to closest peg,
#  even if approaching other pegs
#  base of AIRSHIP is 5' 10.5" dia (flat to flat)
#  LAUNCHPAD tape is 185.3" from PLAYER STATION
#  so peg target is 114.8" or so from PLAYER STATION wall
# minPegContourHeight = pegPixHeightToDist / 114.8
# minPegContourWidth = pegPixWidthToDist / 114.8
# calibrating 3/5/17 at 12.5' total perimeter was 43 x 24 pixels
minPegContourHeight = 12
minPegContourWidth = 4


# ratio of width to height of peg
#  calibrating 2/23/17: one strip width = 35, height = 64; other 32 x 65 
pegShape = 34.5 / 64.5



#
# constants for identifying the BOILER high goal target retroflective tape
# target RFT is 15" across. Top is 4" tall, 4" between; bottom is 2" tall
#

# calibrating 2/20/17
# horizonal distance from camera to chimney, x, yTop, yBot
# 8' 10.5", 100, 45, 35

# L/R pixels from center of image where we want the boiler target to be
#  when it's 'on target,' i.e. it's where the shooter hits
#  negative for left of center
boilerCenterCalibration = 0

# number of pixels 'close enough' to on target
#  when the target is within (+/-) this many pixels of center the UDP and printout
#  will end in 'C' instead of 'L' or 'R'
boilerCloseToCenter = 2

#  boilerCam is set at top of this file
if( boilerCam == 'RealSense_640_480'):
    #   so for RealSense 640x480 camera:
    #     d = (5*480)/(2*sin(23)/sin(67)) / boilerHeightPix
    boilerPixHeightToDist = 10 * 480 / ( 2 * math.sin( 23 * math.pi/180) / math.sin( 67 * math.pi/180))
    #  target width in pixels  = 10.25" * 640 / ( 2 * d * sin( 29.5deg) / sin( 60.5deg))
    boilerPixWidthToDist = 15 * 640 / ( 2 * math.sin( 29.5 * math.pi/180) / math.sin( 60.5 * math.pi/180))

elif( boilerCam == 'LifeCam_1280_720'):
    # target pix/dist ratio for LifeCam webcam 1280x720:
    #   61deg horizontal by 34.3deg vertical
    """
    boilerPixHeightToDist = 10 * 720 / ( 2 * math.sin( 34.3/2 * math.pi/180) / math.sin( (90-34.3/2) * math.pi/180))
    #  target width in pixels  = 10.25" * 640 / ( 2 * d * sin( 29.5deg) / sin( 60.5deg))
    boilerPixWidthToDist = 15 * 1280 / ( 2 * math.sin( 61.0/2 * math.pi/180) / math.sin( (90-61.0/2) * math.pi/180))
    # calibrating 2/26/17
    """
    # from calibration 2/26/17
    boilerPixHeightToDist = 11344
    boilerPixWidthToDist = 12960

    # estimating 3/6 for centroid-based distance computation
    boilerCentroidToDist = 5856

# compute a minimum size of contours to consider as boiler targets
#  assume we won't be farther than far guardrail
#  width of field is 27'
#  viable shooting range is probably 9' to 16'
# minBoilerContourHeight = boilerPixHeightToDist / (27*12.0)
# minBoilerContourWidth = boilerPixWidthToDist / (27*12.0)
# from calibration numbers on 2/27/17
# as half of the measured height and width at 16'
minBoilerContourHeight = 60
minBoilerContourWidth = 38

# calibration 3/7/17
minBoilerContourWidth = 60
minBoilerContourHeight = 20

# new 3/13 # ignore targets tgat are too big
maxBoilerContourWidth = 125
maxBoilerContourHeight = 60

# BOILER shape ratio, width/height
# tube is 15" diameter. Top RFT is 4" tall, 4" between; bottom is 2" tall
# range in findTargets is .65 < ratio < 1.35
# calibrating 2/24/17
#  at 112" from camera
boilerTopShape = (272.0 - 155.0) / (566.0 - 510.0)
boilerBottomShape = (270.0 - 152.0) / (614.0 - 574.0)
boilerPerimeterShape = (272.0 - 152.0) / (614.0 - 510.0)

# calibrating 2/26/17
#  using Minimum Area Rectangles
#  Previously was using Bouding (vertical) Rectangles
# at 16'
boilerTopShape = 77.6 / 30.4 # 2.553
boilerBottomShape = 70.8 / 13.7 # 5.16
boilerPerimeterShape = (365.0 - 290.0) / (330.0 - 270.0) # 1.25
# at 8'
# boilerTopShape = ( 467 - 341) / (80 - 33) = 2.68
# boilerBottomShape = (460-339) / 30 = 4.03
# boilerPerimeterShape = (465-338) / (131-33) = 1.296

# calibrating 3/10/17 on field with green filter
boilerTopShape = 110.0 / 53.0# 
boilerBottomShape =  110.0 / 25.0
boilerPerimeterShape = ( 673.0 - 558.0) / 100.0

