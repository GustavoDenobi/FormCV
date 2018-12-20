import cv2
import numpy as np
import os
import pyexcel as pe
import configparser
import shutil
from datetime import datetime
import unicodedata
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import textwrap

VERSION = '2.0.0'

creditText = ('Este aplicativo foi criado e desenvolvido em 2018 por Gustavo F. A. Denobi, consultor pela iNOVEC. \n'
                  'Agradecimentos especiais ao ICETI e à UNICESUMAR, pela oportunidade de aprendizado no processo '
                  'de desenvolvimento deste aplicativo.\n\n'
                  'O uso deste aplicativo e todo o seu conteúdo está totalmente sujeito a autorização do autor.\n\n'
                  'Contato: gustavodenobi@gmail.com\n\n'
                  'Versão: ' + VERSION
                  )




def errorPopup():
    """ Returns an error message in a popup """
    print('ERROR')


def textPopup(txt):
    """ Receives a string and creates a popup with it's text """
    print(txt)


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
        self.threshold = float(config['const']['threshold'])
        self.imgDir = config['const']['imgDir']
        self.minimumHours = int(config['const']['minimumHours'])
        self.certificateDir = config['const']['certificateDir']
        self.errorLog = []  # Used to store a sequence of lines which contain details about every read image
        self.errors = 0  # Number of errors to be used in the error log
        self.warnings = 0  # NUmber of filling errors to be used in the error log
        self.inDatabase = True # To check if a RA was found in the database

    def checkBackup(self):
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

            shutil.copy(self.databaseFile, os.path.join(backupDir + os.sep + str(currentTime)) + ".csv")
            return True
        else:
            return False

    def refreshParams(self):
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

    # pattern: Defines the values of every cell in a row in the time field of the forms
    # months: defines the standard name for converting the number of a month to a key, which is the same of the database
    # w: width of imgUndist, which is the undistorted version of the input
    # h: height of imgUndist, which is the undistorted version of the input
    # coordOrder: used in getCoordOrder, defines the order of the 4 points of the image contour to be undistorted
    # cvFormats: formats that opencv is able to handle
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
        self.consultantIndex = 0  # whenever a operation finds a consultant index, it is stored here
        self.dbdict = self.readDatabaseDict()  # stores the database as e dict where the key is the label of each row
        self.length = len(self.dbdict['NOME'])  # number of consultants in database
        self.raColInt = self.dbdict['RA']
        self.raCol = self.intToStr(self.raColInt)  # stores the list of RAs
        self.nameCol = self.dbdict['NOME']  # stores the list of names
        self.consultCol = self.dbdict['CONSULTORIA']  # stores the list of consulting names
        self.consultList = sorted(set(self.consultCol))

    def intToStr(self, intList):
        strList = []
        for item in intList:
            strList.append(str(item))
        return strList

    def readDatabaseDict(self):
        """ Used to read a csv file and return it as a dict in which the keys are the labels of each column and the
        values are lists related to each label
        """
        try:
            return pe.get_dict(file_name = self.databaseFile, encoding = 'utf-8-sig')
        # encoding = 'utf-8-sig' -> prevent the 'RA' to become '\ufeffRA' when the database is read
        except:
            return {"RA" : ["ARQUIVO INEXISTENTE"],
                    "NOME" : ["ARQUIVO INEXISTENTE"],
                    "CONSULTORIA" : ["ARQUIVO INEXISTENTE"]}

    def readDatabaseSheet(self):
        """ Used to read a csv file and return it as a sheet. Information is accessed by pyexcel methods"""
        db = pe.get_sheet(file_name=self.databaseFile, encoding='utf-8-sig')
        db.name_rows_by_column(0)
        return db

    def cellWriter(self, ra, period, time):
        """ Writes a consultant's info in the database. Expects the RA to be already in the database
        str ra: 8-number string conataining the RA
        str period: 3-letter code according to Var.months
        float time: sum of time of a consultant in a month
        """
        self.consultantIndex = self.raCol.index(str(ra))
        self.dbdict[period][self.consultantIndex] = time

    def saveDB(self):
        """ Gets the dict from self.dbdict and saves it in the databaseFile"""
        database = pe.get_sheet(adict = self.dbdict)
        database.save_as(self.databaseFile)

    def retrieveConsultant(self, consultantRA):
        """ Searches the database for the given RA number and returns a dict with its name and consulting
        str consultantRA: the RA to be searched
        """
        try:
            self.consultantIndex = self.raCol.index(str(consultantRA))
            return {'RA': self.raCol[self.consultantIndex],
                    'NOME': self.nameCol[self.consultantIndex],
                    'CONSULTORIA': self.consultCol[self.consultantIndex]}
        except:
            return False

    def exportDB(self, address): # Gets a dict and transforms it into a csv output
        """ Used to create SaidaParaCertificados.csv, which feeds the certificates.
        str address: path to the outputed csv file
        """
        database = pe.get_sheet(adict = self.dbdict)
        database.save_as(address)

    def saveConsultant(self, consultant):
        """
        Appends a new consultant to the database
        :param consultant: dict containing consultant's ra, consulting and name
        """
        status = True  # turns to false if the input data is invalid
        for key in consultant.keys():
            if consultant[key] == '':  # checks if all fields are filled
                status = False
        if(not consultant['RA'].isdigit()):  # checks if RA is number
            status = False
        if(not len(consultant['RA']) == 8):  # checks if RA has 8 numbers
            status = False
        if(status):  # if validation passed, proceed
            if(int(consultant['RA']) in self.dbdict['RA']):  # checks if consultant is already in database
                try:
                    index = self.dbdict["RA"].index(int(consultant["RA"]))
                    self.dbdict["NOME"][index] = consultant["NOME"]
                    self.dbdict["CONSULTORIA"][index] = consultant["CONSULTORIA"]
                    self.saveDB()
                    return 1
                except:
                    return 0
            else:
                try:  # adds consultant to the database
                    for key in consultant.keys():
                        self.dbdict[key].append(consultant[key])
                    for key in self.months:
                        self.dbdict[key].append(0)
                    self.saveDB()
                    return 1
                except:
                    return 0

    def delConsultant(self, consultantRA):
        """
        Deletes a consultant according to its given RA
        :param consultantRA: string containing the consultant's RA
        """
        try:
            db = self.readDatabaseSheet()
            del db.row[consultantRA]
            db.save_as(self.databaseFile)
            textPopup("Consultor removido!")
        except:
            errorPopup()


