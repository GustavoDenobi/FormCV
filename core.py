import cv2
import numpy as np
import os
import configparser
import shutil
from datetime import datetime
from tinydb import TinyDB, Query
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import textwrap

VERSION = '2.0.0'

creditText = ('Este aplicativo foi criado e desenvolvido em 2018 por Gustavo F. A. Denobi, consultor pela iNOVEC. \n'
                  'Agradecimentos especiais ao UNICESUMAR Empresarial, pela oportunidade de aprendizado no processo '
                  'de desenvolvimento deste aplicativo.\n\n'
                  'O uso deste aplicativo e todo o seu conteúdo está totalmente sujeito a autorização do autor.\n\n'
                  'Contato: gustavodenobi@gmail.com\n'
                  'GitHub: github.com/GustavoDenobi\n\n'
                  'Versão: ' + VERSION
                  )


class Var:
    """
    This class stores general use variables and constants. When initialized, it reads config.ini to retrieve several
    values.
    """
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.rootDir = os.path.dirname(__file__)
        self.logDir = config['const']['logDir']  # The directory that should be scanned for images
        self.databaseFile = config['const']['databaseFile']  # Location of the current active database
        self.errorLogFile = config['const']['errorLogFile']  # Standard location of the error log
        self.imgPreviewSize = int(config['const']['imgPreviewSize'])  # Used as a factor for resizing image outputs
        self.threshold = float(config['const']['threshold']) # threshold used for defining image normalization
        self.imgDir = config['const']['imgDir'] # directory of images
        self.minimumHours = int(config['const']['minimumHours'])
        self.certificateDir = config['const']['certificateDir']
        self.errorLog = []  # Used to store a sequence of lines which contain details about every read image
        self.errors = 0  # Number of errors to be used in the error log
        self.warnings = 0  # NUmber of filling errors to be used in the error log
        self.inDatabase = True # To check if a RA was found in the database

    def checkBackup(self):
        """ Checks if a new backup should be done, according to the time defined in config.ini and does it if so."""
        config = configparser.ConfigParser()
        config.read('config.ini')
        lastBackup = config['backup']['lastbackup']
        backupDir = config['backup']['backupdir']
        maxTime = int(config['backup']['maxtime'])
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        currentTime = int(currentTime[:14])
        diff = currentTime - int(lastBackup)
        if(diff >= maxTime):
            config['backup']['lastbackup'] = str(currentTime)
            with open('config.ini', 'w') as configFile:
                config.write(configFile)

            shutil.copy(self.databaseFile, os.path.join(backupDir + os.sep + str(currentTime)) + ".json")
            return True
        else:
            return False

    def refreshParams(self):
        """ Refreshes the parameters stored in the __init__"""
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.logDir = config['const']['logDir']  # The directory that should be scanned for images
        self.databaseFile = config['const']['databaseFile']  # Location of the current active database
        self.errorLogFile = config['const']['errorLogFile']  # Standard location of the error log
        self.imgPreviewSize = int(config['const']['imgPreviewSize'])  # Used as a factor for resizing image outputs
        self.threshold = float(config['const']['threshold'])
        self.imgDir = config['const']['imgDir']
        self.minimumHours = int(config['const']['minimumHours'])
        self.certificateDir = config['const']['certificateDir']

    def paramTuner(self, variable, value):
        """
        string variable: the name of the variable in config.ini to be changed
        string value: the new value to be stored in variable
        """
        config = configparser.ConfigParser()
        config.read('config.ini')
        config['const'][variable] = value
        with open('config.ini', 'w') as configFile:
            config.write(configFile)
        self.refreshParams()

    pattern = [0, 1, 2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 0, 0, 1, 2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3]
    months = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
    w = 37 * 16
    h = 47 * 21
    coordOrder = {0: [0, 0], 1: [w, 0], 2: [w, h], 3: [0, h]}
    cvFormats = ['.jpeg', '.jpg', '.png', '.bmp']
    resetParams = {"imgPreviewSize" : 12,
                   "threshold" : 0.2,
                   "minimumHours" : 20}

    def fileCount(self, dir):
        """ Returns the number of valid images in the given directory
        string dir: root directory to count images
        int fileCount: number of valid images counted
        """
        fileCount = 0
        for subdir, dirs, files in os.walk(dir):
            for file in files:
                if (file[file.index('.'):] in self.cvFormats):
                    fileCount += 1
        return fileCount


