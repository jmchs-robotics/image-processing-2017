#
# threaddedWebcamReader.py
#
# class to read images from webcam multi-threaded
# into different buffers and manage them

import cv2, numpy
import threading

class threaddedWebcamReader():
  # set to true to exit the camera-reading loop thread
  exitReadCam = False
  # thread object
  readCamThread = None

  # image buffers
  # TODO: need to initialize these
  img = []

  # status can be either
  #  newestImg, exactly one of these at any given time
  #   set when camera read into this buf is complete
  #  processing, up to as many as other threads
  #   previuosly newestImg, set when processing thread 
  #   needs an image
  #  ready, no limit 
  #   previuosly processing, set when processing thread
  #   is done processing.  Is also startup default
  imgStatus = ["ready", "ready", "ready", "ready"]
  imgStatusLock = threading.Lock()

  def __init__( self, vc):
    # use this camera object
    self.vc = vc
    # set initial image buffers
    for i in range( 4):
        r, a = vc.read()
	print r
        self.img.append( a)
    #
    # lock, move last status to 'new'
    #
    self.imgStatusLock.acquire()
    try:
        self.imgStatus[ 3] = "new"
    except:
      print "Error at 1a."
    finally:
        # unlock
        self.imgStatusLock.release()

  # 
  # set the imgStatus to ready
  #
  def imgStatusToReady( self, num):
    # lock the imgStatus array
    self.imgStatusLock.acquire()
    try:
        # change status
        self.imgStatus[ num] = "ready"
    except:
      print "Error at 1b."
    finally:
        # unlock
     	self.imgStatusLock.release()

  # end imgStatusToReady()

  #
  # get newest image buffer number
  # change its status to processing
  # called by processing threads
  #
  def getNewestImg( self):
    bufNum = None
    # lock the imgStatus array
    self.imgStatusLock.acquire()
    try:
        # find the newestImg
	for i in range( len( self.imgStatus)):
	    if( self.imgStatus[ i] == "new"):
    	        # set it to processing
		self.imgStatus[ i] = "processing"
		bufNum = i
		break
    except:
      print "Error at 1c."
    finally:
        # unlock
	self.imgStatusLock.release()
    # return the buffer number or None if none found
    return bufNum

  # end getNewestImg


  #
  # stop reading the camera
  #
  def stopReadCamLoopThread( self):
    self.exitReadCam = True

  #
  # endless loop of
  # find first available buffer, either ready or lastImg
  # get an image from the webcam
  # save it into the mext img bugfer that's either
  #  lastImg or ready
  #  lock the imgStatus array
  #  mark the previously newestImg as lastImg
  #  and mark the new one as newestImg
  #  unlock
  #
  def readCamLoop( self):
    print "readCamLoop starting."
    while( self.exitReadCam == False):
	#
        # lock, get last 'new' and a 'ready' to load image to 
	#
        self.imgStatusLock.acquire()
	prevBufNum = -1
	writeToBufNum = 0
        try:
            # find the newestImg buf and a ready (unused) buffer
	    for i in range( len( self.imgStatus)):
	        if( self.imgStatus[ i] == "new"):
		    prevBufNum = i
	        elif( self.imgStatus[ i] == "ready"):
		    writeToBufNum = i
        except:
          print "Error at 1d."
        finally:
            # unlock
	    self.imgStatusLock.release()
    
   	# get image from webcam
        r, self.img[ writeToBufNum] = self.vc.read()
        if( r != True):
	    print "threaddedWebcamReader: Warning: Error reading Webcam."
	    exit(1)
 
   	# 
	# lock, move previous 'new' to 'ready'
	# move new new to 'new'
	#
        self.imgStatusLock.acquire()
        try:
	    if( prevBufNum >= 0 and self.imgStatus[ prevBufNum] == "new"):
	        self.imgStatus[ prevBufNum] = "ready"
	    self.imgStatus[ writeToBufNum] = "new"
        except:
          print "Error at 1e."
        finally:
            # unlock
	    self.imgStatusLock.release()
    
  # end readCamLoop()

  #
  # start reading the camera, indefinitely
  #
  def startReadCamLoopThread( self):
    self.readCamThread = threading.Thread( target = self.readCamLoop)
    self.readCamThread.start()

 
  def printImageStatus( self):
    o = ""
    for i in range( 4):
        o += self.imgStatus[ i] + ' '
    print o

