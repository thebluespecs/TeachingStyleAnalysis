# USAGE
# opencv-text-detection --image images/lebron_james.jpg

# import the necessary packages
import argparse
import os
import time

import cv2
from nms import nms
import numpy as np

import utils
from decode import decode
from draw import drawPolygons, drawBoxes


def text_detection(image, east, min_confidence, width, height):
    # load the input image and grab the image dimensions
    file = os.path.basename(image)
    print("Filename: ", file)
    box_path = "../test_images/text_"+file
    poly_path = "../UnblurredPoly/"+file

    image = cv2.imread(image)
    orig = image.copy()
    (origHeight, origWidth) = image.shape[:2]

    # set the new width and height and then determine the ratio in change
    # for both the width and height
    (newW, newH) = (width, height)
    ratioWidth = origWidth / float(newW)
    ratioHeight = origHeight / float(newH)

    # resize the image and grab the new image dimensions
    image = cv2.resize(image, (newW, newH))
    (imageHeight, imageWidth) = image.shape[:2]
    image_area = imageWidth*imageHeight

    # define the two output layer names for the EAST detector model that
    # we are interested -- the first is the output probabilities and the
    # second can be used to derive the bounding box coordinates of text
    layerNames = [
        "feature_fusion/Conv_7/Sigmoid",
        "feature_fusion/concat_3"]

    # load the pre-trained EAST text detector
    print("[INFO] loading EAST text detector...")
    net = cv2.dnn.readNet(east)

    # construct a blob from the image and then perform a forward pass of
    # the model to obtain the two output layer sets
    blob = cv2.dnn.blobFromImage(image, 1.0, (imageWidth, imageHeight), (123.68, 116.78, 103.94), swapRB=True, crop=False)

    start = time.time()
    net.setInput(blob)
    (scores, geometry) = net.forward(layerNames)
    end = time.time()

    # show timing information on text prediction
    print("[INFO] text detection took {:.6f} seconds".format(end - start))


    # NMS on the the unrotated rects
    confidenceThreshold = min_confidence
    nmsThreshold = 0.4

    # decode the blob info
    (rects, confidences, baggage) = decode(scores, geometry, confidenceThreshold)

    offsets = []
    thetas = []
    for b in baggage:
        offsets.append(b['offset'])
        thetas.append(b['angle'])

    ##########################################################

    # functions = [nms.felzenszwalb.nms, nms.fast.nms, nms.malisiewicz.nms]
    functions = [nms.fast.nms]

    print("[INFO] Running nms.boxes . . .")

    for i, function in enumerate(functions):

        start = time.time()
        indicies = nms.boxes(rects, confidences, nms_function=function, confidence_threshold=confidenceThreshold,
                                 nsm_threshold=nmsThreshold)
        end = time.time()

        indicies = np.array(indicies).reshape(-1)

        drawOn = orig.copy()
        text_area = 0
        if rects:
            drawrects = np.array(rects)[indicies]
            print(imageHeight, imageWidth, image_area)
            for _, _, w, h in drawrects:
                text_area += (w*h)

            name = function.__module__.split('.')[-1].title()
            print("[INFO] {} NMS took {:.6f} seconds and found {} boxes".format(name, end - start, len(drawrects)))

            drawBoxes(drawOn, drawrects, ratioWidth, ratioHeight, (0, 255, 0), 2)

            title = "nms.boxes {}".format(name)
        print(text_area/image_area)
        # cv2.imshow(title, drawOn)
        # cv2.moveWindow(title, 150+i*300, 150)

        cv2.imwrite(box_path, drawOn)
    # cv2.waitKey(0)


    # convert rects to polys
    polygons = utils.rects2polys(rects, thetas, offsets, ratioWidth, ratioHeight)

    print("[INFO] Running nms.polygons . . .")

    for i, function in enumerate(functions):

        start = time.time()
        indicies = nms.polygons(polygons, confidences, nms_function=function, confidence_threshold=confidenceThreshold,
                                 nsm_threshold=nmsThreshold)
        end = time.time()

        indicies = np.array(indicies).reshape(-1)

        drawOn = orig.copy()

        if polygons:
            drawpolys = np.array(polygons)[indicies]

            name = function.__module__.split('.')[-1].title()

            print("[INFO] {} NMS took {:.6f} seconds and found {} boxes".format(name, end - start, len(drawpolys)))

            drawPolygons(drawOn, drawpolys, ratioWidth, ratioHeight, (0, 255, 0), 2)

            title = "nms.polygons {}".format(name)
        # cv2.imshow(title, drawOn)
        # cv2.moveWindow(title, 150+i*300, 150)
        # cv2.imwrite(poly_path, drawOn)
    # cv2.waitKey(0)


def text_detection_command():
    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", type=str,
        help="path to input image")
    ap.add_argument("-east", "--east", type=str, default=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'frozen_east_text_detection.pb'),
        help="path to input EAST text detector")
    ap.add_argument("-c", "--min-confidence", type=float, default=0.5,
        help="minimum probability required to inspect a region")
    ap.add_argument("-w", "--width", type=int, default=320,
        help="resized image width (should be multiple of 32)")
    ap.add_argument("-e", "--height", type=int, default=320,
        help="resized image height (should be multiple of 32)")
    args = vars(ap.parse_args())

    path = "../test_images/"
    l = os.listdir(path)
    apply = lambda x: path+x
    orig_imgs = list(map(apply, l))

    print("Begin detecting ..............")
    for img in orig_imgs:
        text_detection(image=img, east=args["east"], min_confidence=args['min_confidence'], width=args["width"], height=args["height"], )

if __name__ == '__main__':
    text_detection_command()