class DBhandler(Var):
    """
    Class used to handle the database.
    """

    def __init__(self):
        super(DBhandler, self).__init__()
        self.docID = 0  # whenever an operation finds a doc ID, it is stored here
        self.loadDB()


    def loadDB(self):
        """ Opens the database file and retrieves useful info. """
        self.db = TinyDB(self.databaseFile)
        with self.db as db:
            self.dblist = db.all() # stores the database as e list
        self.length = len(self.dblist)  # number of consultants in database
        self.raColInt = [x["RA"] for x in self.dblist] # stores the list os RAs as integer
        self.raColStr = self.intToStr(self.raColInt)  # stores the list of RAs as string
        self.nameCol = [x['NOME'] for x in self.dblist]  # stores the list of names
        self.consultCol = [x['CONSULTORIA'] for x in self.dblist]  # stores the list of consulting names
        self.consultList = sorted(set(self.consultCol)) # stores a sorted listed of available consultings
        self.db = TinyDB(self.databaseFile) # creates a new instance of the database to be used by other methods

    def intToStr(self, intList):
        """
        Transforms list of integers into list of strings
        list intList: list containing integers
        """
        strList = []
        for item in intList:
            strList.append(str(item))
        return strList

    def docWriter(self, ra, year, period, time):
        """ Writes a consultant's info in the database. Expects the RA to be already in the database
        str ra: 8-number string conataining the RA
        str year: 4-number string containing the year
        str period: 3-letter code according to Var.months
        float time: sum of time of a consultant in a month
        """
        self.loadDB()
        with self.db as db:
            year = "y" + str(year)
            currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
            currentTime = currentTime[:14]
            q = db.search(Query().RA == int(ra))[0]
            if year in q.keys():
                if period in [x["month"] for x in q[year]]:
                    for item in q[year]:
                        if item['month'] == period:
                            item['time'] = time
                            item['entry_time'] = currentTime
                else:
                    q[year].append({'month': period, 'time': time, 'entry_time': currentTime})
            else:
                q[year] = [{'month': period, 'time': time, 'entry_time': currentTime}]
            db.update(q, Query().RA == int(ra))

    def retrieveConsultant(self, ra):
        """ Searches the database for the given RA number and returns a dict with its name and consulting
        str ra: the RA to be searched
        """
        self.loadDB()
        try:
            ra = int(ra)
            with self.db as db:
                q = [x for x in db.all() if x['RA'] == ra]
                if len(q) == 0:
                    return False
                else:
                    return q[0]
        except:
            return False

    def saveConsultant(self, consultant):
        """
        Appends a new consultant to the database
        :param consultant: dict containing consultant's ra, consulting and name
        """
        status = True  # turns to false if the input data is invalid
        for key in consultant.keys():
            if consultant[key] == '':  # checks if all fields are filled
                status = False
        if(not str(consultant['RA']).isdigit()):  # checks if RA is number
            status = False
        if(not len(str(consultant['RA'])) == 8):  # checks if RA has 8 numbers
            status = False
        if(status):  # if validation passed, proceed
            consultant['RA'] = int(consultant['RA'])
            if(consultant['RA'] in self.raColInt):  # checks if consultant is already in database
                try: # edits consultant
                    self.loadDB()
                    with self.db as db:
                        doc = db.get(Query().RA == consultant['RA'])
                        doc['NOME'] = consultant['NOME']
                        doc['CONSULTORIA'] = consultant['CONSULTORIA']
                        db.update(doc, Query().RA == consultant['RA'])
                    return 1
                except:
                    return 0
            else: # edit consultant
                try:  # adds consultant to the database
                    self.loadDB()
                    with self.db as db:
                        doc = {'RA': consultant['RA'],
                               'NOME': consultant['NOME'],
                               'CONSULTORIA': consultant['CONSULTORIA']}
                        db.insert(doc)
                    return 1
                except:
                    return 0

    def delConsultant(self, ra):
        """
        Deletes a consultant according to its given RA
        :param ra: string containing the consultant's RA
        """
        try:
            ra = int(ra)
            self.loadDB()
            with self.db as db:
                db.remove(Query().RA == ra)
            return 1
        except:
            return 0

    def checkOverwriting(self, ra, month, year):
        """
        When a new reading of forms is made, it's possible that another version of the same document has already been
        read, which could cause unwanted overwriting in the database. The purpose of this method is to check if a month
        has already been stored in the database and retrieve its entry.
        :param ra: consultant ra, either as a string or an integer
        :param month: 3-digit, all-caps string as defined in Var.months
        :param year: 4-digit string or integer
        :return: the entry dicotionary, if existent, else False
        """
        feedback = False
        if (len(str(ra)) == 8) and (len(month) == 3) and (len(str(year)) == 4):
            ra = int(ra)
            consultant = self.retrieveConsultant(ra)
            year = 'y' + str(year)
            if consultant is not False:
                if year in consultant:
                    for entry in consultant[year]:
                        if entry['month'] == month:
                            feedback = entry
        return feedback


