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

"""

TODO - Fix errorLog changing in Options menu. It can't be changed right now.
TODO - Fix icon not showing in exe.
TODO - Create screen that shows/controls the database.

"""

###############################################################################
### INPUT/OUTPUT

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

def readDatabase(databaseFile, db): # Used to read a csv file and store it as a dict
    db.database = pe.get_dict(file_name = databaseFile, encoding = 'utf-8-sig')
    # encoding = 'utf-8-sig' -> prevent the 'RA' to become '\ufeffRA' when the database is read
    return db

def cellWriter(ra, period, time, database): # Writes the time according to the RA number and the month
    consultantRow = database['RA'].index(int(ra))
    database[period][consultantRow] = time
    return database

def saveDatabase(database, databaseFile): # Gets a dict and transforms it into a csv output
    database = pe.get_sheet(adict = database)
    database.save_as(databaseFile)
    
def outputDatabase(const, db, months):
# Generates 'SaidaParaCertificados.csv', which is used to feed 'Certificados.docx'
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
    try:
        db = readDatabase(const.databaseFile, db)
        #print(db.database['NOME'][0])
        length = len(db.database['NOME'])
        output = {'RA': db.database['RA'],
                  'NOME': db.database['NOME'],
                  'CONSULTORIA': db.database['CONSULTORIA'],
                  months[0]: db.database[months[0]],
                  months[1]: db.database[months[1]],
                  'TOTAL': ([0] * length),
                  'MES1': ([monthTrans[months[0]]] * length),
                  'MES2': ([monthTrans[months[1]]] * length)}
        
        for i in range(len(db.database['NOME'])):
            sumTime = db.database[months[0]][i] + db.database[months[1]][i]
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
        for i in range(len(db.database['NOME'])):
            if(output['TOTAL'][i] >= 20.0):
                for key in output.keys():
                    newoutput[key].append(output[key][i])
        
        certificateCount = len(newoutput['NOME'])
        output = pe.get_sheet(adict = newoutput) # Transforms the dict created above in csv format
        output.save_as(const.outputFile) # Saves the csv into file
        
        # sorts SaidaParaCertificados by Consulting names
        b = pe.get_array(file_name = const.outputFile)
        indexConsult = b[0].index('CONSULTORIA')
        
        def takeSecond(b):
            element = b[indexConsult]
            return element
        
        sortedList = [b[0]] + sorted(b[1::], key=takeSecond)
        pe.save_as(array=sortedList, dest_file_name=const.outputFile)
        textPopup('Sucesso!\n\n' + str(certificateCount) + ' certificado(s) gerados.')
    except:
        errorPopup()

def strip_accents(text):
    """
    Strip accents from input String.

    :param text: The input string.
    :type text: String.

    :returns: The processed String.
    :rtype: String.
    """
    try:
        text = unicode(text, 'utf-8')
    except (TypeError, NameError): # unicode is a default on python 3 
        pass
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")
    return str(text)
        
def addConsultant(const, db, consultant):
    db = readDatabase(const.databaseFile, db)
    #print(db.database['RA'])
    if(int(consultant['RA']) in db.database['RA']):
        popup = Popup(title='FormCV',
                      content=Label(text='Este RA já está no banco de dados.'),
                      size_hint=(None, None), size=(400, 200))
        popup.open()
    else:
        try:
            for key in consultant.keys():
                db.database[key].append(consultant[key])
            for key in const.months:
                db.database[key].append(0)
            saveDatabase(db.database, const.databaseFile)
            popup = Popup(title='FormCV',
                          content=Label(text='Consultor adicionado com sucesso.'),
                          size_hint=(None, None), size=(400, 200))
            popup.open()
        except:
            errorPopup()
            
