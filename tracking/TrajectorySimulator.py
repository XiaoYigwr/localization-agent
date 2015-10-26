import os,sys
import numpy as np
import random, time
from PIL import Image
from PIL import ImageEnhance
from PIL import ImageDraw
import numpy.linalg
import pickle

#TODO: correct methods not following same logic as numpy.random, e.g. randint (includes both extremes)
def startRandGen():
  r = random.Random()
  r.jumpahead(long(time.time()))
  return r

def segmentCrop(image, polygon):
    cropMask = Image.new('L', image.size, 0)
    maskDraw = ImageDraw.Draw(cropMask)
    maskDraw.polygon(polygon, fill=255)
    bounds = polygon_bounds(polygon)
    imageCopy = image.copy()
    imageCopy.putalpha(cropMask)
    crop = imageCopy.crop(bounds)
    return crop

def polygon_bounds(polygon):
    maskCoords = np.array(polygon).reshape(len(polygon)/2,2).T
    bounds = map(int, (maskCoords[0].min(), maskCoords[1].min(), maskCoords[0].max(), maskCoords[1].max()))
    return bounds

def applyScale(scales):
    return np.array([[scales[0], 0, 0],[0, scales[1], 0],[0, 0, 1]])

def applyRotate(angle):
    return np.array([[np.cos(angle), np.sin(angle), 0],[-np.sin(angle), np.cos(angle), 0],[0, 0, 1]])

def applyTranslate(translation):
    return np.array([[1, 0, translation[0]],[0,1,translation[1]],[0, 0, 1]])

def applyTransform(crop, transform, camSize):
    # Requires inverse as the parameters transform from object to camera 
    return crop.transform(camSize, Image.AFFINE, np.linalg.inv(transform).flatten()[:7])

def concatenateTransforms(transforms):
    # TODO: remove hard coded dimension
    result = np.eye(3)
    for aTransform in transforms:
        result = np.dot(aTransform, result)
    return result

# Points must be in homogeneous coordinates
def transform_points(transform, points):
    transformedCorners = np.dot(transform, points)
    return transformedCorners
    
#################################
# GENERATION OF COSINE FUNCTIONS
#################################
MIN_AMPLITUDE = 0.2
MAX_AMPLITUDE = 1.2
MIN_PERIOD = 0.25
MAX_PERIOD = 1.0
MIN_PHASE = 0.0
MAX_PHASE = 1.0
MIN_VSHIFT = -0.5
MAX_VSHIFT = 0.5
RANGE = np.arange(0.0, 6.0, 0.1)

def stretch(values, z1, z2):
  mi = min(values)
  ma = max(values)
  return (z2 - z1)*( (values-mi)/(ma-mi) ) + z1

def cosine(y1, y2, randGen):
    a = (MAX_AMPLITUDE - MIN_AMPLITUDE)*randGen.random() + MIN_AMPLITUDE
    b = (MAX_PERIOD - MIN_PERIOD)*randGen.random() + MIN_PERIOD
    c = (MAX_PHASE - MIN_PHASE)*randGen.random() + MIN_PHASE
    d = (MAX_VSHIFT - MIN_VSHIFT)*randGen.random() + MIN_VSHIFT

    f = a*np.cos(b*RANGE - c) + d
    return stretch(f, y1, y2)

#################################
# TRAJECTORY CLASS
#################################