class pdfCreator():
    """
    Creates PDF files based on a template and infos contained in certificateInfo and saves it to dir.
    :param certificateInfo: list of dicts
    :param dir: directory to save the PDFs
    """

    def __init__(self, certificateInfo, dir):
        self.template = Image.open("img\\template.png") # base image on which info is drawed
        self.draw = ImageDraw.Draw(self.template) # instance of the drawing
        # margins
        self.x_body = 500
        self.y_body = 800
        self.x_date = 1100
        self.y_date = 1400

        self.certificateInfo = certificateInfo
        self.writeText(self.certificateInfo) # writes text
        self.writeDate() # writes date
        self.savePDF(dir) # saves file in dir


    def writeText(self, fdict):
        """
        :param fdict: dict containing info for the text
        :return:
        """
        text = ("    Certifico que "
                + fdict["NOME"]
                + ", sob o RA "
                + fdict["RA"] +
                ", participou das atividades acadêmicas da Consultoria Júnior "
                + fdict["CONSULTORIA"]
                + ", cumprindo uma carga horária de "
                + fdict["TOTAL"]
                + " horas, nos meses de "
                + fdict["MES1"]
                + " e "
                + fdict["MES2"]
                + " no ano de "
                + fdict["ANO"]
                + ".")

        text = textwrap.wrap(text)
        selectFont = ImageFont.truetype("consola.ttf", size=72)
        linespace = 0
        for line in text:
            self.draw.text((self.x_body, self.y_body + linespace), line, (0, 0, 0), font=selectFont)
            linespace += 88

    def writeDate(self, city = "Maringá"):
        """
        :param city: name of the city to be written in the document
        :return:
        """
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        currentTime = currentTime[:8]
        year = currentTime[:4]
        month = int(currentTime[4:6])
        months = ['Janeiro',
                  'Fevereiro',
                  'Março',
                  'Abril',
                  'Maio',
                  'Junho',
                  'Julho',
                  'Agosto',
                  'Setembro',
                  'Outubro',
                  'Novembro',
                  'Dezembro']
        month = months[month-1]
        day = currentTime[6:8]
        text = city + ", " + day + " de " + month + " de " + year + "."
        selectFont = ImageFont.truetype("consola.ttf", size=72)
        self.draw.text((self.x_date, self.y_date), text, (0, 0, 0), font=selectFont)


    def savePDF(self, dir):
        """
        :param dir: directory to save the PDF
        :return:
        """
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        filepath = os.path.join(dir, (self.certificateInfo["CONSULTORIA"]
                                      + " - "
                                      + self.certificateInfo["NOME"]
                                      + " - "
                                      + self.certificateInfo["RA"]
                                      + " - "
                                      + currentTime[0:14]
                                      + ".pdf"))
        self.template.save(filepath, "PDF", resolution=300.0)


class certificateGenerator(DBhandler):
    """
    Used to retrieve info of consultants that achieved the minimum worked time.
    """
    monthTrans = {'JAN': 'Janeiro',
                  'FEV': 'Fevereiro',
                  'MAR': 'Março',
                  'ABR': 'Abril',
                  'MAI': 'Maio',
                  'JUN': 'Junho',
                  'JUL': 'Julho',
                  'AGO': 'Agosto',
                  'SET': 'Setembro',
                  'OUT': 'Outubro',
                  'NOV': 'Novembro',
                  'DEZ': 'Dezembro'}

    def __init__(self, year, months, consult):
        super(certificateGenerator, self).__init__()
        self.fdict = {"RA" : "",
                      "NOME" : "",
                      "CONSULTORIA" : "",
                      "TOTAL" : "",
                      "MES1" : "",
                      "MES2" : "",
                      "ANO" : ""}
        self.months = months
        self.year = year
        self.certToGenerate = self.filterSumTime(year, months, consult)
        self.certCount = len(self.certToGenerate["RA"])

    def filterSumTime(self, year, months, consult):
        """
        :param year: year of activity
        :param months: list of 2 months
        :param consult: consulting
        :return: dict of list with info to be written in certificates
        """
        output = {'RA': [],
                     'NOME': [],
                     'CONSULTORIA': [],
                     'TOTAL': []}

        self.loadDB()
        yearstr = ('y' + str(year))
        for doc in self.dblist:
            total = 0
            if consult == "Todas":
                if yearstr in doc:

                    for entry in doc[yearstr]:
                        if entry['month'] in months:
                            total += entry['time']
            else:
                if (yearstr in doc) and (consult in doc['CONSULTORIA']):
                    for entry in doc[yearstr]:
                        if entry['month'] in months:
                            total += entry['time']
            total = int(total) if total % 1 <= 0.5 else int(total) + 1
            if total >= float(self.minimumHours):
                output['RA'].append(doc['RA'])
                output['NOME'].append(doc['NOME'])
                output['CONSULTORIA'].append(doc['CONSULTORIA'])
                output['TOTAL'].append(total)
        return output

    def saveCertificate(self, index):
        """
        Used to save a single certificate
        :param index: index of consultant to get a certificate
        :return:
        """
        currentCertificate = self.fdict
        currentCertificate["RA"] = str(self.certToGenerate["RA"][index])
        currentCertificate["NOME"] = self.certToGenerate["NOME"][index]
        currentCertificate["CONSULTORIA"] = self.certToGenerate["CONSULTORIA"][index]
        currentCertificate["MES1"] = self.monthTrans[self.months[0]]
        currentCertificate["MES2"] = self.monthTrans[self.months[1]]
        currentCertificate["TOTAL"] = str(self.certToGenerate["TOTAL"][index])
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        currentCertificate["ANO"] = currentTime[0:4]
        pdfCreator(currentCertificate, self.certificateDir)

    def saveCertificates(self):
        """
        Saves the certificates to PDFs using the pdfCreator class
        :return:
        """
        for current in range(self.certCount):
            currentCertificate = self.fdict
            currentCertificate["RA"] = str(self.certToGenerate["RA"][current])
            currentCertificate["NOME"] = self.certToGenerate["NOME"][current]
            currentCertificate["CONSULTORIA"] = self.certToGenerate["CONSULTORIA"][current]
            currentCertificate["MES1"] = self.monthTrans[self.months[0]]
            currentCertificate["MES2"] = self.monthTrans[self.months[1]]
            currentCertificate["TOTAL"] = str(self.certToGenerate["TOTAL"][current])
            currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
            currentCertificate["ANO"] = currentTime[0:4]
            pdfCreator(currentCertificate, self.certificateDir)


