#!/usr/bin/python
#
# findTargets.py
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

from config import pegPixWidthToDist, pegPixHeightToDist, minPegContourHeight, minPegContourWidth, pegCloseToCenter, pegShape, pegCenterCalibration

from config import boilerPixWidthToDist, boilerPixHeightToDist, minBoilerContourHeight, minBoilerContourWidth, boilerCenterCalibration, boilerCloseToCenter, boilerTopShape, boilerBottomShape, boilerPerimeterShape, maxBoilerContourWidth, maxBoilerContourHeight

from config import printDebug
from config import boilerCentroidToDist

#
# process collection of boundingBoxes for an image pattern
#  that resembles the LIFT PEG retroflective tape
#
def findPegCentroids( boundingBoxes, contours, imgW, imgH):
    
    punt = False # flag to stop looking for contours
    b = [ 0, 0, 0, 0]
    b2 = [ 0, 0, 0, 0]

    # - iterate contours from the bottom of the image by counting index i from 0...
    for i in range( 0, len( boundingBoxes)):
        if( punt):
            break
        b = boundingBoxes[ i]
        bWh = b[2] / b[3]

        # ignore boxes smaller than minimum expected
        if( b[3] < minPegContourHeight * 0.65):
            continue

        # if within size and shape (w:h ratio) of whole strip
        if(( bWh > pegShape * 0.65) and ( bWh < pegShape * 1.35)):
            if printDebug: 
                print "one possible strip at"
                print b

            # iterate subsequent (equal/higher) contours by counting j from 1... len( contours) - i
            for j in range( i+1, len( boundingBoxes)):
                b2 = boundingBoxes[ j]
                bWh = b2[2] / b2[3]

                # only consider pairs of boxes close in altitude in the FOV
                if( b2[1] < b[1] -10*b[3] or b2[1] > b[1] + 10*b[3]):
                    break

                # if similar in height and also correct shape
                if(( b2[3] > b[3]*0.65) and ( b2[3] < b[3]*1.35) and ( bWh > pegShape * 0.65) and ( bWh < pegShape * 1.35)):
                    if printDebug:
                        print 'found a box of similar width and appropriate w/h ratio:'
                        print b2

                    # if two boxes' distance apart L_R is right ratio to the first one's height
                    if(( abs( b2[0] - b[0]) / b[3] > 8.25/5.0 * 0.6) and ( abs( b2[0] - b[0]) / b[3] < 8.25/5.0 * 1.4)):
                        if printDebug:
                            print "Winner!"
                        r = [ 0, 0, -1, -1]
                        # pick upper left corner and compute max size
                        r[0] = min( b[0], b2[0])
                        r[2] = max( b2[0]+b2[2], b[0]+b[2]) - min( b2[0], b[0])
                        r[1] = min( b[1], b2[1])
                        r[3] = max( b2[1]+b2[3], b[1]+b[3]) - min( b2[1], b[1])

			# compute centroids of upper and of lower tape
			M = cv2.moments( contours[i])
			cxi = int(M['m10']/M['m00'])
			cyi = int(M['m01']/M['m00'])
			M = cv2.moments( contours[j])
			cxj = int(M['m10']/M['m00'])
			cyj = int(M['m01']/M['m00'])
			
			# compute center of the target as center betwen
			#  the centroids
			ctrX = ( cxi + cxj) / 2.0
			ctrY = ( cyi + cyj) / 2.0

			# compute distance between centroids
			distBetweenCentroids = math.sqrt( math.pow(cxi-cxj, 2) + math.pow(cyi-cyj,2))

                        punt = True # stop outer iteration
                        break # found the two strips of tape

                    # end if() b2 contours good dist apart
                # end if() 2nd contour is right size, shape
            # end for() iterate 2nd contour
        # end if() contour has appropriate shape
    # end for() iterate contours


    # if didn't find the target, nothing else to do
    if( punt == False):
        return None, None, None, None, None, None, None, None, None
    

    # return the distance from the center of the image to the
    #  center of the rectangle, and the distance to the target
    ctr2targetUD = ( imgH / 2.0) - ( r[1] + r[3] / 2.0)
    ctr2targetLR = ( r[0] + r[2] / 2.0) - ( imgW / 2.0) - pegCenterCalibration

    # compute distance to target
    # TODO: what to do in case can't see 2nd piece of RF tape
    outDistW = pegPixWidthToDist / ((b[2] + b2[2]) / 2.0)
    outDistH = pegPixHeightToDist / (( b[3] + b2[3])/2.0) # based on ave height of each piece of RF tape

        #
        # TODO: deal with a bisected tape stip
        #
        # --- iterate higher contours by counting j from 1...
        # ---- if contour[ I+j] within distance (x,y), size and shape (one part of the tape, bisected by the peg)
        # ----- iterate lower contours by counting j from -1, -2...
        # ------ if contour[ I+j] within distance (x,y), size and shape (one part of the tape, bisected by the peg)
        # ------- calculate distance based on outside perimeter of all 3 contours
        # ------- calculate peg position from outside perimeter all 3
        # ------- return peg position, distance, message which way to lean because you're off target enough to have a tape obscured

    #if( ctr2targetLR < m + 100 and ctr2targetLR > m - 100): # good result? Send it
    trackDir = "C"
    if( ctr2targetLR < - pegCloseToCenter):
        trackDir = "L"
    elif( ctr2targetLR > pegCloseToCenter):
        trackDir = "R"

    # return ctr2targetLR, ctr2targetUD, outDistW, outDistH, trackDir, r
    return ctr2targetLR, ctr2targetUD, outDistW, outDistH, trackDir, r, ctrX - ( imgW / 2.0) - boilerCenterCalibration, ( imgH / 2.0) - ctrY, boilerCentroidToDist / distBetweenCentroids