def delConsultant(const, db, consultantRA):
    try:
        db.database = pe.get_sheet(file_name=const.databaseFile, encoding = 'utf-8-sig')
        db.database.name_rows_by_column(0)
        del db.database.row[consultantRA]
        db.database.save_as(const.databaseFile)
        
        popup = Popup(title='FormCV',
                      content=Label(text='Consultor removido!'),
                      size_hint=(None, None), size=(400, 200))
        popup.open()   
    except:
        errorPopup()

def errorLogWriter(errorLogFile, aux):
    with open(errorLogFile, 'w') as file_handler:
        file_handler.write("Erros fatais: {}     ".format(str(aux.errors)))
        file_handler.write("Imagens com erros: {}\n\n".format(str(aux.warnings)))
        for item in aux.errorLog:
            file_handler.write("{}\n".format(item))

            
def errorLogExporter(errorLogFile, dst):
    shutil.copy(errorLogFile, dst)
    
def imgPreview(img):
    cv2.imshow('Preview', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
###############################################################################
### CORE

def imgUndistort(const, imgAddress):
    try:
        imggray = cv2.cvtColor(cv2.imread(imgAddress), cv2.COLOR_BGR2GRAY)  #import and convert into grayscale
        width, height = imggray.shape
        maxheight = 1024
        maxwidth = int(maxheight/(width/height))
        imgresize = cv2.resize(imggray,(maxwidth, maxheight), interpolation = cv2.INTER_AREA)
        #imgPreview(imgresize)
        imgblur = cv2.GaussianBlur(imgresize,(9,9),0) #apply gaussian blur
        imgthresh = cv2.adaptiveThreshold(imgblur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,\
                cv2.THRESH_BINARY_INV,3,2)
        im2, contours, hierarchy = cv2.findContours(imgthresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) #detect contours
        #imgPreview(imgthresh)
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
        pts2 = np.float32(getCoordOrder(const, approx))
        M = cv2.getPerspectiveTransform(pts1,pts2)
        imgundist = cv2.warpPerspective(imgresize,M,(const.w, const.h))
        return imgundist
    except:
        return "IMGUNDIST"
    
def getCoordOrder(const, array):
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
    ordered = [[const.CoordOrder[tl]],[const.CoordOrder[tr]],[const.CoordOrder[br]],[const.CoordOrder[bl]]]
    return ordered

def imgTransform(img):
    try:
        # transforms data into single pixels
        imgthresh = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_MEAN_C,\
                cv2.THRESH_BINARY,17,25)
        #imgPreview(imgthresh)
        imgblur = cv2.GaussianBlur(imgthresh,(13,13),0)
        #imgPreview(imgblur)
        ret,imgthresh = cv2.threshold(imgblur,180,255,cv2.THRESH_BINARY)
        #imgPreview(imgthresh)
        imgresized = cv2.resize(imgthresh,(37, 95), interpolation = cv2.INTER_AREA)
        #imgPreview(imgresized)
        ret,imgthresh = cv2.threshold(imgresized,192,255,cv2.THRESH_BINARY_INV)
        imgout = imgthresh[1:94, 1:36] #deletes 1 pixel at all margins
        #imgPreview(imgout)
        return imgout
    except:
        return "IMGOUT"

def imgToMatrix(img):
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

def dataExtract(matrix):
    data = matrix
    ra = []
    period = []
    time = []
    timeFilter = []
    errorLog = []
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
                errorLog.append('          AVISO: erro de preenchimento ou leitura detectado no dia: ' + str(time[line][-1:]))
            elif sumRow == 6:
                timeFilter.append(time[line][:-1]) #passes only time
                dayIndex.append(time[line][-1:])
                #timeFilter.append(time[line]) #passes day number also
    except:
        return "DATAEXTRACT"
    return ra, period, timeFilter, errorLog, dayIndex

def timePositionToValue(time):
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
    

