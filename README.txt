Steamworks Vision Processing 2017
Last Updated 4/5/17

1. WHAT HAPPENS ON UP-BOARD BOOT-UP
1a. When the UP board operating system boots up, the last thing it does is run /etx/rc.local.  So we put a few lines in /etc/rc.local to start running our vision processing software and catching printed lines to 'log' files.  These lines go at the end of /etc/rc.local, but before the "exit 0" line:

# start Steamworks 2017 image processing
#
# Boiler
su - frc5933 -c '/home/frc5933/steamworks2017/image-processing/runBoilerWebcam.py &> /home/frc5933/steamworks2017/image-processing/logs/runBoilerWebcam.log &' 
# Peg
su - frc5933 -c '/home/frc5933/steamworks2017/image-processing/runPeg640.py &> /home/frc5933/steamworks2017/image-processing/logs/runPeg640.log &'

1b.  Because the UP board boots faster than the FRC router, the runBoilerWebcam.py and runPeg640.py check for a good network connection on 10.59.33 or 192.168.  Because the cameras don't boot quickly (at least the webcam was occasionally slow, and trackRft.py doesn't deal well with that) run... then checks that its respective camera is up and running.  They then run trackRft.py with the command line parameters for boiler or peg.  These run... scripts run within try/except blocks and run indefinitely withoit returning.

1c.  Once all connections are good, trackRft.py is running twice, once to find the boiler using the webcam writing results to port 5800, and once to find the peg using the RealSense on 640x480 at 60 frames per second writing to port 5801.  These details are set on trackRft.py's command line.

2. FILES
2a. trackRft.py, findTargets.py, config.py, threaddedWebcamReader.py are all used (as trackRft.py) to read input (camera or file), process ilthe input image(s), find the desired target, and write target position relative to the center of the image and estimate the target distance from the camera.

2b. runBoilerWebcam.py and runPeg640.py - see 1b.

2c. startWebImageServer runs mjpg_streamer, which will serve images to a remote web page.  It's not very well tested. cpImgToTmp.py was used to test mjpg_streamer by copying a few images where mjpg_streamer would serve them to the web page.

2d. killAllImageProcessing is used to stop mjpg_streamer, trackRft.py, runBoilerWebcam.py and runPeg640.py all at once.

2e. runallBoilerSnapshots was to run trackRft.py on all the images we captured during field walking at UT Regionals on 3/10/17.  By running all the snapshots we adjusted the hsv thresholds to find targets, and estimate distances.

2f. takeCal.py runs trackRft.py and copies the snapshot images to a directory.  Use this to calibrate the field. Not well tested.

2g. calibration*/ are directories with snapshot images from walking the playing field.  Used for selecting / confirming hsv threshold values and algorithms.

2h. logs/ contains stdout capture from runBoilerWebcam.py and runPeg640.py, to aid debugging.

OTHER NOTES
- the parent directory for all these files was changed between last competition use and git commit, so some hard-coded use of directories may fail.