# end findPegCentroid()


#
# process collection of vertical boundingBoxes for an image pattern
#  that resembles the BOILER target retroflective tape
#
def findBoilerCentroids( boundingMinRects, contours, imgW, imgH):
   
    if printDebug:
        print boundingMinRects

    punt = False # flag to stop looking for contours
    # get upper left corner x, y, plus w, h from minimum rectangles in box vextor format
    boundingBoxes = []
    for bmr in boundingMinRects:
        w = bmr[1][1]
        h = bmr[1][0]
	if( bmr[2] < 45 and bmr[2] > -45):
	   w2 = w
	   w = h
	   h = w2
        x = round( bmr[0][0] - w / 2.0)
        y = round( bmr[0][1] - h / 2.0)
        boundingBoxes.append( [ x, y, w, h])

    b = [ 0, 0, 0, 0]
    b2 = [ 0, 0, 0, 0]
   
    # - iterate contours from the top of the image by counting index i from len() down...
    for i in range( len( boundingBoxes)-1, -1, -1):
        if( punt):
            break
        b = boundingBoxes[ i]

        # ignore boxes smaller than minimum expected
        # if( b[3] < 1.0 or b[2] < minBoilerContourWidth * 0.65): # before 3/13
	# 3/14 better check- ignore boxes outside min and max sizes
       	if( b[3] < minBoilerContourHeight * 0.65 or b[2] < minBoilerContourWidth * 0.65 or b[2] > maxBoilerContourWidth * 1.35 or b[3] > maxBoilerContourHeight * 1.35):
            continue

        # compute width to height ratio of shape
        bWh = b[2] / b[3]

        # if within size and shape (w:h ratio) of whole strip
        if(( bWh > boilerTopShape*.65) and ( bWh < boilerTopShape*1.5)): # 1.35
            if printDebug:
                print "found a box in range of boilerTopShape,"
                print b

            # iterate subsequent (equal/lower) contours by counting j from i-1 down...
            #for j in range( i-1, -1, -1):
            for j in range( len( boundingBoxes)-1, -1, -1):
		if( i == j):  # don't consider the same target against itself
			continue
                b2 = boundingBoxes[ j]
                # ignore boxes smaller than minimum expected
                # if( b2[3] < 1.0 or b2[2] < minBoilerContourWidth * 0.65): # before 3/14
		# 3/14 better check- ignore boxes outside min and max sizes
        	if( b[3] < minBoilerContourHeight * 0.65 or b[2] < minBoilerContourWidth * 0.65 or b[2] > maxBoilerContourWidth * 1.35 or b[3] > maxBoilerContourHeight * 1.35):
                    continue
                bWh = b2[2] / b2[3]

                # only consider pairs of boxes close in width
                #if( b2[2] < b[2] * 0.8):
                #    break

                # if similar in width to first box, and correct shape
                if(( b2[2] > b[2]*0.65) and ( b2[2] < b[2]*1.35) ):
                  if printDebug:
                        print 'found a box of similar width:'
                        print b2
                  # if correct shape
		  if(( bWh > boilerBottomShape*.65) and ( bWh < boilerBottomShape*1.35)):
                    if printDebug:
                        print 'found a box of appropriate w/h ratio:'
                        print b2

                    # if two boxes' total perimeter ratio is right
		    d = math.sqrt( math.pow( b[0] - b2[0], 2) + math.pow( b[1] - b2[1], 2)) # distance between box centers
		    totH = ( d + b[3] / 2.0 + b2[3] / 2.0) # total height
		    aveW = ( b[2] + b2[2]) / 2.0 
		    pr = aveW / totH
                    if(( pr > boilerPerimeterShape * 0.6) and ( pr < boilerPerimeterShape * 1.4)):
                        if printDebug:
                            print "Winner:"
                        # compute upper left corner and total size
			# total height is 10". mid-height position is 3" from top RFT's mid height and 4" from bottom RFT's mid height, or 3/7 dist between the RFT's mid height
			boxMidY = min( b[1], b2[1]) + abs( b[3] - b2[3]) * 3.0 / 7.0
			# pick LR center of larger (upper) RFT as LR center of target
			boxMidX = b[0]
			if( b2[3] > b[3]):
			    boxMidX = b2[0]
                        r = [ 0, 0, -1, -1]
                        r[0] = int( round( boxMidX))
                        r[2] = int( round( aveW))
                        r[1] = int( round( boxMidY))
                        r[3] = int( round( totH))

			# compute centroids of upper and of lower tape
			M = cv2.moments( contours[i])
			cxi = int(M['m10']/M['m00'])
			cyi = int(M['m01']/M['m00'])
			M = cv2.moments( contours[j])
			cxj = int(M['m10']/M['m00'])
			cyj = int(M['m01']/M['m00'])
			
			# compute center of the target as center betwen
			#  the centroids
			ctrX = ( cxi + cxj) / 2.0
			ctrY = ( cyi + cyj) / 2.0

			# compute distance between centroids
			distBetweenCentroids = math.sqrt( math.pow(cxi-cxj, 2) + math.pow(cyi-cyj,2))

                        if printDebug:
                            print r
                        punt = True # stop outer iteration
                        break # found the two strips of tape

                    # end if() b2 contours good dist apart
                # end if() 2nd contour is right size, shape
            # end for() iterate 2nd contour
        # end if() contour has appropriate shape
    # end for() iterate contours


    # if didn't find the target, nothing else to do
    if( punt == False):
        return None, None, None, None, None, None, None, None, None
        #return None, None, None, None, None, None

    # return the distance from the center of the image to the
    #  center of the rectangle, and the distance to the target
    ctr2targetUD = ( imgH / 2.0) - ( r[1] + r[3] / 2.0)
    ctr2targetLR = ( r[0] + r[2] / 2.0) - ( imgW / 2.0) - boilerCenterCalibration

    # compute distance to target based on width of RFT
    outDistW = boilerPixWidthToDist / r[2]
    # compute distance to target based on height total of both strips of RFT
    outDistH = boilerPixHeightToDist / r[3]

    #
    # give L/R/C direction
    #
    trackDir = "C"
    if( ctr2targetLR < - boilerCloseToCenter):
        trackDir = "L"
    elif( ctr2targetLR > boilerCloseToCenter):
        trackDir = "R"

    return ctr2targetLR, ctr2targetUD, outDistW, outDistH, trackDir, r, ctrX - ( imgW / 2.0) - boilerCenterCalibration, ( imgH / 2.0) - ctrY, boilerCentroidToDist / distBetweenCentroids
# end findBoilerCentroids()