class OffsetTrajectory():

    def __init__(self, w, h, offset):
        self.thetaMin = -np.pi/12
        self.thetaMax = np.pi/12
        self.xMin = np.max(np.abs(offset*np.sin([self.thetaMin, self.thetaMax])))
        self.yMin = np.max(np.abs(offset*np.sin([self.thetaMin, self.thetaMax])))
        self.xMax = w-offset
        self.yMax = h-offset
        self.scaleMax = 1.0
        self.scaleMin = 0.8
        print('Translation bounds: {} to {}'.format([self.xMin, self.yMin], [self.xMax, self.yMax]))
        print('Rotation bounds: {} to {}'.format(self.thetaMin, self.thetaMax))
        print('Scale bounds: {} to {}'.format(self.scaleMin, self.scaleMax))
        self.transforms = [
            #Transformation(translateX, -offset, -offset),
            #Transformation(translateY, -offset, -offset),
            Transformation(rotate, self.thetaMin, self.thetaMax),
            Transformation(scaleX, self.scaleMin, self.scaleMax),
            Transformation(scaleY, self.scaleMin, self.scaleMax),
            Transformation(translateX, self.xMin, self.xMax),
            Transformation(translateY, self.yMin, self.yMax),
        ]

class BoundedTrajectory():

  def __init__(self, w, h):
    # Do sampling of starting and ending points (fixed number of steps).
    # Implicitly selects speed, length and direction of movement.
    # Assume constant speed (no acceleration).
    self.randGen = startRandGen()
    x1 = (0.8*w - 0.2*w)*elf.randGen.random() + 0.2*w
    y1 = (0.8*h - 0.2*h)*self.randGen.random() + 0.2*h
    x2 = (0.8*w - 0.2*w)*self.randGen.random() + 0.2*w
    y2 = (0.8*h - 0.2*h)*self.randGen.random() + 0.2*h
    print 'Trajectory: from',int(x1),int(y1),'to',int(x2),int(y2)

    # Sample direction of waving
    if self.randGen.random() > 0.5:
      # Horizontal steps, vertical wave
      self.X = stretch(RANGE, x1, x2)
      self.Y = cosine(y1, y2)
    else:
      # Horizontal wave, vertical steps
      self.X = cosine(x1, x2)
      self.Y = stretch(RANGE, y1, y2)

  def getCoord(self, j):
    return (self.X[j], self.Y[j])

#################################
# TRANSFORMATION CLASS
#################################

class Transformation():

  def __init__(self, f, a, b, pathFunction=None, steps=64):
    self.func = f
    self.randGen = startRandGen()
    if pathFunction is None:
        # Initialize range of transformation
        alpha = (b - a)*self.randGen.random() + a
        beta = (b - a)*self.randGen.random() + a
        if alpha > beta:
          c = alpha
          alpha = beta
          beta = c
        # Generate a transformation "path"
        self.X = cosine(alpha, beta, self.randGen)
    else:
        self.X = pathFunction(a, b, steps)

  def transformContent(self, j):
    return self.func(self.X[j])

  def transformShape(self, w, h, j):
    return self.func(w, h, self.X[j])

#################################
# CONTENT TRANSFORMATIONS
#################################

def rotate(angle):
  matrix = applyRotate(angle)
  return matrix

def translateX(value):
  matrix = applyTranslate([value, 0])
  return matrix

def translateY(value):
  matrix = applyTranslate([0, value])
  return matrix

def scaleX(value):
  matrix = applyScale([value, 1])
  return matrix

def scaleY(value):
  matrix = applyScale([1, value])
  return matrix

def color(img, value):
  enhancer = ImageEnhance.Color(img)
  return enhancer.enhance(value)

def contrast(img, value):
  enhancer = ImageEnhance.Contrast(img)
  return enhancer.enhance(value)

def brightness(img, value):
  enhancer = ImageEnhance.Brightness(img)
  return enhancer.enhance(value)

def sharpness(img, value):
  enhancer = ImageEnhance.Sharpness(img)
  return enhancer.enhance(value)

#################################
# SHAPE TRANSFORMATIONS
#################################

MIN_BOX_SIDE = 20

def identityShape(w, h, factor):
  return (w, h)

#################################
# OCCLUSSIONS
#################################

