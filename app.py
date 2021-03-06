#fill_data functtion

import requests as r
import cv2
import numpy as np
import operator
import os
from PIL import Image
import sqlite3
import time
from flask import Flask, render_template, Response,request,redirect,url_for,flash
from flask_cors import CORS,cross_origin
import io
import base64
from io import StringIO
import imutils
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
cors = CORS(app)
socketio = SocketIO(app)


app.secret_key='Oblivion'
chara={"character":"","tag":0,"tags":0, "flag":0, "l":[]}

@app.route('/')
def login():
    chara["tag"] = 0

    return render_template('login.html')

@app.route('/index_page')
def index():
    return render_template('index.html')

@app.route("/logout")
def logout():
    try:
        chara["character"] = None
        chara["tag"] = 0
        chara["tags"] = 0
        chara["flag"] = 0
        chara["l"] = []
    except:
        chara.clear()
        chara["character"]= None
        chara["tag"]= 0
        chara["tags"]=0
        chara["flag"]= 0
        chara["l"]=[]
    #flash("Logout successfullt","info")
    return redirect(url_for("login"))

@app.route('/signup')
def sign_up():
    chara["tag"] = 1
    return render_template('signup.html')

@app.route('/signup_page', methods=["GET"])
def signup():
    #Name, Id, Category, Email, Gender, Contat = map(str, list_of_data)
    if request.method == "GET":
        Name = request.args['Username']
        Id = request.args['ID']
        Category = request.args['Category']
        Email = request.args['Email']
        Gender = request.args['Gender']
        Contact = request.args['Contact']
        chara["Name"] = str(Name)
        chara["Id"] = int(Id)
        chara["Category"] = str(Category)
        chara["Email"] = str(Email)
        chara["Gender"] = str(Gender)
        chara["Contact"] = str(Contact)
    return render_template('index.html')

@app.route('/fill_data')
def fill_data():
    Name = chara["Name"]
    Id = chara["Id"]
    Category = chara["Category"]
    Email = chara['Email']
    Gender = chara['Gender']
    Contact = chara['Contact']
    character=chara["character"]
    con = sqlite3.connect("passcode.db")
    cmd = "SELECT * FROM People WHERE ID=" + str(Id)
    cursor = con.execute(cmd)
    isRecordExist = 0
    for row in cursor:
        isRecordExist = 1
    if (isRecordExist == 1):
        cmd = "UPDATE People SET Name=%r ,Gender=%r ,Category=%r ,Email=%r ,Contact=%r, Character=%r WHERE ID=%d" % (
            Name, Gender, Category, Email, Contact, character, int(Id))
        con.execute(cmd)
        con.commit()

    else:
        cmd = "INSERT INTO People Values(%r,%r,%r,%r,%r,%r,%r)" % (Id, Name, Gender, Category, Email, Contact, character)
        con.execute(cmd)
        con.commit()
        con.close()
    return redirect(url_for('logout'))

@app.route("/check_entry",methods=['GET'])
def check_login():
    if request.method == "GET" :
        Name = request.args['username']
        Id = request.args['ID']
        chara["Name"]=Name
        chara["Id"]=Id

        con = sqlite3.connect("passcode.db")
        cmd = "SELECT * FROM People WHERE ID=" + str(Id)
        cursor = con.execute(cmd)
        isRecordExist_id = 0
        isRecordExist_name = 0

        for row in cursor:
            isRecordExist_id = 1
            if str(row[1]) == Name:
                isRecordExist_name = 1

        if isRecordExist_id == 1 and isRecordExist_name == 1:
            return render_template('index.html')
        else:
            return render_template('login.html', info="No Existing Data Found")
    else:
        return render_template('login.html', info="type again pls")

