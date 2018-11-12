from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, StringProperty
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
import cv2
import numpy as np
import os
import pyexcel as pe
import configparser
import shutil
from datetime import datetime
import unicodedata

VERSION = '1.0.2'

creditText = ('Este aplicativo foi criado e desenvolvido em 2018 por Gustavo F. A. Denobi, consultor pela iNOVEC. \n'
                  'Agradecimentos especiais ao ICETI e à UNICESUMAR, pela oportunidade de aprender no processo '
                  'de desenvolvimento deste aplicativo.\n\n'
                  'O uso deste aplicativo e todo o seu conteúdo está totalmente sujeito a autorização do autor.\n\n'
                  'Contato: gustavodenobi@gmail.com\n\n'
                  'Versão: ' + VERSION
                  )

def errorPopup():
    popup = Popup(title='FormCV',
                  content=Label(text='Ops! Algo deu errado.'),
                  size_hint=(None, None), size=(400, 200))
    popup.open()


def textPopup(txt):
    popup = Popup(title='FormCV',
                  content=Label(text=txt),
                  size_hint=(None, None), size=(500, 200))
    popup.open()


class Var:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.rootDir = os.path.dirname(__file__)
        self.imgDir = config['const']['imgDir']
        self.imgAddress = config['const']['imgAddress']
        self.databaseFile = config['const']['databaseFile']
        self.errorLogFile = config['const']['errorLogFile']
        self.outputFile = config['const']['outputFile']
        self.imgPreviewSize = int(config['const']['imgPreviewSize'])
        self.numOfFiles = self.fileCount(self.imgDir)
        self.errorLog = []
        self.errors = 0
        self.warnings = 0
        self.status = True

    def paramTuner(self, variable, value):
        config = configparser.ConfigParser()
        config.read('config.ini')
        config['const'][variable] = value
        with open('config.ini', 'w') as configFile:
            config.write(configFile)

    pattern = [0, 1, 2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 0, 0, 1, 2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3]
    months = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
    windowSize = (1000,600)
    w = 37 * 16
    h = 47 * 21
    coordOrder = {0: [0, 0], 1: [w, 0], 2: [w, h], 3: [0, h]}
    cvFormats = ['.jpeg', '.jpg', '.png', '.bmp']

    def fileCount(self, dir):
        fileCount = 0
        for subdir, dirs, files in os.walk(dir):
            for file in files:
                if (file[file.index('.'):] in self.cvFormats):
                    fileCount += 1
        return fileCount


class DBhandler(Var):
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

    def __init__(self):
        super(DBhandler, self).__init__()
        self.consultantRowIndex = 0
        self.dbdict = self.readDatabaseDict()
        self.length = len(self.dbdict['NOME'])
        self.raCol = self.dbdict['RA']
        self.nameCol = self.dbdict['NOME']
        self.consultCol = self.dbdict['CONSULTORIA']

    def readDatabaseDict(self): # Used to read a csv file and store it as a dict
        return pe.get_dict(file_name = self.databaseFile, encoding = 'utf-8-sig')
        # encoding = 'utf-8-sig' -> prevent the 'RA' to become '\ufeffRA' when the database is read

    def readDatabaseSheet(self):
        db = pe.get_sheet(file_name=self.databaseFile, encoding='utf-8-sig')
        db.name_rows_by_column(0)
        return db

    def cellWriter(self, ra, period, time): # Writes the time according to the RA number and the month
        self.consultantRowIndex = self.raCol.index(int(ra))
        self.dbdict[period][self.consultantRowIndex] = time

    def saveDB(self): # Gets a dict and transforms it into a csv output
        database = pe.get_sheet(adict = self.dbdict)
        database.save_as(self.databaseFile)

    def retrieveConsultant(self, consultantRA):
        try:
            consultantIndex = self.raCol.index(consultantRA)
            return {'RA': self.raCol[consultantIndex],
                    'NOME': self.nameCol[consultantIndex],
                    'CONSULTORIA': self.consultCol[consultantIndex],
                    'INDEX': consultantIndex}
        except:
            return False

    def exportDB(self, address): # Gets a dict and transforms it into a csv output
        database = pe.get_sheet(adict = self.dbdict)
        database.save_as(address)

    def addConsultant(self, consultant):
        status = True
        for key in consultant.keys():
            if consultant[key] == '':
                status = False
                textPopup('Preencha todos os campos.')
        if(not consultant['RA'].isdigit()):
            status = False
            textPopup('Preencha o RA com numeros apenas.')
        if(not len(consultant['RA']) == 8):
            textPopup('Preencha o RA com 8 numeros.')
            status = False
        if(status):
            if(int(consultant['RA']) in self.dbdict['RA']):
                consultCheck = self.retrieveConsultant(int(consultant['RA']))
                textPopup("Este RA ja esta cadastrado.\n\nNome: " +
                          consultCheck['NOME'] +
                          "\nConsultoria: " +
                          consultCheck['CONSULTORIA'])
            else:
                try:
                    for key in consultant.keys():
                        self.dbdict[key].append(consultant[key])
                    for key in self.months:
                        self.dbdict[key].append(0)
                    self.saveDB()
                    textPopup("Consultor adicionado com sucesso!")
                except:
                    errorPopup()

    def delConsultant(self, consultantRA):
        try:
            db = self.readDatabaseSheet()
            del db.row[consultantRA]
            db.save_as(self.databaseFile)
            textPopup("Consultor removido!")
        except:
            errorPopup()