class OcclussionGenerator():

  def __init__(self, w, h, maxSize):
    self.randGen = startRandGen()
    num = self.randGen.randint(0,10)
    self.boxes = []
    for i in range(num):
      x1 = (w - maxSize)*self.randGen.random()
      y1 = (h - maxSize)*self.randGen.random()
      wb = maxSize*self.randGen.random()
      hb = maxSize*self.randGen.random()
      box = map(int, [x1, y1, x1+wb, y1+hb])
      self.boxes.append(box)

  def occlude(self, img, source):
    for b in self.boxes:
      patch = source.crop(b)
      img.paste(patch, b)
    return img

#################################
# TRAJECTORY SIMULATOR CLASS
#################################

class TrajectorySimulator():

  def __init__(self, sceneFile, objectFile, box, polygon=None, maxSegments=9, camSize=(224,224), axes=False, maxSteps=None, contentTransforms=None, shapeTransforms=None, cameraContentTransforms=None, cameraShapeTransforms=None, drawBox=False, camera=True, drawCam=False, trajectoryModelPath=None, trajectoryModelLength=60):
    self.randGen = startRandGen()
    if maxSteps is None:
        maxSteps = len(RANGE)
    self.maxSteps = maxSteps
    # Load images
    self.scene = Image.open(sceneFile)
    self.obj = Image.open(objectFile)
    # Use scene as camera
    if camSize is None:
        camSize = self.scene.size
    self.camSize = camSize
    # Correct camera size to be even as needed by video encoding software
    evenCamSize = list(self.camSize)
    for index in range(len(evenCamSize)):
        if evenCamSize[index] % 2 ==1:
            evenCamSize[index] += 1
    self.camSize = tuple(evenCamSize) 
    # Use box as polygon
    if polygon is None:
        polygon = (box[0], box[1], box[2], box[1], box[2], box[3], box[0], box[3])
    self.polygon = polygon
    self.drawBox = drawBox
    self.drawCam = drawCam
    self.camera = camera
    #Segment the object using the polygon and crop to the resulting axes-aligned bounding box
    self.obj = segmentCrop(self.obj, polygon)
    # Draw coordinate axes for each source
    if axes:
      self.scene = self.draw_axes(self.scene)
      self.obj = self.draw_axes(self.obj)
    self.objSize = self.obj.size
    self.box = [0,0,0,0]
    self.step = 0
    self.validStep = 0
    # Start trajectory
    self.scaleObject()
    # Calculate bounds after scaling
    self.bounds = np.array([[0,self.objSize[0],self.objSize[0],0],[0,0,self.objSize[1],self.objSize[1]]])
    self.bounds = np.vstack([self.bounds, np.ones((1,self.bounds.shape[1]))])
    self.cameraBounds = np.array([[0,self.camSize[0],self.camSize[0],0],[0,0,self.camSize[1],self.camSize[1]]])
    self.cameraBounds = np.vstack([self.cameraBounds, np.ones((1,self.cameraBounds.shape[1]))])
    self.occluder = OcclussionGenerator(self.scene.size[0], self.scene.size[1], min(self.objSize)*0.3)
    self.currentTransform = np.eye(3,3)
    self.cameraTransform = np.eye(3,3)
    #TODO: reactivate shape transforms
    # Initialize transformations
    #TODO: select adequate values for transforms and maybe sample them from a given distribution
    if shapeTransforms is None:
        self.shapeTransforms = [
            Transformation(identityShape, 1, 1),
        ]
    else:
        self.shapeTransforms = shapeTransforms
    if trajectoryModelPath is None:
        if contentTransforms is None:
            self.contentTransforms = [
                Transformation(scaleX, 0.7, 1.3),
                Transformation(scaleY, 0.7, 1.3),
                Transformation(rotate, -np.pi/50, np.pi/50),
                Transformation(translateX, 0, self.camSize[0]-max(self.objSize)),
                Transformation(translateY, 0, self.camSize[1]-max(self.objSize)),
            ]
        else:
            self.contentTransforms = contentTransforms
    else:
        model = TrajectoryModel(trajectoryModelPath, trajectoryModelLength)
        self.contentTransforms = model.sample(self.scene.size)
    if cameraContentTransforms is None:
        if trajectoryModelPath is None:
            cameraDiagonal = np.sqrt(self.camSize[0]**2+self.camSize[1]**2)
            self.cameraContentTransforms = OffsetTrajectory(self.scene.size[0], self.scene.size[1], cameraDiagonal).transforms
        else:
            #TODO: camera transforms related to sampled trajectory
            self.cameraContentTransforms = []
    else:
        self.cameraContentTransforms = cameraContentTransforms
    if cameraShapeTransforms is None:
        self.cameraShapeTransforms = [
            Transformation(identityShape, 1, 1),
        ]
    else:
        self.cameraShapeTransforms = cameraShapeTransforms
    self.transform()
    self.render()
    print '@TrajectorySimulator: New simulation with scene {} and object {}'.format(sceneFile, objectFile)

  def scaleObject(self):
    # Initial scale of the object is 
    # a fraction of the smallest side of the scene
    smallestSide = min(self.camSize)
    side = smallestSide*( 0.4*self.randGen.random() + 0.4 )
    # Preserve object's aspect ratio with the largest side being "side"
    ar = float(self.obj.size[1])/float(self.obj.size[0])
    if self.obj.size[1] > self.obj.size[0]:
      h = side
      w = side/ar
    else:
      h = side*ar
      w = side
    self.objView = self.obj.resize((int(w),int(h)), Image.ANTIALIAS)
    self.objSize = self.objView.size

  def validate_bounds(self, transform, points, size):
    transformedPoints = transform_points(transform, points)
    return np.all(np.logical_and(np.greater(transformedPoints[:2,:], [[0], [0]]), np.less(transformedPoints[:2,:], [[size[0]],[size[1]]])))

  def transform(self):
    self.objSize = self.shapeTransforms[0].transformShape(self.objSize[0], self.objSize[1], self.step)
    self.objView = self.obj.resize(self.objSize, Image.ANTIALIAS)
    # Concatenate transforms and apply them to obtain transformed object
    self.cameraTransform = concatenateTransforms((self.cameraContentTransforms[i].transformContent(self.step) for i in xrange(len(self.cameraContentTransforms))))
    self.currentTransform = concatenateTransforms((self.contentTransforms[i].transformContent(self.step) for i in xrange(len(self.contentTransforms))))
    self.objView = applyTransform(self.objView, np.dot(self.cameraTransform, self.currentTransform), self.scene.size)

  def render(self):
    self.sceneView = self.scene.copy()
    # Paste the transformed object, at origin as scene is absolute reference system
    self.sceneView.paste(self.objView, (int(0),int(0)), self.objView)
    self.sceneView = self.occluder.occlude(self.sceneView, self.scene)
    for i in range(len(self.cameraShapeTransforms)):
      self.sceneSize = self.cameraShapeTransforms[i].transformShape(self.scene.size[0], self.scene.size[1], self.step)
      self.sceneView = self.sceneView.resize(self.sceneSize, Image.ANTIALIAS).crop((0,0) + self.scene.size)
    # Obtain definite camera transform by appending object transform
    self.camView = applyTransform(self.sceneView, np.linalg.inv(self.cameraTransform), self.camSize)
    referenceTransform = self.cameraTransform
    # Obtain bounding box points on camera coordinate system
    if self.camera:
        boxPoints = transform_points(self.currentTransform, self.bounds)
        clipSize = self.camSize
    else:
        boxPoints = transform_points(np.dot(self.cameraTransform, self.currentTransform), self.bounds)
        clipSize = self.sceneView.size
    self.box = [max(min(boxPoints[0,:]),0), max(min(boxPoints[1,:]),0), min(max(boxPoints[0,:]), clipSize[0]-1), min(max(boxPoints[1,:]),clipSize[1]-1)]
    self.camDraw = ImageDraw.ImageDraw(self.camView)
    self.sceneDraw = ImageDraw.ImageDraw(self.sceneView)
    if self.drawBox:
        if self.camera:
            self.camDraw.rectangle(self.box)
        else:
            self.sceneDraw.rectangle(self.box)
    if self.drawCam:
        camPoints = transform_points(self.cameraTransform, self.cameraBounds)
        cameraBox = map(int, camPoints[:2, :].T.ravel())
        self.sceneDraw.polygon(cameraBox, outline=(0,255,0))
        sceneBoxPoints = transform_points(np.dot(self.cameraTransform, self.currentTransform), self.bounds)
        objectBox = map(int, sceneBoxPoints[:2, :].T.ravel())
        self.sceneDraw.polygon(objectBox, outline=(0,0,255))
    
  def nextStep(self):
    if self.step < self.maxSteps:
      self.transform()
      self.render()
      self.step += 1
      return True
    else:
      return False

  def saveFrame(self, outDir):
    fname = os.path.join(outDir, str(self.step).zfill(4) + '.jpg')
    self.getFrame().save(fname)
    gtPath = os.path.join(outDir, 'groundtruth_rect.txt')
    if self.step <= 1:
      out = open(gtPath, 'w')
    else:
      out = open(gtPath, 'a')
    box = map(int,[self.box[0], self.box[1], self.box[2], self.box[3]])
    out.write(','.join(map(str,box)) + '\n' )
    out.close()

  def getFrame(self):
    if self.camera:
      return self.camView
    else:
      return self.sceneView

  def getBox(self):
    return self.box

  def convertToGif(self, sequenceDir):
    os.system('convert -delay 1x30 ' + sequenceDir + '/*jpg ' + sequenceDir + '/animation.gif')
    os.system('rm ' + sequenceDir + '*jpg')

  def __iter__(self):
    return self

  def next(self):
    if self.nextStep():
      return self.getFrame()
    else:
      raise StopIteration()

  def draw_axes(self, image):
    size = image.size
    imageCopy = image.copy()
    draw = ImageDraw.Draw(imageCopy)
    minSize = min(size[1], size[0])
    width = int(minSize*0.1)
    length = int(minSize*0.3)
    draw.line(map(int, (width/2, width/2, width/2, length)), fill=(255, 0, 0), width=width)
    draw.line(map(int, (width/2, width/2, length, width/2)), fill=(0, 255, 0), width=width)
    
    del draw
    return imageCopy

