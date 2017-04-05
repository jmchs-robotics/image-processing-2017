#!/usr/bin/python
#
# takeCal.py
#
# run trackRft.py for one frame, capture snapshot
# for either --peg or --boiler
# move the snapshot file to the ./calibrationFiles/ directory 
#  to filename given on command line
# save results to ./calibrationFiles/ directory

import os
import sys
import subprocess

punt = False
if( sys.argv[1] == "--boiler"):
  c1 = "--boiler"
  c2 = "--webcam"
elif( sys.argv[1] == "--peg"):
  c1 = "--peg"
  c2 = "--640"
else:
  punt = True

fn = sys.argv[2]
if fn == None or fn == '':
  punt = True

if punt == True:
  print "Usage: getBoilerCal.py --peg|--boiler <filename>"

print "Taking calibration for {}.  Give me a few seconds...".format( c1)

b = subprocess.check_output( ["/home/frc5933/steamworks2017/image-processing/trackRft.py", "--print", c1, c2, "--limit", "1", "--snapshots"], stderr=subprocess.STDOUT)
fp = open( "/home/frc5933/steamworks2017/image-processing/calibrationFiles/{}.txt".format( fn), 'w')
fp.write( b)
fp.close()

for a in ["colorMasked", "colorWithContours", "colorWithTargets"]:
    os.system( "mv /home/frc5933/steamworks2017/image-processing/{}.jpg /home/frc5933/steamworks2017/image-processing/calibrationFiles/{}_{}.jpg".format( a, fn, a))

print "Wrote \'{}\' files into ./calibrationFiles/ directory.  Done.".format( fn)