class DBoutput(DBhandler):
    def __init__(self, threshold, months):
        super(DBoutput, self).__init__()
        self.certToGenerate = self.filterSumTime(threshold, months)
        self.outputFile, self.certificateCount = self.outputDatabase()

    def filterSumTime(self, threshold, months):
        output = {'RA': self.dbdict['RA'],
                  'NOME': self.dbdict['NOME'],
                  'CONSULTORIA': self.dbdict['CONSULTORIA'],
                  months[0]: self.dbdict[months[0]],
                  months[1]: self.dbdict[months[1]],
                  'TOTAL': ([0] * self.length),
                  'MES1': ([self.monthTrans[months[0]]] * self.length),
                  'MES2': ([self.monthTrans[months[1]]] * self.length)}

        for i in range(len(self.dbdict['NOME'])):
            sumTime = self.dbdict[months[0]][i] + self.dbdict[months[1]][i]
            if (sumTime % 1) <= 0.5:
                sumTime = int(sumTime)
            else:
                sumTime = int(sumTime) + 1
            output['TOTAL'][i] = sumTime

        newoutput = {'RA': [],
                  'NOME': [],
                  'CONSULTORIA': [],
                  months[0]: [],
                  months[1]: [],
                  'TOTAL': [],
                  'MES1': [],
                  'MES2': []}

        # The following loop selects only the consultants with more than 20 hours in the selected 2 months
        for i in range(len(self.dbdict['NOME'])):
            if(output['TOTAL'][i] >= float(threshold)):
                for key in output.keys():
                    newoutput[key].append(output[key][i])
        return newoutput

    def outputDatabase(self):
    # Generates 'SaidaParaCertificados.csv', which is used to feed 'Certificados.docx'

        certificateCount = len(self.certToGenerate['NOME'])
        output = pe.get_sheet(adict = self.certToGenerate) # Transforms the dict created above in csv format
        output.save_as(self.outputFile) # Saves the csv into file

        # sorts SaidaParaCertificados by Consulting names
        b = pe.get_array(file_name = self.outputFile)
        indexConsult = b[0].index('CONSULTORIA')

        def takeSecond(b):
            element = b[indexConsult]
            return element

        sortedList = [b[0]] + sorted(b[1::], key=takeSecond)
        pe.save_as(array=sortedList, dest_file_name=self.outputFile)
        textPopup('Sucesso!\n\n' + str(certificateCount) + ' certificado(s) gerados.')
        return sortedList, certificateCount

    def strip_accents(self, text):
        """
        Strip accents from input String.

        :param text: The input string.
        :type text: String.

        :returns: The processed String.
        :rtype: String.
        """
        text = unicodedata.normalize('NFD', text)
        text = text.encode('ascii', 'ignore')
        text = text.decode("utf-8")
        return str(text)


class IOmethod(Var):
    def __init__(self):
        super(IOmethod, self).__init__()

    def errorLogWriter(self, errors, warnings, errorLog):
        with open(self.errorLogFile, 'w') as file_handler:
            file_handler.write("Erros fatais: {}     ".format(str(errors)))
            file_handler.write("Imagens com erros de preenchimento/soma: {}\n\n".format(str(warnings)))
            for item in errorLog:
                file_handler.write("{}\n".format(item))

    def errorLogExporter(self, dst):
        shutil.copy(self.errorLogFile, dst)