## Recommended Usage:
# o = TrajectorySimulator('bogota.jpg','crop_vp.jpg',[0,0,168,210])
# while o.nextStep(): o.saveFrame(dir)
# o.sceneView

try:
    import pycocotools.coco

    class COCOSimulatorFactory():

        #Assumes standard data layout as specified in https://github.com/pdollar/coco/blob/master/README.txt
        def __init__(self, dataDir, dataType):
            self.randGen = startRandGen()
            self.dataDir = dataDir
            self.dataType = dataType
            self.annFile = '%s/annotations/instances_%s.json'%(dataDir,dataType)
            self.imagePathTemplate = '%s/images/%s/%s'
            #COCO dataset handler object
            print '!!!!!!!!!!!!! WARNING: Loading the COCO annotations can take up to 3 GB RAM !!!!!!!!!!!!!'
            self.coco = pycocotools.coco.COCO(self.annFile)
            #TODO: Filter the categories to use in sequence generation
            self.catIds = self.coco.getCatIds()
            cats = self.coco.loadCats(self.catIds)
            nms=[cat['name'] for cat in cats]
            self.imgIds = self.coco.getImgIds(catIds=self.catIds)
            self.fullImgIds = self.coco.getImgIds()
            print 'Number of categories {} and corresponding images {}'.format(len(self.catIds), len(self.imgIds))
            print 'Category names: {}'.format(', '.join(nms))
            
        def createInstance(self, *args, **kwargs):
            #Select a random image for the scene
            sceneData = self.coco.loadImgs(self.fullImgIds[self.randGen.randint(0, len(self.fullImgIds))])[0]
            scenePath = self.imagePathTemplate%(self.dataDir, self.dataType, sceneData['file_name'])

            #Select a random image for the object, restricted to annotation categories
            objData = self.coco.loadImgs(self.imgIds[self.randGen.randint(0, len(self.imgIds))])[0]
            objPath = self.imagePathTemplate%(self.dataDir, self.dataType, objData['file_name'])

            #Get annotations for object scene
            objAnnIds = self.coco.getAnnIds(imgIds=objData['id'], catIds=self.catIds, iscrowd=None)
            objAnns = self.coco.loadAnns(objAnnIds)

            #Select a random object in the scene and read the segmentation polygon
            objectAnnotations = objAnns[self.randGen.randint(0, len(objAnns))]
            print 'Segmenting object from category {}'.format(self.coco.loadCats(objectAnnotations['category_id'])[0]['name'])
            polygon = objectAnnotations['segmentation'][self.randGen.randint(0, len(objectAnnotations['segmentation']))]

            scene = Image.open(scenePath)
            scene.close()
            simulator = TrajectorySimulator(scenePath, objPath, [], polygon=polygon, *args, **kwargs)
            
            return simulator

        def create(self, sceneFullPath, objectFullPath, axes=False):
            #TODO: make really definite
            sceneDict = [data for data in self.coco.loadImgs(self.fullImgIds) if str(data['file_name']) == os.path.basename(sceneFullPath)][0]
            objectDict = [data for data in self.coco.loadImgs(self.imgIds) if str(data['file_name']) == os.path.basename(objectFullPath)][0]
            scenePath = self.imagePathTemplate%(self.dataDir, self.dataType, sceneDict['file_name'])
            objPath = self.imagePathTemplate%(self.dataDir, self.dataType, objectDict['file_name'])
            objAnnIds = self.coco.getAnnIds(imgIds=objectDict['id'], catIds=self.catIds, iscrowd=None)
            objAnns = self.coco.loadAnns(objAnnIds)
            objectAnnotations = objAnns[self.randGen.randint(0, len(objAnns))]
            print 'Segmenting object from category {}'.format(self.coco.loadCats(objectAnnotations['category_id'])[0]['name'])
            polygon = objectAnnotations['segmentation'][self.randGen.randint(0, len(objectAnnotations['segmentation']))]
            scene = Image.open(scenePath)
            camSize = map(int, (scene.size[0]*0.5, scene.size[1]*0.5))
            scene.close()

            simulator = TrajectorySimulator(scenePath, objPath, [], polygon=polygon, camSize=camSize, axes=axes)

            return simulator
except Exception as e:
    print 'No support for pycoco'

class TrajectoryModel():

    def __init__(self, modelPath, length, maxSize=10, base=10.0):
        self.modelPath = modelPath
        modelFile = open(self.modelPath, 'r')
        self.model = pickle.load(modelFile)
        modelFile.close()
        self.length = length
        self.maxSize = maxSize

    def sample(self, sceneSize, base=10.0):
        nComponents = self.model.n_components
        clusterIds = np.random.choice(nComponents, size=np.random.choice(self.maxSize))
        trajectory = np.mean(self.model.means_[clusterIds], axis=0)
        trajectory = trajectory.reshape(int(trajectory.shape[0]/self.length), self.length)
        tx, ty, sx, sy = trajectory
        tx = tx*sceneSize[0]
        ty = ty*sceneSize[1]
        sx = base**sx
        sy = base**sy
        transforms = [
            Transformation(scaleX, None, None, pathFunction=lambda a,b,steps: sx),
            Transformation(scaleY, None, None, pathFunction=lambda a,b,steps: sy),
            Transformation(translateX, None, None, pathFunction=lambda a,b,steps: tx),
            Transformation(translateY, None, None, pathFunction=lambda a,b,steps: ty),
        ]
        return transforms