class errorLogHandler(Var):
    """
    Contains methods to handle the error log
    """
    def __init__(self):
        super(errorLogHandler, self).__init__()
        self.errorLogText = self.errorLogLoader(self.errorLogFile)

    def errorLogLoader(self, file):
        """
        Loads the text contained in the error log file.
        :param file: error log file path
        :return:
        """
        with open(file) as stream:
            text = stream.read()
            return text

    def errorLogWriter(self, errorLog):
        """
        Writes the errorLog.txt.
        :param errors: number of errors detected
        :param warnings: number of filling errors detected
        :param errorLog: list of operations completed
        """
        with open(self.errorLogFile, 'w') as file_handler:
            for item in errorLog:
                file_handler.write("{}\n".format(item))

    def errorLogExporter(self, dst):
        """
        Copies the errorLog.txt to a destination defined in dst
        :param dst: exporting destination
        """
        shutil.copy(self.errorLogFile, dst)


class FormCV(Var):
    """
    This is the core of forms reading, only class where opencv is widely used.
    """
    def __init__(self):
        super(FormCV, self).__init__()
        self.f = 8
        self.dayWithFillError = []  # filled in dataExtract(), stores days with other than 6 marks
        self.dayWithSumError = []  # filled in timeCalc(), stores days with impossible values
        self.daysWorked = []  # filled in timeCalc(), stores days that were successfully read
        self.imgresize = None  # imported image
        self.imgcontour = None
        self.imgnormal = None  # normalized image

    def imread(self, filename, flags=cv2.IMREAD_COLOR, dtype=np.uint8):
        """
        Workaround to cv.imread(), which fails to read a file containing utf-8 symbols like accentuation.
        :param filename: path to image to be read
        :param flags: type of image to be returned. Standard colored image.
        :param dtype: encoding
        :return: image as matrix with shape (x,y,3)
        """
        try:
            n = np.fromfile(filename, dtype)
            img = cv2.imdecode(n, flags)
            return img
        except Exception as e:
            return None

    def imgPreview(self, img, title = "Preview"):
        """
        Shows a window with the given image
        :param img: the array to be showed
        :param title: the window title
        """
        cv2.imshow(title, img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        k = -1
        while(k == -1):
            k = cv2.waitKey(0)  & 0xFF

    def imgUndistort(self, file):
        """
        Reads an image, converts it to grayscale, finds its contour and returns the undistorted version of it.
        There's a major problem with this function, as it is unable to handle any input image that is not exactly stand-
        ing upright. In this sense, the getCoordOrder() below is part of the problem (see its docstring for details).
        :return:  the undistorted version of the input image, or a failure string "IMGUNDIST"
        """
        try:
            imgread = self.imread(file)
            imggray = cv2.cvtColor(imgread, cv2.COLOR_BGR2GRAY)  #import and convert into grayscale
            width, height = imggray.shape
            maxheight = 1024
            maxwidth = int(maxheight/(width/height))
            self.imgresize = cv2.resize(imggray,(maxwidth, maxheight), interpolation = cv2.INTER_AREA)
            imgblur = cv2.GaussianBlur(self.imgresize,(9,9),0) #apply gaussian blur
            imgthresh = cv2.adaptiveThreshold(imgblur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,3,2)
            im2, contours, hierarchy = cv2.findContours(imgthresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) #detect contours
            #Select contour with biggest area:
            cnt = contours[0]
            for c in contours:
                if cv2.contourArea(c) > cv2.contourArea(cnt):
                    cnt = c

            #simplify contour to 4 coordinates
            epsilon = 0.1*cv2.arcLength(cnt,True)
            approx = cv2.approxPolyDP(cnt,epsilon,True)

            self.imgcontour = cv2.drawContours(cv2.cvtColor(self.imgresize, cv2.COLOR_GRAY2BGR),
                                               [approx],
                                               0,
                                               (0, 255, 0),
                                               4)

            #transforms polygon that contains data into rectangle
            #
            pts1 = np.float32(approx) #coordinates from contour
            pts2 = np.float32(self.getCoordOrder(approx))

            M = cv2.getPerspectiveTransform(pts1,pts2)
            imgundist = cv2.warpPerspective(self.imgresize,M,(self.w, self.h))

            return imgundist
        except:
            return "IMGUNDIST"
    
    def getCoordOrder(self, array):
        """
        Used by imgUndistort() to retrieve the order of coordinates, so it can operate the undistorting algorithm.
        The problem with this function is that it can only work if the image is in portrait format (y>x) and the area of
        interest is upright in this image. Given the fact that the (0,0) point in an image is in the top left corner,
        this function identifies it by considering that the top left corner of the area of interest is the closest point
        to the top left corner of the image.
        :param array: points to be evaluated
        :return: the ordered coordinates (top left, top right, bottom right, bottom left)
        """
        try:
            sumofcoorda = []
            sumofcoordb = []
            for a in array:
                for b in a:
                    partial = 0
                    for coord in b:
                        partial = partial + coord
                    sumofcoorda.append(partial)
                    sumofcoordb.append(partial)
            tl = sumofcoorda.index(min(sumofcoorda)) # top left
            br = sumofcoorda.index(max(sumofcoorda)) # bottom right
            sumofcoordb.remove(min(sumofcoorda))
            sumofcoordb.remove(max(sumofcoorda))
            tr = sumofcoorda.index(min(sumofcoordb)) # top right
            bl = sumofcoorda.index(max(sumofcoordb)) # bottom left
            ordered = [[self.coordOrder[tl]],[self.coordOrder[tr]],[self.coordOrder[br]],[self.coordOrder[bl]]]
            return ordered
        except:
            return [0] # this will purposedly create an error in imgUndistort()

    def imgTransform(self, img):
        """
        Here is where the trick takes place. The image is first normalized an then shrinked until each cell in the ori-
        ginal image corresponds to a single pixel, which we can easily evaluate
        :param img: input image
        :return: outpupt image, a matrix correspondent to the forms
        """
        try:
            # transforms data into single pixels
            imgthresh = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,17,25)
            imgblur = cv2.GaussianBlur(imgthresh,(13,13),0)
            ret,self.imgnormal = cv2.threshold(imgblur,180,255,cv2.THRESH_BINARY)
            imgshrink1 = cv2.resize(self.imgnormal,(37, 95*self.f), interpolation = cv2.INTER_AREA)
            ret,imgshrink1 = cv2.threshold(imgshrink1,180,255,cv2.THRESH_BINARY)
            imgshrink2 = cv2.resize(imgshrink1, (37, 95*self.f), interpolation=cv2.INTER_AREA)
            ret, imgshrink2 = cv2.threshold(imgshrink2, 220, 255, cv2.THRESH_BINARY_INV)
            imgout = imgshrink2[1*self.f:94*self.f, 1:36] #deletes 1 pixel at all margins
            return imgout
        except:
            return "IMGOUT"

    def imgToMatrix(self, img):
        """
        At this point, the image is a matrix of 0 and 255. This function transforms it in a 0 and 1 matrix.
        :param img: input image
        :return: a list of lists
        """
        imgcut = img
        row,col = imgcut.shape


        try:
            #turns 255 values into 1
            for x in range(row):
                for y in range(col):
                    imgcut[x,y] = imgcut[x,y]/255

            for line in range(row):
                imgcut[line] = imgcut[line].tolist()
                #print(imgcut[line])

            batchSize = self.f

            data = []

            count = 0
            batch = []
            for line in range(row):
                if(line%batchSize == batchSize-1):
                    batch.append(imgcut[line].tolist())
                    data.append(batch)
                    batch = []
                else:
                    batch.append(imgcut[line].tolist())

            out = []
            count = 0
            for batch in data:
                if(count%2 == 0):
                    zipped = [(a + b + c + d + e + f + g + h) / 8 for a, b, c, d, e, f, g, h in
                              zip(batch[0], batch[1], batch[2], batch[3],
                                  batch[4], batch[5], batch[6], batch[7])]
                    count += 1
                    out.append(zipped)
                else:
                    count += 1

            for row in range(len(out)):
                for item in range(len(out[row])):
                    if out[row][item] > self.threshold:
                        out[row][item] = 1
                    else:
                        out[row][item] = 0

            return out
        except:
            return "TOMATRIX"

    def dataExtract(self, matrix):
        """
        Retrieves information from matrix
        :param matrix: filtered input image
        :return: ra, month, list of days worked and their indexes
        """
        data = matrix
        ra = []
        period = []
        time = []
        timeFilter = []
        dayIndex = []
        try:
            for line in range(8):
                ra.append(data[line][0:10])
            for line in range(3):
                period.append(data[line][18:30])
            #adds day number at the end of each line

            count = 1
            for line in range(10,47):
                data[line].append(count)
                time.append(data[line])
                count += 1

            for line in range(37):
                sumRow = 0
                for item in time[line][:-1]:
                    sumRow = sumRow + item
                if sumRow > 0 and sumRow != 6: # if true, theres an error in the current line in the image
                    self.dayWithFillError.extend(time[line][-1:])
                elif sumRow == 6:
                    timeFilter.append(time[line][:-1]) #passes only time
                    dayIndex.extend(time[line][-1:])
                    #timeFilter.append(time[line]) #passes day number also
        except:
            return "DATAEXTRACT"
        return ra, period, timeFilter, dayIndex

    def timePositionToValue(self, time):
        """
        Takes the list of completely filled days and retrieves the indexes of the ones in every line.
        [0,0,0,0,1,0,0,1] -> [4,7]

        :param time: list of lists containing only 0s and 1s.
        :return: list of lists containing 6 integers each.
        """
        index = []
        try:
            for line in range(len(time)):
                for item in range(len(time[line])):
                    if time[line][item] == 1:
                        index.append(item)
            count = 0
            timeIndex = []
            b = []
            for item in range(len(index)):
                if count == 5:
                    count = 0
                    b.append(index[item])
                    #b.append()
                    timeIndex = timeIndex + [b]
                    b = []
                else:
                    count = count + 1
                    b.append(index[item])
            return timeIndex
        except:
            return "TIMEREAD"

    def timeCalc(self, time, days):
        """
        Takes the lists of indexes contained in time and calculates the sum of time in the day refferenced in days para-
        meter. Both time and days will always have the same length and its data is related through its indexes, meaning
        that the data in time[0] is related to the day[0].
        This function also detects some sum errors, like having a day with more than 24h or a timeOut lower than timeIn.
        The successfully read days are stored in daysWorked.

        :param time: list of lists containing indexes of days marked in the forms.
        :param days: list of the days that have been marked in the forms.
        :return: the sum of time in the forms.
        """
        totalTime = 0.

        try:
            for line in range(len(time)):
                timeIn = 10*self.pattern[time[line][0]] + self.pattern[time[line][1]] + 0.25*self.pattern[time[line][2]]
                timeOut = 10*self.pattern[time[line][3]] + self.pattern[time[line][4]] + 0.25*self.pattern[time[line][5]]
                dayTime = timeOut - timeIn
                if(timeIn > 23.75 or timeOut > 23.75 or dayTime < 0.0):
                    self.dayWithSumError.append(days[line])
                else:
                    self.daysWorked.append(days[line])
                    totalTime += dayTime
            return totalTime
        except:
            return 0

    def dataRead(self, ra, period):
        """
        Retrieves the data contained in the header (RA and Period).
        :param ra: list of 8 lists, each list containing 9 zeroes and 1 one.
        :param period: list of 3 lists containing data related to the year and month.
        :return: strings containing RA, Period and Year as read in the header.
        """
        raStr = ''
        periodStr = ''
        yearStr = ''

        try:
            #Reads RA
            for line in ra:
                raStr = raStr + str(line.index(1))
            periodStr = self.months[period[2].index(1)]
            yearStr = str(period[0].index(1)+1) + str(period[1].index(1)+1)
        except:
            pass
        return raStr, periodStr, yearStr