class FormCV(Var):
    def __init__(self):
        super(FormCV, self).__init__()
        self.dayWithFillError = []
        self.dayWithSumError = []
        self.daysWorked = []

    def imgPreview(self, img):
        cv2.imshow('Preview', img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def imgUndistort(self):
        try:
            imggray = cv2.cvtColor(cv2.imread(self.imgAddress), cv2.COLOR_BGR2GRAY)  #import and convert into grayscale
            width, height = imggray.shape
            maxheight = 1024
            maxwidth = int(maxheight/(width/height))
            imgresize = cv2.resize(imggray,(maxwidth, maxheight), interpolation = cv2.INTER_AREA)
            imgblur = cv2.GaussianBlur(imgresize,(9,9),0) #apply gaussian blur
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

            #transforms polygon that contains data into rectangle
            pts1 = np.float32(approx) #coordinates from contour
            pts2 = np.float32(self.getCoordOrder(approx))
            M = cv2.getPerspectiveTransform(pts1,pts2)
            imgundist = cv2.warpPerspective(imgresize,M,(self.w, self.h))
            return imgundist
        except:
            return "IMGUNDIST"
    
    def getCoordOrder(self, array):
        sumofcoorda = []
        sumofcoordb = []
        for a in array:
            for b in a:
                partial = 0
                for coord in b:
                    partial = partial + coord
                sumofcoorda.append(partial)
                sumofcoordb.append(partial)
        tl = sumofcoorda.index(min(sumofcoorda))
        br = sumofcoorda.index(max(sumofcoorda))
        sumofcoordb.remove(min(sumofcoorda))
        sumofcoordb.remove(max(sumofcoorda))
        tr = sumofcoorda.index(min(sumofcoordb))
        bl = sumofcoorda.index(max(sumofcoordb))
        ordered = [[self.coordOrder[tl]],[self.coordOrder[tr]],[self.coordOrder[br]],[self.coordOrder[bl]]]
        return ordered

    def imgTransform(self, img):
        try:
            # transforms data into single pixels
            imgthresh = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,17,25)
            imgblur = cv2.GaussianBlur(imgthresh,(13,13),0)
            ret,imgthresh = cv2.threshold(imgblur,180,255,cv2.THRESH_BINARY)
            imgresized = cv2.resize(imgthresh,(37, 95), interpolation = cv2.INTER_AREA)
            ret,imgthresh = cv2.threshold(imgresized,192,255,cv2.THRESH_BINARY_INV)
            imgout = imgthresh[1:94, 1:36] #deletes 1 pixel at all margins
            return imgout
        except:
            return "IMGOUT"

    def imgToMatrix(self, img):
        imgcut = img
        row,col = imgcut.shape

        try:
            #turns 255 values into 1
            for x in range(row):
                for y in range(col):
                    imgcut[x,y] = imgcut[x,y]/255

            #delete odd lines (blank)
            data = []
            for line in range(93):
                if line%2 == 0:
                    data.append(imgcut[line].tolist())
            #Returns matrix of 0s and 1s

            return data
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

            #adds day number in the end of each line
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
    def __init__(self):
        super(ImgRead, self).__init__()
        self.status = True
        self.terminalError = False
        self.imgUndist = self.imgUndistort()
        self.dayWorked = []
        self.dayWithError = []
        self.hasWarnings = False
        self.hasFillError = False
        self.hasSumError = False
        if(self.imgUndist != "IMGUNDIST"):
            self.imgOut = self.imgTransform(self.imgUndist)
        else:
            self.status = False

        if(self.imgOut != "IMGOUT" and self.status):
            self.imgData = self.imgToMatrix(self.imgOut)
        else:
            self.status = False
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
        self.imgAnottated = self.grayToBGR(self.imgUndist)
            
            
    def errorFinder(self):
        errors = []
        if(self.imgUndist == "IMGUNDIST"):
            errors.append(self.imgUndist)
            self.terminalError = True
            return errors
        if(self.imgOut == "IMGOUT"):
            errors.append(self.imgOut)
            self.terminalError = True
            return errors
        if(self.imgData == "TOMATRIX"):
            errors.append(self.imgData)
            self.terminalError = True
            return errors
        for line in self.raRaw:
            if (line.count(1) != 1):
                errors.append("RA")
        for line in self.periodRaw:
            if (line.count(1) != 1):
                errors.append("PERIOD")
        return errors

    def grayToBGR(self, src):
        return cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)

    def resizeImg(self, src, height):
        factor = height/src.shape[0]
        return cv2.resize(src, dsize=None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)

    def getAnottatedImage(self, x=5):
        self.imgAnottated = self.resizeImg(self.imgAnottated, 95 * x)
        if("RA" in self.errorType):
            self.imgAnottated = cv2.rectangle(self.imgAnottated, (x,1), (17*x,17*x), (0,0,250), 2)
        else:
            self.imgAnottated = cv2.rectangle(self.imgAnottated, (x, 1), (17*x,17*x), (250, 0, 0), 1)
        if("PERIOD" in self.errorType):
            self.imgAnottated = cv2.rectangle(self.imgAnottated, (28*x,1), (49*x,7*x), (0,0,250), 2)
        else:
            self.imgAnottated = cv2.rectangle(self.imgAnottated, (28*x,1), (49*x,7*x), (250, 0, 0), 1)
        for line in range(1,38):
            self.imgAnottated = cv2.line(self.imgAnottated,
                                             (x,19*x + int(x/2) + line*x*2),
                                             (self.imgAnottated.shape[1]-x,19*x + int(x/2)+ line*x*2),
                                             (150,150,150), thickness=1)
        if(len(self.dayWithError) > 0):
            for day in self.dayWithError:
                self.imgAnottated = cv2.line(self.imgAnottated,
                                             (x,19*x + int(x/2) + day*x*2),
                                             (self.imgAnottated.shape[1]-x,19*x + int(x/2)+ day*x*2),
                                             (0,0,250), thickness=1)
        if (len(self.daysWorked) > 0):
            for day in self.daysWorked:
                self.imgAnottated = cv2.line(self.imgAnottated,
                                             (x, 19 * x + int(x / 2) + day * x * 2),
                                             (self.imgAnottated.shape[1] - x, 19 * x + int(x / 2) + day * x * 2),
                                             (0, 250, 0), thickness=1)
        self.imgPreview(self.imgAnottated)