class pdfCreator():

    def __init__(self, certificateInfo, dir):
        self.template = Image.open("img\\template.png")
        self.draw = ImageDraw.Draw(self.template)
        self.x = 500
        self.y = 800
        self.certificateInfo = certificateInfo
        self.writeText(self.certificateInfo)
        self.savePDF(dir)


    def writeText(self, fdict):
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
            self.draw.text((self.x, self.y + linespace), line, (0, 0, 0), font=selectFont)
            linespace += 88

    def writeDate(self):
        pass

    def savePDF(self, dir):
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

    def __init__(self, months, consult):
        super(certificateGenerator, self).__init__()
        self.fdict = {"RA" : "",
                      "NOME" : "",
                      "CONSULTORIA" : "",
                      "TOTAL" : "",
                      "MES1" : "",
                      "MES2" : "",
                      "ANO" : ""}
        self.months = months
        self.certToGenerate = self.filterSumTime(months, consult)
        self.certCount = len(self.certToGenerate["RA"])

    def filterSumTime(self, months, consult):
        output = {'RA': self.dbdict['RA'],
                  'NOME': self.dbdict['NOME'],
                  'CONSULTORIA': self.dbdict['CONSULTORIA'],
                  'TOTAL': ([0] * self.length)}

        for i in range(len(self.dbdict['NOME'])):
            if(consult == "Todas"):
                sumTime = self.dbdict[months[0]][i] + self.dbdict[months[1]][i]
                if (sumTime % 1) <= 0.5:
                    sumTime = int(sumTime)
                else:
                    sumTime = int(sumTime) + 1
                output['TOTAL'][i] = sumTime
            elif(self.dbdict["CONSULTORIA"][i] == consult):
                sumTime = self.dbdict[months[0]][i] + self.dbdict[months[1]][i]
                if (sumTime % 1) <= 0.5:
                    sumTime = int(sumTime)
                else:
                    sumTime = int(sumTime) + 1
                output['TOTAL'][i] = sumTime

        newoutput = {'RA': [],
                     'NOME': [],
                     'CONSULTORIA': [],
                     'TOTAL': []}

        # The following loop selects only the consultants with more than 20 hours in the selected 2 months
        for i in range(len(self.dbdict['NOME'])):
            if (output['TOTAL'][i] >= float(self.minimumHours)):
                for key in output.keys():
                    newoutput[key].append(output[key][i])
        return newoutput

    def saveCertificate(self, index):
        currentCertificate = self.fdict
        currentCertificate["RA"] = str(self.certToGenerate["RA"][index])
        currentCertificate["NOME"] = self.certToGenerate["NOME"][index]
        currentCertificate["CONSULTORIA"] = self.certToGenerate["CONSULTORIA"][index]
        currentCertificate["MES1"] = self.monthTrans[self.months[0]]
        currentCertificate["MES2"] = self.monthTrans[self.months[1]]
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        currentCertificate["ANO"] = currentTime[0:4]
        pdfCreator(currentCertificate, self.certificateDir)

    def saveCertificates(self):
        for current in range(len(self.certToGenerate["RA"])):
            currentCertificate = self.fdict
            currentCertificate["RA"] = str(self.certToGenerate["RA"][current])
            currentCertificate["NOME"] = self.certToGenerate["NOME"][current]
            currentCertificate["CONSULTORIA"] = self.certToGenerate["CONSULTORIA"][current]
            currentCertificate["MES1"] = self.monthTrans[self.months[0]]
            currentCertificate["MES2"] = self.monthTrans[self.months[1]]
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
        try:
            n = np.fromfile(filename, dtype)
            img = cv2.imdecode(n, flags)
            return img
        except Exception as e:
            print(e)
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
        return cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)

    def resizeImg(self, src, height):
        factor = height/src.shape[0]
        return cv2.resize(src, dsize=None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)

    def getAnottatedImage(self, x=5):
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
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        currentTime = currentTime[:14]
        if(self.status):
            ra = str(self.ra)
        else:
            ra = "x"
        path = os.path.join(dir, (ra + "-" + currentTime + ".jpg"))
        cv2.imwrite(path, img)

    def getInfo(self):
        info = {'IMG': [],
                'RA': [],
                'NOME': [],
                'CONSULTORIA': [],
                'MES': [],
                'ANO': [],
                'HORAS': []}
        info['IMG'].append(self.file)
        try:
            info['RA'].append(self.ra)
            info['MES'].append(self.period)
            info['ANO'].append(self.year)
            info['HORAS'].append(str(self.time))
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
        log = []
        log.append("IMAGEM: " + self.file)
        if (self.status):
            log.append("    RA: " + self.ra)
            log.append("    NOME: " + self.info['NOME'][self.info['RA'].index(self.ra)])
            log.append("    CONSULTORIA: " + self.info['CONSULTORIA'][self.info['RA'].index(self.ra)])
            log.append("    PERIODO: " + self.period)
            log.append("    ANO: " + self.year)
            log.append("    HORAS: " + str(self.time))
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
        for form in self.forms:
            if(not form.terminalError):
                if (len(form.errorType) == 0) and (str(form.ra) in self.db.raCol):
                    self.db.cellWriter(form.ra, form.period, form.time)
                elif(str(form.ra) in self.db.raCol):
                    form.inDatabase = False

    def logAppend(self, txt):
        """
        Appends a string to the errorLog.
        :param txt: string with some log information.
        :return: nothing
        """
        self.var.errorLog.append(txt)

    def getLog(self):
        errorLog = []
        for form in self.forms:
            errorLog.extend(form.log)
            errorLog.append("")
        return errorLog

    def outputLog(self):
        self.io.errorLogWriter(self.log)
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        self.io.errorLogExporter(os.path.join(self.var.logDir,
                                              (self.var.errorLogFile[:-4]
                                               + currentTime[:14]
                                               + ".txt")))

    def logToStr(self, log, numOfLines = 25):
        logList = log
        #for item in range(numOfLines - len(logList)):
        #    logList.append("")
        logStr = ""
        for line in logList:
            logStr = logStr + line + "\n"
        return logStr

    def saveDB(self):
        try:
            self.db.saveDB()
            return True
        except:
            return False