@app.route('/compare_sign')
def compare_sign():
    if chara["tag"]==1:
        return redirect(url_for('fill_data'))
    else:
        if chara["Id"] and chara["character"]!=None:
            Id=chara["Id"]
            character=chara["character"]
        else:
            render_template("display.html", info="Password incorrect")
        con = sqlite3.connect("passcode.db")
        cmd = "SELECT * FROM People WHERE ID=" + str(Id)
        cursor = con.execute(cmd)

        isRecordExist_id = 0
        isRecordExist_character = 0
        for row in cursor:
            isRecordExist_id = 1
            if str(row[6]) == character:

                isRecordExist_character = 1
        if isRecordExist_id == 1 and isRecordExist_character == 1:
            return render_template('display.html', info="Found ")
        else:
            return render_template('display.html', info="Password incorrect")


def center(x,y,w,h):
    x_cord = int(x + (1 / 2)*w)
    y_cord = int(y + (1 / 2)*h)
    point=(x_cord,y_cord)
    return point

def tracking(img,centers):
    for center_point in centers:
        cv2.circle(img, center_point, radius=0, color=(0, 255, 0), thickness=10)

def show_display(img,centers):
    start_point=centers[0]
    color = (0, 255, 0)
    # Line thickness of 9 px
    thickness = 9
    for i in range(1,len(centers)-1):
        end_point=centers[i]
        cv2.line(img, start_point, end_point, color, thickness)
        start_point=centers[i]
    return img
MIN_CONTOUR_AREA = 100

RESIZED_IMAGE_WIDTH = 20
RESIZED_IMAGE_HEIGHT = 30

class ContourWithData():

    # member variables ############################################################################
    npaContour = None           # contour
    boundingRect = None         # bounding rect for contour
    intRectX = 0                # bounding rect top left corner x location
    intRectY = 0                # bounding rect top left corner y location
    intRectWidth = 0            # bounding rect width
    intRectHeight = 0           # bounding rect height
    fltArea = 0.0               # area of contour

    def calculateRectTopLeftPointAndWidthAndHeight(self):               # calculate bounding rect info
        [intX, intY, intWidth, intHeight] = self.boundingRect
        self.intRectX = intX
        self.intRectY = intY
        self.intRectWidth = intWidth
        self.intRectHeight = intHeight
        return

    def checkIfContourIsValid(self):                            # this is oversimplified, for a production grade program
        if self.fltArea < MIN_CONTOUR_AREA: return False        # much better validity checking would be necessary
        return True