class FileReader():

    def __init__(self, multiple=True, imgAddress = "", showErrorImage = False, showPreviews = False):
        self.multi = multiple
        self.showErrorImage = showErrorImage
        self.showPreviews = showPreviews
        self.var = Var()
        self.db = DBhandler()
        self.io = IOmethod()
        if(self.multi):
            self.filesToRead = self.getFilesToRead()
        else:
            self.filesToRead = [imgAddress]
        self.readImages()

    def getFilesToRead(self):
        fileList = []
        for subdir, dirs, files in os.walk(self.var.imgDir):
            for file in files:
                filepath = subdir + os.sep + file
                if (file[file.index('.'):] in self.var.cvFormats):
                    fileList.append(filepath)
        return fileList

    def outputInfo(self):
        try:
            self.io.errorLogWriter(self.var.errors, self.var.warnings, self.var.errorLog)
            self.db.saveDB()
            if(self.multi):
                currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
                self.io.errorLogExporter(os.path.join(self.var.imgDir, (self.var.errorLogFile[:-4] + currentTime[:14] + ".txt")))
                textPopup('Imagens lidas: ' +
                          str(self.var.numOfFiles) +
                          '\nErros fatais: ' +
                          str(self.var.errors) +
                          '\nImagens com erros de preenchimento: ' +
                          str(self.var.warnings))
            else:
                textPopup("Leitura completa. Confira detalhes no relatorio.")
        except:
            textPopup("Algo deu errado ao salvar o banco de dados.\nCertifique-se de que o arquivo esta fechado.")

    def readImages(self):
        for file in self.filesToRead:
            self.var.paramTuner('imgAddress', file)
            self.var.errorLog.append('IMG: ' + file)
            imgRead = ImgRead()
            if(self.showErrorImage):
                imgRead.getAnottatedImage(x=self.var.imgPreviewSize)
            if (imgRead.status):
                self.var.errorLog.append("    RA: " + imgRead.ra)
                self.var.errorLog.append("    PERIODO: " + imgRead.period)
                self.var.errorLog.append("    HORAS: " + str(imgRead.time))
                if(imgRead.hasFillError):
                    self.var.errorLog.append("        Dias com erros de preenchimento: " + str(imgRead.dayWithFillError))
                if(imgRead.hasSumError):
                    self.var.errorLog.append("        Dias com horas erradas: " + str(imgRead.dayWithSumError))
                if(len(imgRead.errorType) == 0):
                    try:
                        self.db.cellWriter(imgRead.ra, imgRead.period, imgRead.time)
                    except:
                        self.var.errorLog.append('    ERRO: nao foi possivel encontrar o RA no banco de dados.')
                        self.var.errors += 1
                else:
                    if ("RA" in imgRead.errorType):
                        self.var.errorLog.append("    Erro de preenchimento no RA.")
                    if ("PERIOD" in imgRead.errorType):
                        self.var.errorLog.append("    Erro de preenchimento no Periodo.")
                    self.var.errors += 1
            elif (imgRead.terminalError):
                self.var.errorLog.append("    Imagem nao foi reconhecida.")
                self.var.errors += 1
            if imgRead.hasWarnings:
                self.var.warnings += 1
            self.var.errorLog.append("")
        self.outputInfo()