def timeCalc(const, time, days):
    totalTime = 0.
    timeIn = 0.
    timeOut = 0.
    errorLog = []
    try:
        for line in range(len(time)):
            timeIn = 10*const.pattern[time[line][0]] + const.pattern[time[line][1]] + 0.25*const.pattern[time[line][2]]
            timeOut = 10*const.pattern[time[line][3]] + const.pattern[time[line][4]] + 0.25*const.pattern[time[line][5]]
            dayTime = timeOut - timeIn
            if timeIn > 23.75 or timeOut > 23.75 or dayTime < 0.0:
                dayTime = 0
                errorLog.append('          AVISO: dia com soma maior que 24h detectado no dia: ' + str(days[line]))
            totalTime = totalTime + dayTime
        return totalTime, errorLog
    except:
        return 0, errorLog

def dataRead(const, ra, period, days):
    raStr = ''
    periodStr = ''
    
    try:
        #Reads RA
        for line in ra:
            raStr = raStr + str(line.index(1))   
        periodStr = const.months[period[2].index(1)]
        yearStr = str(period[0].index(1)+1) + str(period[1].index(1)+1)
    except:
        pass
    return raStr, periodStr, yearStr

class ImgRead:
    
    def __init__(self, const, imgAddress):
            self.imgAddress = imgAddress
            self.status = True
            self.terminalError = False
            self.imgUndist = imgUndistort(const, self.imgAddress)
            self.warningCount = 0
            self.errorLog = []
            if(self.imgUndist != "IMGUNDIST"):
                self.imgOut = imgTransform(self.imgUndist)
            else:
                self.status = False
                
            if(self.imgOut != "IMGOUT" and self.status):
                self.imgData = imgToMatrix(self.imgOut)
            else:
                self.status = False
            if(self.imgData != "TOMATRIX" and self.status):
                try:
                    self.raRaw, self.periodRaw, self.timeRaw, self.fillingErrorLog, self.dayIndex = dataExtract(self.imgData)
                    self.warningCount += len(self.fillingErrorLog)
                    self.timeRead = timePositionToValue(self.timeRaw)
                    self.time, self.sumErrorLog = timeCalc(const, self.timeRead, self.dayIndex)
                    self.warningCount += len(self.sumErrorLog)
                    self.ra, self.period, self.year = dataRead(const, self.raRaw, self.periodRaw, self.dayIndex)
                    self.errorLog.extend(self.sumErrorLog)
                    self.errorLog.extend(self.fillingErrorLog)
                except:
                    self.status = False
            self.errorType = self.errorFinder()
            
            
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
        
            
    def getErrorImage(self):
        errorImg = self.imgUndist
        error = False
        if("RA" in self.errorType):
            errorImg = cv2.rectangle(errorImg, (10,3), (185,175), (250,250,250), 2)
            error = True
        if("PERIOD" in self.errorType):
            errorImg = cv2.rectangle(errorImg, (300,3), (505,72), (250,250,250), 2)
            error = True
        if(error):
            imgPreview(errorImg)
            
    def getWarningImage(self):
        pass
        
        
           
###############################################################################
### PARAMETERS

class Param:
    class Const:
        def __init__(self):
            config = configparser.ConfigParser()
            config.read('config.ini')
            self.rootDir = os.path.dirname(__file__)
            self.imgDir = config['const']['imgDir']
            self.databaseFile = config['const']['databaseFile']
            self.errorLogFile = config['const']['errorLogFile']
            self.outputFile = config['const']['outputFile']

        pattern = [0,1,2,0,1,2,3,4,5,6,7,8,9,0,1,2,3,0,0,1,2,0,1,2,3,4,5,6,7,8,9,0,1,2,3]
        months = ['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ']
        w = 37*16
        h = 47*21
        CoordOrder = {0:[0,0], 1:[w,0], 2:[w,h], 3:[0,h]}

    class Var:
        imgAddress = ''
        errorCount = 0
        
    class Aux:
        status = True
        errorLog = []
        errors = 0
        warnings = 0
        numOfFiles = 0
        
    class Db:
        database = []
        