def get_text(imgTestingNumbers):
    allContoursWithData = []                # declare empty lists,
    validContoursWithData = []              # we will fill these shortly
    s="pause"
    try:
        npaClassifications = np.loadtxt("classifications.txt", np.float32)                  # read in training classifications
    except:
        print("error, unable to open classifications.txt, exiting program\n")
        os.system("pause")
        return
    # end try

    try:
        npaFlattenedImages = np.loadtxt("flattened_images.txt", np.float32)                 # read in training images
    except:
        print ("error, unable to open flattened_images.txt, exiting program\n")
        os.system("pause")
        return
    # end try

    npaClassifications = npaClassifications.reshape((npaClassifications.size, 1))       # reshape numpy array to 1d, necessary to pass to call to train

    kNearest = cv2.ml.KNearest_create()                   # instantiate KNN object

    kNearest.train(npaFlattenedImages, cv2.ml.ROW_SAMPLE, npaClassifications)

    #imgTestingNumbers = cv2.imread("validate2.png")          # read in testing numbers image

    if imgTestingNumbers is None:                           # if image was not read successfully
        print("error: image not read from file \n\n")  # print error message to std out
        os.system("pause")                                  # pause so user can see error message
        return                                             # and exit function (which exits program)
    # end if

    imgGray = cv2.cvtColor(imgTestingNumbers, cv2.COLOR_BGR2GRAY)       # get grayscale image
    imgBlurred = cv2.GaussianBlur(imgGray, (5,5), 0)                    # blur

                                                        # filter image from grayscale to black and white
    imgThresh = cv2.adaptiveThreshold(imgBlurred,                           # input image
                                      255,                                  # make pixels that pass the threshold full white
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,       # use gaussian rather than mean, seems to give better results
                                      cv2.THRESH_BINARY_INV,                # invert so foreground will be white, background will be black
                                      11,                                   # size of a pixel neighborhood used to calculate threshold value
                                      2)                                    # constant subtracted from the mean or weighted mean

    imgThreshCopy = imgThresh.copy()        # make a copy of the thresh image, this in necessary b/c findContours modifies the image

    npaContours, npaHierarchy = cv2.findContours(imgThreshCopy,             # input image, make sure to use a copy since the function will modify this image in the course of finding contours
                                                 cv2.RETR_EXTERNAL,         # retrieve the outermost contours only
                                                 cv2.CHAIN_APPROX_SIMPLE)   # compress horizontal, vertical, and diagonal segments and leave only their end points

    for npaContour in npaContours:                             # for each contour
        contourWithData = ContourWithData()                                             # instantiate a contour with data object
        contourWithData.npaContour = npaContour                                         # assign contour to contour with data
        contourWithData.boundingRect = cv2.boundingRect(contourWithData.npaContour)     # get the bounding rect
        contourWithData.calculateRectTopLeftPointAndWidthAndHeight()                    # get bounding rect info
        contourWithData.fltArea = cv2.contourArea(contourWithData.npaContour)           # calculate the contour area
        allContoursWithData.append(contourWithData)                                     # add contour with data object to list of all contours with data
    # end for

    for contourWithData in allContoursWithData:                 # for all contours
        if contourWithData.checkIfContourIsValid():             # check if valid
            validContoursWithData.append(contourWithData)       # if so, append to valid contour list
        # end if
    # end for

    validContoursWithData.sort(key = operator.attrgetter("intRectX"))         # sort contours from left to right

    strFinalString = ""         # declare final string, this will have the final number sequence by the end of the program

            # for each contour               # thickness

    imgROI = imgThresh[contourWithData.intRectY : contourWithData.intRectY + contourWithData.intRectHeight,     # crop char out of threshold image
                       contourWithData.intRectX : contourWithData.intRectX + contourWithData.intRectWidth]

    imgROIResized = cv2.resize(imgROI, (RESIZED_IMAGE_WIDTH, RESIZED_IMAGE_HEIGHT))             # resize image, this will be more consistent for recognition and storage

    npaROIResized = imgROIResized.reshape((1, RESIZED_IMAGE_WIDTH * RESIZED_IMAGE_HEIGHT))      # flatten image into 1d numpy array

    npaROIResized = np.float32(npaROIResized)       # convert from 1d numpy array of ints to 1d numpy array of floats

    retval, npaResults, neigh_resp, dists = kNearest.findNearest(npaROIResized, k = 1)     # call KNN function find_nearest

    strCurrentChar = str(chr(int(npaResults[0][0])))                                             # get character from results

    strFinalString = strFinalString + strCurrentChar            # append current char to full string

    return (imgTestingNumbers,strFinalString)

@socketio.on('image')
@cross_origin()
def image(data_image):
    handDetect=cv2.CascadeClassifier('fist.xml')
    sbuf = StringIO()
    sbuf.write(data_image)
    b = io.BytesIO(base64.b64decode(data_image))
    try:
        pimg = Image.open(b)
        gray = cv2.cvtColor(np.array(pimg), cv2.COLOR_BGR2GRAY)
        hand = handDetect.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in hand:
            center_point = center(x, y, w, h)
            chara["l"].append(center_point)
        if len(chara["l"]) != 0:
            scr = Image.open('blank.jpg')
            sample_sign_1 = show_display(np.array(scr), chara["l"])
            sample = get_text(sample_sign_1)
            character = sample[1]
        else:
            character = 'No Character Detected'
        chara["character"] = character
        emit('response_back', character)
    except:
        character="Processing......"
        emit('response_back', character)

        
if __name__ == '__main__':
    #app.run(debug=True)
    socketio.run(app,host='0.0.0.0', debug=True )