# KIVY

Window.size = Var.windowSize

class MainMenu(Screen):
    
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)


class ChangeDatabaseDialog(FloatLayout):
    loadDatabase = ObjectProperty(None)
    cancel = ObjectProperty(None)
    
    class Text(Widget):
        databaseFile = StringProperty(Var().databaseFile)
        
    text = Text()
    
    def textUpdate(self):
        self.text.datbaseFile = Var().databaseFile


class ChangeImgDialog(FloatLayout):
    loadImg = ObjectProperty(None)
    cancel = ObjectProperty(None)
    
    class Text(Widget):
        imgDir = StringProperty(Var().imgDir)
        
    text = Text()
    
    def textUpdate(self):
        self.text.imgDir = Var().imgDir


class ChangeOutputDialog(FloatLayout):
    loadOutput = ObjectProperty(None)
    cancel = ObjectProperty(None)

    class Text(Widget):
        outputFile = StringProperty(Var().outputFile)
        
    text = Text()
    
    def textUpdate(self):
        self.text.outputFile = Var().outputFile


class SaveErrorLogDialog(FloatLayout):
    saveErrorLog = ObjectProperty(None)
    cancel = ObjectProperty(None)

    class Text(Widget):
        imgDir = StringProperty(Var().imgDir)
        
    text = Text()
    
    def textUpdate(self):
        self.text.imgDir = Var().imgDir


