import logging
import numpy
import matplotlib as mpl
import matplotlib.pyplot as plt
import os

def parse_gt(gtPath):
    '''
    Parses a line oriented bounding box description (whitespace or comma separated)
    '''
    #some file are comma-separated instead of tab-separated
    gtFile = open(gtPath)
    gt = numpy.array([map(int, line.strip().replace(',', '\t').split()) for line in gtFile])
    gtFile.close()
    logging.debug('Found {} lines in ground truth file {}'.format(len(gt), gtPath))
    return gt

def plot_gt(gt, formatString=''):
    '''
    Plots the different columns of a parsed bounding box sequence
    '''
    expectedLabels = ['X lower left coord.', 'Y lower left coord.', 'Width', 'Height']
    if not len(expectedLabels) == gt.shape[1]:
        raise Exception('Label and column mismatch ({} vs. {})'.format(len(expectedLabels), gt.shape[1]))
    for column in xrange(len(expectedLabels)):
        plt.subplot(2,2,column+1)
        plt.plot(numpy.linspace(0, 1, num=gt.shape[0]), gt[:,column], formatString, label=expectedLabels[column])
        plt.xlabel('Frame index')
        plt.ylabel('Pixel')
        plt.title(expectedLabels[column])
    plt.show()

def dataset_gt(gtsDir, pattern='groundtruth_rect.txt'):
    '''
    Parses the bounding boxes of the dataset, where each folder is a sequence and groundtruth file has a name pattern
    '''
    sequenceNames = os.listdir(gtsDir)
    gtsDict = {}
    for sequenceName in sequenceNames:
        #TODO: make adaptable with a reg-exp as pattern
        gtPath = os.path.join(gtsDir, sequenceName, pattern)
        if not os.path.exists(gtPath):
            logging.debug('Ommiting sequence {} as ground truth file {} wasnt found'.format(sequenceName, pattern))
            continue
        sequenceGt = parse_gt(gtPath)
        gtsDict[sequenceName] = sequenceGt
        logging.debug('Parsed gt for sequence {}'.format(sequenceName))
    return gtsDict
