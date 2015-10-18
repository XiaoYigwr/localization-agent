import os
import numpy as np
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import TrajectorySimulator as ts
import TraxClient as tc
try:
  import cv2
  channels = 4
except:
  cv2 = None
  channels = 2

#TODO: Put this configuration in an external file or rely entirely on Coco's data
dataDir = '/home/jccaicedoru/data/tracking/simulations/'
scene = dataDir + 'bogota.jpg'
obj = dataDir + 'photo.jpg'
box = [0, 100, 0, 100]
polygon = [50, 0, 100, 50, 50, 100, 0, 50]
imgSize = 64
totalFrames = 60
cam = False

MAX_SPEED_PIXELS = 1.0

def fraction(b,k):
  w = (b[2]-b[0])*(1-k)/2.
  h = (b[3]-b[1])*(1-k)/2.
  return [b[0]+w,b[1]+h, b[2]-w,b[3]-h]

def maskFrame(frame, flow, box):
  if flow is not None:
    maskedF = np.zeros( (4, frame.shape[0], frame.shape[1]) )
    maskedF[1,:,:] = flow[...,0]/10
    maskedF[2,:,:] = flow[...,1]/10
  else:
    maskedF = np.zeros( (2, frame.shape[0], frame.shape[1]) )
  maskedF[0,:,:] = (frame - 128.0)/128.0
  maskedF[-1,:,:] = 0
  for factor in [(1.00, 1), (0.75, -1), (0.5, 1), (0.25, -1)]:
    b = map(int, fraction(box, factor[0]))
    maskedF[-1, b[0]:b[2], b[1]:b[3]] = factor[1]
  #import pylab
  #pylab.imshow(maskedF[-1,:,:])
  #pylab.show()
  return maskedF

class VideoSequenceData(object):

  def __init__(self):
    self.predictedBox = [0,0,0,0]
    self.prevBox = [0,0,0,0]
    self.box = [0,0,0,0]
    self.prv = None
    self.now = None

  def prepareSequence(self, loadSequence=None):
    if loadSequence is None:
      self.dataSource = ts.TrajectorySimulator(scene, obj, box, polygon, camera=cam)
    elif loadSequence == 'TraxClient':
      self.dataSource = TraxClientWrapper()
    else:
      self.dataSource = StaticDataSource(loadSequence) 
    self.deltaW = float(imgSize)/self.dataSource.getFrame().size[0]
    self.deltaH = float(imgSize)/self.dataSource.getFrame().size[1]
    b = self.dataSource.getBox()
    self.box = map(int, [b[0]*self.deltaW, b[1]*self.deltaH, b[2]*self.deltaW, b[3]*self.deltaH])
    self.prevBox = map(int, [b[0]*self.deltaW, b[1]*self.deltaH, b[2]*self.deltaW, b[3]*self.deltaH])
    self.transformFrame()
    self.prev = self.now.copy()
    self.time = 0

  def nextStep(self, mode='training'):
    self.prevBox = map(lambda x:x, self.box)
    end = self.dataSource.nextStep()
    if mode == 'training':
      b = self.dataSource.getBox()
      self.box = map(int, [b[0]*self.deltaW, b[1]*self.deltaH, b[2]*self.deltaW, b[3]*self.deltaH])
    else:
      self.box = map(lambda x:x, self.predictedBox)
    self.time += 1
    return end

  def getFrame(self, savePath=None):
    if savePath is not None:
      with open(savePath + '/rects.txt','a') as rects:
        rects.write(' '.join(map(str,self.box)) + '\n')
      savePath += '/' + str(self.time).zfill(4) + '.jpg'

    self.prv = self.now
    self.transformFrame(save=savePath, box=self.prevBox)
    if cv2 is not None:
      flow = cv2.calcOpticalFlowFarneback(self.prv, self.now, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    else:
      flow = None

    return maskFrame(self.now, flow, self.box)

  def getMove(self):
    delta = [int(self.box[i]-self.prevBox[i])/MAX_SPEED_PIXELS for i in range(len(self.box))]
    return delta

  def setMove(self, delta):
    self.predictedBox = [int(self.box[i] + delta[i]*MAX_SPEED_PIXELS) for i in range(len(self.box))]
    self.dataSource.reportBox(self.predictedBox)

  def transformFrame(self, save=None, box=None):
    frame = self.dataSource.getFrame()
    frame = frame.convert('L')
    frame = frame.resize((imgSize,imgSize),Image.ANTIALIAS)
    '''if box is not None:
      draw = ImageDraw.Draw(frame)
      for f in [1,0.75,0.5,0.25]:
        draw.rectangle(fraction(box,f),outline=255)'''
    if save is not None:
      frame.save(save)
    self.now = np.array(frame)

class StaticDataSource(object):

  def __init__(self, directory):
    data = os.listdir(directory)
    self.dir = directory
    self.frames = [d for d in data if d.endswith(".jpg")]
    self.frames.sort()
    self.boxes = [ map(int,b.split()) for b in open(directory + '/rects.txt')]
    self.img = Image.open(self.dir + self.frames[0])
    self.current = 0
  
  def getFrame(self):
    return self.img

  def getBox(self):
    return self.boxes[self.current]

  def reportBox(self, box):
    return

  def nextStep(self):
    if self.current < len(self.frames):
      self.current += 1
      self.img = Image.open(self.dir + self.frames[self.current])
      return True
    else:
      return False

class TraxClientWrapper(object):

  def __init__(self):
    self.client = tc.TraxClient()
    self.path = self.client.nextFramePath()
    self.box = self.client.initialize()

  def getFrame(self):
    img = Image.open(self.path)
    return img

  def getBox(self):
    return self.box

  def reportBox(self, box):
    self.box = box
    self.client.reportRegion(box)

  def nextStep(self):
    return True