class Options(Screen):
    var = Var()

    class Text(Widget):
        var = Var()
        dbDir = StringProperty(var.databaseFile)
        imgDir = StringProperty(var.imgDir)
        elDir = StringProperty(var.errorLogFile)
        outputDir = StringProperty(var.outputFile)

    text = Text()

    def textUpdate(self):
        var = Var()
        self.text.dbDir = var.databaseFile
        self.text.imgDir = var.imgDir
        self.text.elDir = var.errorLogFile
        self.text.outputDir = var.outputFile
    
    def dismiss_popup(self):
        self._popup.dismiss()
    
    def show_load_database(self):
        content = ChangeDatabaseDialog(loadDatabase=self.changeDatabase, cancel=self.dismiss_popup)
        self._popup = Popup(title="Selecione um arquivo", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
    
    def show_load_imgDir(self):
        content = ChangeImgDialog(loadImg=self.changeImgDir, cancel=self.dismiss_popup)
        self._popup = Popup(title="Selecione uma pasta", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def show_load_output(self):
        content = ChangeOutputDialog(loadOutput=self.changeOutput, cancel=self.dismiss_popup)
        self._popup = Popup(title="Selecione uma pasta", content=content,
                            size_hint=(0.9, 0.9))
        
    def changeDatabase(self, path, filename):
        if(filename != []):
            self.var.paramTuner('databaseFile', os.path.join(path, filename[0]))
        self.textUpdate()
        self.dismiss_popup()        
        
    def changeImgDir(self, path, filename):
        if(filename != []):
            self.var.paramTuner('imgDir', os.path.join(path, filename[0]))
        self.textUpdate()
        self.dismiss_popup()
        
    def changeOutput(self, path, filename):
        if(filename != []):
            self.var.paramTuner('outputFile', os.path.join(path, filename[0]))
        self.textUpdate()
        self.dismiss_popup()


class RMFmenu(Screen):
    var = Var()

    class Info(Widget):
        var = Var()
        imgDir = StringProperty(var.imgDir)
        numOfFiles = StringProperty(str(var.numOfFiles))
    
    info = Info()
    
    def infoUpdate(self):
        var = Var()
        self.info.imgDir = var.imgDir
        self.info.numOfFiles = str(var.numOfFiles)
    
    def dismiss_popup(self):
        self._popup.dismiss()    
    
    def show_load_imgDir(self):
        content = ChangeImgDialog(loadImg=self.changeImgDir, cancel=self.dismiss_popup)
        self._popup = Popup(title="Carregar Pasta", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def changeImgDir(self, path, filename):
        self.var.paramTuner('imgDir', os.path.join(path, filename[0]))
        self.infoUpdate()
        self.dismiss_popup()
    
    def rmf(self):
        FileReader()


class ChooseRSF(FloatLayout):
    loadRSF = ObjectProperty(None)
    cancel = ObjectProperty(None)

    class Text(Widget):
        imgDir = StringProperty(Var().imgDir)
        
    text = Text()
    
    def textUpdate(self):
        self.text.imgDir = Var().imgDir


class RSFmenu(Screen):
    
    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load_rsf(self):
        content = ChooseRSF(loadRSF=self.runRSF, cancel=self.dismiss_popup)
        content.textUpdate()
        self._popup = Popup(title="Selecione Imagem", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
        
    def runRSF(self, path, filename):
        filepath = os.path.join(path, filename[0])
        FileReader(multiple=False, imgAddress=filepath, showErrorImage=True)
        self.dismiss_popup()


class Credit(Screen):
    
    creditText = ('Este aplicativo foi criado e desenvolvido em 2018 por Gustavo F. A. Denobi, consultor pela iNOVEC. \n'
                  'Agradecimentos especiais ao ICETI e à UNICESUMAR, pela oportunidade de aprender no processo '
                  'de desenvolvimento deste aplicativo.\n\n'
                  'O uso deste aplicativo e todo o seu conteúdo está totalmente sujeito a autorização do autor.\n\n'
                  'Contato: gustavodenobi@gmail.com\n\n'
                  'Versão: ' + VERSION
                  )


class ManageConsultant(Screen):
    consultant = {'RA': '',
                  'NOME': '',
                  'CONSULTORIA': ''}
    
    def bindRA(self, ra):
        self.consultant['RA'] = ra
        
    def bindNOME(self, nome):
        self.consultant['NOME'] = nome
        
    def bindCONSULT(self, consult):
        self.consultant['CONSULTORIA'] = consult

    def runAddConsultant(self):
        DBhandler().addConsultant(self.consultant)
            
            
    def runDelConsultant(self):
        status = True
        if(not self.consultant['RA'].isdigit()):
            status = False
            textPopup('Preencha o RA apenas com numeros.')
        if(status):
            DBhandler().delConsultant(self.consultant['RA'])


class ViewErrorLog(Screen):
    errorLogText = StringProperty()
    
    def load(self, file):
        with open(file) as stream:
            self.errorLogText = stream.read()

    def runLoad(self):
        self.load(Var().errorLogFile)

    def dismiss_popup(self):
        self._popup.dismiss()    
    
    def show_export_errorlog(self):
        content = SaveErrorLogDialog(saveErrorLog=self.exportErrorLog, cancel=self.dismiss_popup)
        content.textUpdate()
        self._popup = Popup(title="Salvar", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def exportErrorLog(self, path, filename):
        self.dismiss_popup()
        if(filename != []):
            try:
                IOmethod().errorLogExporter(os.path.join(path, filename[0]))
                textPopup("Relatorio exportado com sucesso!")
            except:
                errorPopup()
        else:
            textPopup('Selecione uma pasta de destino.')


class GenerateCertificate(Screen):
    months = ['','']
    
    def bindm1(self, m1):
        self.months[0] = m1
        
    def bindm2(self, m2):
        self.months[1] = m2
    
    def generateCertificate(self):
        if(self.months[0] == self.months[1]):
            textPopup('Selecione meses diferentes.')
        elif(self.months[0] == '' or self.months[1] == ''):
            textPopup('Selecione 2 meses.')
        else:
            DBoutput(20.0, self.months)


class Manager(ScreenManager):
    mainmenu = ObjectProperty(None)
    options = ObjectProperty(None)
    credit = ObjectProperty(None)
    addconsultant = ObjectProperty(None)
    errorlog = ObjectProperty(None)
    rmf = ObjectProperty(None)
    rsf = ObjectProperty(None)


class MainApp(App):
        
    def build(self):
        m = Manager(transition=NoTransition())
        return m


if __name__ == '__main__':
    MainApp().run()