class ImgRead(FormCV):
    """
    Extends FormCV class and actually runs it.
    """
    def __init__(self, file):
        super(ImgRead, self).__init__()
        self.status = True
        self.terminalError = False
        self.dayWorked = []
        self.dayWithError = []
        self.hasWarnings = False
        self.hasFillError = False
        self.hasSumError = False
        self.hasHeaderError = False
        self.file = file
        self.imgUndist = self.imgUndistort(self.file)
        if(len(self.imgUndist) != len("IMGUNDIST")):
            self.imgOut = self.imgTransform(self.imgUndist)
        else:
            self.status = False
            self.imgOut = []
        if(self.imgOut != "IMGOUT" and self.status):
            self.imgData = self.imgToMatrix(self.imgOut)
        else:
            self.status = False
            self.imgData = []
        if(self.imgData != "TOMATRIX" and self.status):
            try:
                self.raRaw, self.periodRaw, self.timeRaw, self.dayIndex = self.dataExtract(self.imgData)
                self.timeRead = self.timePositionToValue(self.timeRaw)
                self.time = self.timeCalc(self.timeRead, self.dayIndex)
                self.ra, self.period, self.year = self.dataRead(self.raRaw, self.periodRaw)
            except:
                self.status = False
        self.errorType = self.errorFinder()
        self.dayWithError.extend(self.dayWithFillError)
        self.dayWithError.extend(self.dayWithSumError)
        if(len(self.dayWithError) > 0):
            self.hasWarnings = True
        if(len(self.dayWithSumError) > 0):
            self.hasSumError = True
        if(len(self.dayWithFillError) > 0):
            self.hasFillError = True
        if(len(self.imgUndist) != len("IMGUNDIST")):
            self.imgAnottated = self.grayToBGR(self.imgnormal)
        else:
            self.imgAnottated = None
        self.db = DBhandler()
        self.getAnottatedImage(x=self.imgPreviewSize)
        self.info = self.getInfo()
        self.log = self.getLog()

            
            
    def errorFinder(self):
        """
        Finds the errors in the image reading process
        :return: list of errors
        """
        errors = []
        if(len(self.imgUndist) == len("IMGUNDIST")):
            errors.append(self.imgUndist)
            self.terminalError = True
            return errors
        if(len(self.imgOut) == len("IMGOUT")):
            errors.append(self.imgOut)
            self.terminalError = True
            return errors
        if(len(self.imgData) == len("TOMATRIX")):
            errors.append(self.imgData)
            self.terminalError = True
            return errors
        for line in self.raRaw:
            if (line.count(1) != 1):
                errors.append("RA")
                self.hasHeaderError = True
        for line in self.periodRaw:
            if (line.count(1) != 1):
                errors.append("PERIOD")
                self.hasHeaderError = True
        return errors

    def grayToBGR(self, src):
        """
        Transforms image from grayscale to BGR
        :param src: source image
        :return: BGR image
        """
        return cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)

    def resizeImg(self, src, height):
        """
        Resizes image keeping the aspect ratio
        :param src: source image
        :param height: target height
        :return: resized image
        """
        factor = height/src.shape[0]
        return cv2.resize(src, dsize=None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)

    def getAnottatedImage(self, x=5):
        """
        Anottates image with errors encountered.
        :param x: resizing factor
        :return:
        """
        try:
            self.imgAnottated = self.resizeImg(self.imgAnottated, 95 * x)
            if("RA" in self.errorType):
                self.imgAnottated = cv2.rectangle(self.imgAnottated, (x,1), (17*x,17*x), (0,0,250), 4)
            else:
                self.imgAnottated = cv2.rectangle(self.imgAnottated, (x, 1), (17*x,17*x), (250, 0, 0), 3)
            if("PERIOD" in self.errorType):
                self.imgAnottated = cv2.rectangle(self.imgAnottated, (28*x,1), (49*x,7*x), (0,0,250), 4)
            else:
                self.imgAnottated = cv2.rectangle(self.imgAnottated, (28*x,1), (49*x,7*x), (250, 0, 0), 3)
            for line in range(1,38):
                self.imgAnottated = cv2.line(self.imgAnottated,
                                                 (x,19*x + int(x/2) + line*x*2),
                                                 (self.imgAnottated.shape[1]-x,19*x + int(x/2)+ line*x*2),
                                                 (150,150,150), thickness=3)
            if(len(self.dayWithError) > 0):
                for day in self.dayWithError:
                    self.imgAnottated = cv2.line(self.imgAnottated,
                                                 (x,19*x + int(x/2) + day*x*2),
                                                 (self.imgAnottated.shape[1]-x,19*x + int(x/2)+ day*x*2),
                                                 (0,0,250), thickness=4)
            if (len(self.daysWorked) > 0):
                for day in self.daysWorked:
                    self.imgAnottated = cv2.line(self.imgAnottated,
                                                 (x, 19 * x + int(x / 2) + day * x * 2),
                                                 (self.imgAnottated.shape[1] - x, 19 * x + int(x / 2) + day * x * 2),
                                                 (0, 250, 0), thickness=3)
        except:
            pass

    def logAppend(self, txt):
        """
        Appends a string to the errorLog.
        :param txt: string with some log information.
        :return: nothing
        """
        self.errorLog.append(txt)

    def saveImg(self, dir, img):
        """
        Saves image to disk.
        :param dir: directory in which the img should be saved
        :param img: image to be saved
        :return:
        """
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        currentTime = currentTime[:14]
        if(self.status):
            ra = str(self.ra)
        else:
            ra = "x"
        path = os.path.join(dir, (ra + "-" + currentTime + ".jpg"))
        cv2.imwrite(path, img)

    def getInfo(self):
        """
        Gets info from the read image
        :return: info gathered
        """
        info = {'IMG': [],
                'RA': [],
                'NOME': [],
                'CONSULTORIA': [],
                'MES': [],
                'ANO': [],
                'HORAS': []}
        info['IMG'].append(self.file)
        try:
            year = "20" + str(self.year)
            checkOverwrite = False
            if not self.terminalError:
                checkOverwrite = self.db.checkOverwriting(self.ra, self.period, year)
            info['RA'].append(self.ra)
            info['MES'].append(self.period)
            if checkOverwrite is not False:
                txt = str(checkOverwrite['entry_time'])
                txt = str(txt[6:8]
                          + '/'
                          + txt[4:6]
                          + '/'
                          + txt[:4]
                          + ' - '
                          + txt[8:10]
                          + ':'
                          + txt[10:12]
                          + ':'
                          + txt[12:14])
                info['MES'][0] += (" - Última leitura realizada em " + txt)
            info['ANO'].append(self.year)
            info['HORAS'].append(str(self.time))
            if checkOverwrite is not False:
                txt = str(checkOverwrite['time'])
                info['HORAS'][0] += (" [" + txt + "]")
            consultant = self.db.retrieveConsultant(self.ra)
            if(consultant is not False):
                info['NOME'].append(consultant['NOME'])
                info['CONSULTORIA'].append(consultant['CONSULTORIA'])
            else:
                info['NOME'].append('?')
                info['CONSULTORIA'].append('?')
        except:
            info['RA'].append('?')
            info['MES'].append('?')
            info['ANO'].append('?')
            info['HORAS'].append('?')
            info['NOME'].append('?')
            info['CONSULTORIA'].append('?')
        return info

    def getLog(self):
        """
        Gathers log info
        :return: log
        """
        log = []
        log.append("IMAGEM: " + self.file)
        if (self.status):
            log.append("    RA: " + str(self.ra))
            log.append("    NOME: " + str(self.info['NOME'][self.info['RA'].index(self.ra)]))
            log.append("    CONSULTORIA: " + str(self.info['CONSULTORIA'][self.info['RA'].index(self.ra)]))
            log.append("    PERIODO: " + str(self.info['MES'][0]))
            log.append("    ANO: 20" + str(self.year))
            log.append("    HORAS: " + str(self.info['HORAS'][0]))
            if(self.hasFillError or self.hasSumError):
                self.warnings += 1
                if(self.hasFillError):
                    log.append("        Dias com erros de preenchimento: " + str(self.dayWithFillError))
                if(self.hasSumError):
                    log.append("        Dias com horas erradas: " + str(self.dayWithSumError))
        else:
            self.errors += 1
        if("RA" in self.errorType):
            log.append("    Erro de preenchimento no RA.")
        elif(not self.inDatabase):
            log.append("    RA não encontrado no banco de dados.")
        if("PERIOD" in self.errorType):
            log.append("    Erro de preenchimento no Período.")
        if(self.terminalError):
            log.append("    Imagem não reconhecida.")
        return log