def paramTuner(variable, value):
    config = configparser.ConfigParser()
    config.read('config.ini')
    config['const'][variable] = value
    with open('config.ini', 'w') as configFile:
        config.write(configFile)
    global const1
    const1 = Param.Const()


const1 = Param.Const()
var1 = Param.Var()
aux1 = Param.Aux()
db1 = Param.Db()

###############################################################################

def fileCount(const,aux):
    aux.numOfFiles = 0
    for subdir, dirs, files in os.walk(const.imgDir):
        for file in files:
            filepath = subdir + os.sep + file
            if filepath.endswith(".jpeg") or filepath.endswith(".jpg"):
                aux.numOfFiles += 1
    return aux.numOfFiles

def multipleFileReader(const, var, aux, db):
    db = readDatabase(const.databaseFile, db)
    aux.numOfFiles = fileCount(const, aux)
    for subdir, dirs, files in os.walk(const.imgDir):
        for file in files:
            var1.errorCount = 0
            filepath = subdir + os.sep + file
            if filepath.endswith(".jpeg") or filepath.endswith(".jpg"):
                aux.errorLog.append('IMG: ' + file)
                imgRead = ImgRead(const, filepath)
                if(imgRead.status):
                    aux.errorLog[aux.errorLog.index('IMG: ' + file)] = ('IMG: ' + file +
                                                                        '  |  RA: ' + imgRead.ra +
                                                                        '  |  PERIODO: ' + imgRead.period +
                                                                        '  |  HORAS: ' + str(imgRead.time))
                    aux.errorLog.extend(imgRead.errorLog)
                    try:
                        db.database = cellWriter(str(imgRead.ra), imgRead.period, imgRead.time, db.database)
                    except:
                        aux.errorLog.append('    ERRO: nao foi possivel encontrar o RA no banco de dados.')
                        aux.errors += 1                
                else:
                    if(imgRead.terminalError):
                        aux.errorLog.append("    Imagem nao foi reconhecida.")
                    else:
                        if("RA" in imgRead.errorType):
                            aux.errorLog.append("    Erro de preenchimento no RA.")
                        if("PERIOD" in imgRead.errorType):
                            aux.errorLog.append("    Erro de preenchimento no Periodo.")
                    aux.errors += 1
                if imgRead.warningCount > 0:
                    aux.warnings += 1
    try:
        errorLogWriter(const.errorLogFile, aux)
        currentTime = str(datetime.today()).replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        errorLogExporter(const.errorLogFile, os.path.join(const.imgDir, (const.errorLogFile[:-4] + currentTime[:14] + ".txt")))
        saveDatabase(db.database, const.databaseFile)
        textPopup('Imagens lidas: ' + str(aux.numOfFiles) + '\nErros fatais: ' + str(aux.errors) + '\nImagens com erros de preenchimento: ' + str(aux.warnings))
    except:
        textPopup("Algo deu errado ao salvar o banco de dados.\nCertifique-se de que o arquivo esta fechado.")
    
    #Resets error countings
    aux1.errorLog = []
    aux1.errors = 0
    aux1.warnings = 0
    
