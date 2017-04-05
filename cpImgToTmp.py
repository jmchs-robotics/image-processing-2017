#!/usr/bin/python

import time
import sys
import shutil

fileL = ["d.jpg", "colorMasked.jpg", "d2.jpg", "r.jpg", "rRed.jpg", "rWhite.jpg", "dtmp.jpg", "irmap.jpg"]

while(1):
 for fn in fileL:
  shutil.copyfile( '/home/frc5933/roboPong2016/image-processing/'+fn, '/mnt/ramdisk/pic.jpg')
  time.sleep( 0.5)