class FileReader():
    """
    Used to unite info from different parts of the program (database, read images), save info and write the log file.
    """
    def __init__(self, forms):
        self.var = Var()
        self.db = DBhandler()
        self.io = errorLogHandler()
        self.numImages = len(forms)
        self.forms = forms
        self.writeInfo()
        self.log = self.getLog()
        self.outputLog()

    def writeInfo(self):
        """
        Stores the info gathered from the last reading in the database.
        :return:
        """
        try:
            for form in self.forms:
                if(not form.terminalError):
                    if (len(form.errorType) == 0) and (str(form.ra) in self.db.raColStr):
                        self.db.docWriter(form.ra, ('20' + str(form.year)), form.period, form.time)
                    elif(str(form.ra) in self.db.raColStr):
                        form.inDatabase = False
            return True
        except:
            return False

    def logAppend(self, txt):
        """
        Appends a string to the errorLog.
        :param txt: string with some log information.
        :return: nothing
        """
        self.var.errorLog.append(txt)

    def getLog(self):
        """
        Retrieves the log from the forms.
        :return: error log
        """
        errorLog = []
        for form in self.forms:
            errorLog.extend(form.log)
            errorLog.append("")
        return errorLog

    def outputLog(self):
        """
        Saves 2 copies of the error log file.
        :return:
        """
        self.io.errorLogWriter(self.log)
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        self.io.errorLogExporter(os.path.join(self.var.logDir,
                                              (self.var.errorLogFile[:-4]
                                               + currentTime[:14]
                                               + ".txt")))

    def logToStr(self, log):
        """
        Transforms the lists contained in the log into string.
        :param log: error log list
        :return:
        """
        logList = log
        logStr = ""
        for line in logList:
            logStr = logStr + line + "\n"
        return logStr