def singleFileReader(const, var, aux, db):
    db = readDatabase(const.databaseFile, db)
    if var.imgAddress.endswith(".jpeg") or var.imgAddress.endswith(".jpg"):
        aux.errorLog.append('IMG: ' + var.imgAddress)
        imgRead = ImgRead(const, var.imgAddress)
        imgRead.getErrorImage()
        if(imgRead.status):
            aux.errorLog.append("    RA: " + imgRead.ra)
            aux.errorLog.append("    PERIODO: " + imgRead.period)
            aux.errorLog.append("    HORAS: " + str(imgRead.time))
            aux.errorLog.extend(imgRead.errorLog)
            try:
                db.database = cellWriter(str(imgRead.ra), imgRead.period, imgRead.time, db.database)
            except:
                aux.errorLog.append('    ERRO: nao foi possivel encontrar o RA no banco de dados.')
                aux.errors += 1                
        else:
            if(imgRead.terminalError):
                aux.errorLog.append("    Imagem nao foi reconhecida.")
            else:
                if("RA" in imgRead.errorType):
                    aux.errorLog.append("    Erro de preenchimento no RA.")
                if("PERIOD" in imgRead.errorType):
                    aux.errorLog.append("    Erro de preenchimento no Periodo.")
            aux.errors += 1
        if imgRead.warningCount > 0:
            aux.warnings += 1
    try:
        errorLogWriter(const.errorLogFile, aux)
        saveDatabase(db.database, const.databaseFile)
        textPopup("Leitura finalizada.\nConfira o relatorio para obter detalhes.")
    except:
        textPopup("Algo deu errado ao salvar o banco de dados.\nCertifique-se de que o arquivo esta fechado.")
    
    #Resets error countings
    aux1.errorLog = []
    aux1.errors = 0
    aux1.warnings = 0
        
###############################################################################
# KIVY APP
    
Window.size = (1000,600)

class MainMenu(Screen):
    
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)
        
class ChangeDatabaseDialog(FloatLayout):
    loadDatabase = ObjectProperty(None)
    cancel = ObjectProperty(None)
    
    class Text(Widget):
        databaseFile = StringProperty(const1.databaseFile)
        
    text = Text()
    
    def textUpdate(self):
        self.text.datbaseFile = const1.databaseFile

class ChangeImgDialog(FloatLayout):
    loadImg = ObjectProperty(None)
    cancel = ObjectProperty(None)
    
    class Text(Widget):
        imgDir = StringProperty(const1.imgDir)
        
    text = Text()
    
    def textUpdate(self):
        self.text.imgDir = const1.imgDir
    
class ChangeOutputDialog(FloatLayout):
    loadOutput = ObjectProperty(None)
    cancel = ObjectProperty(None)

    class Text(Widget):
        outputFile = StringProperty(const1.outputFile)
        
    text = Text()
    
    def textUpdate(self):
        self.text.outputFile = const1.outputFile

class SaveErrorLogDialog(FloatLayout):
    saveErrorLog = ObjectProperty(None)
    cancel = ObjectProperty(None)

    class Text(Widget):
        imgDir = StringProperty(const1.imgDir)
        
    text = Text()
    
    def textUpdate(self):
        self.text.imgDir = const1.imgDir

class Options(Screen):

    class Text(Widget):
        dbDir = StringProperty(const1.databaseFile)
        imgDir = StringProperty(const1.imgDir)
        elDir = StringProperty(const1.errorLogFile)
        outputDir = StringProperty(const1.outputFile)
    
    text = Text()
    
    def textUpdate(self):
        self.text.dbDir = const1.databaseFile
        self.text.imgDir = const1.imgDir
        self.text.elDir = const1.errorLogFile
        self.text.outputDir = const1.outputFile
    
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
            paramTuner('databaseFile', os.path.join(path, filename[0]))
        self.textUpdate()
        self.dismiss_popup()        
        
    def changeImgDir(self, path, filename):
        if(filename != []):
            paramTuner('imgDir', os.path.join(path, filename[0]))
        self.textUpdate()
        self.dismiss_popup()
        
    def changeOutput(self, path, filename):
        if(filename != []):
            paramTuner('outputFile', os.path.join(path, filename[0]))
        self.textUpdate()
        self.dismiss_popup()

class RMFmenu(Screen):

    class Info(Widget):
        imgDir = StringProperty(const1.imgDir)
        numOfFiles = StringProperty(str(aux1.numOfFiles))
        
        def __init__(self, *kwargs):
            self.numOfFiles = str(fileCount(const1, aux1))
    
    info = Info()
    
    def infoUpdate(self):
        self.info.imgDir = const1.imgDir
        aux1.numOfFiles = fileCount(const1, aux1)
        self.info.numOfFiles = str(aux1.numOfFiles)
    
    def dismiss_popup(self):
        self._popup.dismiss()    
    
    def show_load_imgDir(self):
        content = ChangeImgDialog(loadImg=self.changeImgDir, cancel=self.dismiss_popup)
        self._popup = Popup(title="Carregar Pasta", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def changeImgDir(self, path, filename):
        paramTuner('imgDir', os.path.join(path, filename[0]))
        self.infoUpdate()
        self.dismiss_popup()
    
    def rmf(self):
        multipleFileReader(Param.Const(), var1, aux1, Param.Db())

class ChooseRSF(FloatLayout):
    loadRSF = ObjectProperty(None)
    cancel = ObjectProperty(None)

    class Text(Widget):
        imgDir = StringProperty(const1.imgDir)
        
    text = Text()
    
    def textUpdate(self):
        self.text.imgDir = const1.imgDir

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
        var1.imgAddress = os.path.join(path, filename[0])
        singleFileReader(Param.Const(), var1, aux1, Param.Db())
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
        self.consultant['NOME'] = strip_accents(nome).title()
        
    def bindCONSULT(self, consult):
        self.consultant['CONSULTORIA'] = consult

    def runAddConsultant(self):
        status = True
        for key in self.consultant.keys():
            if self.consultant[key] == '':
                status = False
                popup = Popup(title='FormCV',
                          content=Label(text='Preencha todos os campos.'),
                          size_hint=(None, None), size=(400, 200))
                popup.open()
        if(not self.consultant['RA'].isdigit()):
            status = False
            popup = Popup(title='FormCV',
                      content=Label(text='Preencha o RA com numeros apenas.'),
                      size_hint=(None, None), size=(400, 200))
            popup.open()
        if(not len(self.consultant['RA']) == 8):
            popup = Popup(title='FormCV',
                      content=Label(text='Preencha o RA com 8 numeros.'),
                      size_hint=(None, None), size=(400, 200))
            popup.open()
        if(status):
            addConsultant(const1, db1, self.consultant)
            
            
    def runDelConsultant(self):
        status = True
        if(not self.consultant['RA'].isdigit()):
            status = False
            popup = Popup(title='FormCV',
                      content=Label(text='Preencha o RA apenas com numeros.'),
                      size_hint=(None, None), size=(400, 200))
            popup.open()
        if(status):
            delConsultant(const1, db1, self.consultant['RA'])

class ViewErrorLog(Screen):
    errorLogText = StringProperty()
    
    def load(self, file):
        with open(file) as stream:
            self.errorLogText = stream.read()

    def runLoad(self):
        self.load(const1.errorLogFile)

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
                errorLogExporter(const1.errorLogFile, os.path.join(path, filename[0]))
                popup = Popup(title='FormCV',
                          content=Label(text='Relatorio exportado com sucesso.'),
                          size_hint=(None, None), size=(400, 200))
                popup.open()
            except:
                errorPopup
        else:
            popup = Popup(title='FormCV',
                      content=Label(text='Selecione uma pasta de destino.'),
                      size_hint=(None, None), size=(400, 200))
            popup.open()

class GenerateCertificate(Screen):
    months = ['','']
    
    def bindm1(self, m1):
        self.months[0] = m1
        
    def bindm2(self, m2):
        self.months[1] = m2
    
    def generateCertificate(self):
        if(self.months[0] == self.months[1]):
            popup = Popup(title='FormCV',
                      content=Label(text='Selecione meses diferentes.'),
                      size_hint=(None, None), size=(400, 200))
            popup.open()
        elif(self.months[0] == '' or self.months[1] == ''):
            popup = Popup(title='FormCV',
                      content=Label(text='Selecione 2 meses.'),
                      size_hint=(None, None), size=(400, 200))
            popup.open()
        else:
            outputDatabase(const1, db1, self.months)
       
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
