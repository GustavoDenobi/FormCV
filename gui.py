from core import *

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class App(QMainWindow):

    def __init__(self):
        super().__init__()
        scriptDir = os.path.dirname(os.path.realpath(__file__))
        self.setWindowIcon(QIcon(scriptDir + os.path.sep + 'Icon.ico'))
        self.title = 'FormCV'
        self.left = 0
        self.top = 0
        #self.width = 900
        #self.height = 600
        self.setWindowTitle(self.title)
        #self.setGeometry(self.left, self.top, self.width, self.height)
        self.setWindowState(Qt.WindowMaximized)

        self.table_widget = MyTableWidget(self)
        self.setCentralWidget(self.table_widget)

        self.show()


class MyTableWidget(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.var = Var()
        self.height = self.height()
        self.width = self.width()

        # Initialize tab screen
        self.initUI()
        self.setTabs()
        self.get_tab1()
        self.get_tab2()
        self.get_tab3()
        self.get_tab4()
        self.get_tab5()

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def cv_to_qt(self, img):
        if(len(img.shape) == 2):
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        height, width, channel = img.shape
        bytesPerLine = 3 * width
        qImg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        return qImg

    def setMyData(self, dict):
        self.table.setColumnCount(len(dict.items()))
        self.table.setHorizontalHeaderLabels(dict.keys())
        self.table.setRowCount(self.database.length)
        for column, key in enumerate(dict):
            self.table.horizontalHeaderItem(column).setTextAlignment(Qt.AlignHCenter)
            for row, item in enumerate(dict[key]):
                newitem = QTableWidgetItem(str(item))
                newitem.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, newitem)
        self.table.resizeColumnsToContents()

    def getFolder(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.Directory)
        #dlg.setFilter(self.var.cvFormats)
        path = QStringListModel()
        fileList = []

        if dlg.exec_():
            path = dlg.selectedFiles()
            for subdir, dirs, files in os.walk(path[0]):
                for file in files:
                    filepath = subdir + os.sep + file
                    if (file[file.index('.'):] in self.var.cvFormats):
                        fileList.append(filepath)
            self.tab1.fileList = fileList
            self.getList()

    def getFiles(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFiles)
        #dlg.setFilter(self.var.cvFormats)
        filenames = QStringListModel()

        if dlg.exec_():
            filenames = dlg.selectedFiles()
            self.tab1.fileList = filenames
            self.getList()

    def getList(self):
        self.pendingReading = True
        self.listedFiles.clear()
        for item in self.tab1.fileList:
            self.listedFiles.addItem(QListWidgetItem(item))

    def runFileReader(self):
        if(len(self.tab1.fileList) > 0):
            self.pendingReading = False
            self.tab1.readings = FileReader(self.tab1.fileList)
            self.changeViews()
            self.refreshLog()

    def changeViews(self):
        if(not self.pendingReading):
            row = self.listedFiles.currentRow()
            if(row == -1):
                row = 0
            self.tab1.sub2.info.setText(self.tab1.readings.logToStr(self.tab1.readings.forms[row].errorLog))

            try:
                img = QPixmap(self.cv_to_qt(self.tab1.readings.forms[row].imgread))
                img = img.scaled(int(self.width * 18), int(self.height * 18), Qt.KeepAspectRatio)
                self.tab1.tab1.img1.setPixmap(img)
            except:
                self.tab1.tab1.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.cv_to_qt(self.tab1.readings.forms[row].imgcontour))
                img = img.scaled(int(self.width * 18), int(self.height * 18), Qt.KeepAspectRatio)
                self.tab1.tab2.img1.setPixmap(img)
            except:
                self.tab1.tab2.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.cv_to_qt(self.tab1.readings.forms[row].imgundist))
                img = img.scaled(int(self.width * 18), int(self.height * 18), Qt.KeepAspectRatio)
                self.tab1.tab3.img1.setPixmap(img)
            except:
                self.tab1.tab3.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.cv_to_qt(self.tab1.readings.forms[row].imgnormal))
                img = img.scaled(int(self.width * 18), int(self.height * 18), Qt.KeepAspectRatio)
                self.tab1.tab4.img1.setPixmap(img)
            except:
                self.tab1.tab4.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.cv_to_qt(self.tab1.readings.forms[row].imgAnottated))
                img = img.scaled(int(self.width*18), int(self.height*18), Qt.KeepAspectRatio)
                self.tab1.tab5.img1.setPixmap(img)
            except:
                self.tab1.tab5.img1.setText("Erro ao ler imagem.")

    def refreshLog(self):
        self.errorLog.clear()
        self.errorLog.setText(errorLogHandler().errorLogText)

    def initUI(self):
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.showMaximized()
        #self.setWindowState(Qt.WindowMaximized)
        #self.tabs.resize(900, 600)

    def setTabs(self):
        self.tabs.addTab(self.tab1, "Leitura")
        self.tabs.addTab(self.tab2, "Relatório")
        self.tabs.addTab(self.tab3, "Banco de Horas")
        self.tabs.addTab(self.tab4, "Configurações")
        self.tabs.addTab(self.tab5, "Sobre")

    def get_tab1(self):
        # LEITURA
        self.tab1.layout = QHBoxLayout(self)
        self.tab1.sub1 = QWidget()
        self.tab1.sub2 = QWidget()
        self.tab1.sub1.layout = QVBoxLayout(self)
        self.tab1.sub2.layout = QVBoxLayout(self)

        ## sub1
        self.tab1.fileList = []
        self.btn_Folder = QPushButton("Selecionar pasta")
        self.btn_Folder.clicked.connect(self.getFolder)
        self.btn_Files = QPushButton("Selecionar imagens")
        self.btn_Files.clicked.connect(self.getFiles)
        self.listedFiles = QListWidget()
        self.listedFiles.currentRowChanged.connect(self.changeViews)
        self.btn_Run = QPushButton("Iniciar leitura")
        self.btn_Run.clicked.connect(self.runFileReader)
        self.tab1.sub1.layout.addWidget(self.btn_Folder)
        self.tab1.sub1.layout.addWidget(self.btn_Files)
        self.tab1.sub1.layout.addWidget(self.listedFiles)
        self.tab1.sub1.layout.addWidget(self.btn_Run)
        self.tab1.sub1.setLayout(self.tab1.sub1.layout)

        ## sub2
        self.tab1.tabs = QTabWidget()
        self.tab1.tab1 = QWidget()
        self.tab1.tab2 = QWidget()
        self.tab1.tab3 = QWidget()
        self.tab1.tab4 = QWidget()
        self.tab1.tab5 = QWidget()
        self.tab1.tab1.setAutoFillBackground(True)
        self.tab1.tab2.setAutoFillBackground(True)
        self.tab1.tab3.setAutoFillBackground(True)
        self.tab1.tab4.setAutoFillBackground(True)
        self.tab1.tab5.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.lightGray)
        self.setPalette(p)
        self.tab1.tabs.addTab(self.tab1.tab1, "1")
        self.tab1.tabs.addTab(self.tab1.tab2, "2")
        self.tab1.tabs.addTab(self.tab1.tab3, "3")
        self.tab1.tabs.addTab(self.tab1.tab4, "4")
        self.tab1.tabs.addTab(self.tab1.tab5, "5")

        self.tab1.tab1.layout = QVBoxLayout()
        self.tab1.tab2.layout = QVBoxLayout()
        self.tab1.tab3.layout = QVBoxLayout()
        self.tab1.tab4.layout = QVBoxLayout()
        self.tab1.tab5.layout = QVBoxLayout()
        self.tab1.tab1.img1 = QLabel("Aguardando leitura.")
        self.tab1.tab1.img1.setAlignment(Qt.AlignCenter)
        self.tab1.tab2.img1 = QLabel("Aguardando leitura.")
        self.tab1.tab2.img1.setAlignment(Qt.AlignCenter)
        self.tab1.tab3.img1 = QLabel("Aguardando leitura.")
        self.tab1.tab3.img1.setAlignment(Qt.AlignCenter)
        self.tab1.tab4.img1 = QLabel("Aguardando leitura.")
        self.tab1.tab4.img1.setAlignment(Qt.AlignCenter)
        self.tab1.tab5.img1 = QLabel("Aguardando leitura.")
        self.tab1.tab5.img1.setAlignment(Qt.AlignCenter)
        self.tab1.tab1.layout.addWidget(self.tab1.tab1.img1)
        self.tab1.tab2.layout.addWidget(self.tab1.tab2.img1)
        self.tab1.tab3.layout.addWidget(self.tab1.tab3.img1)
        self.tab1.tab4.layout.addWidget(self.tab1.tab4.img1)
        self.tab1.tab5.layout.addWidget(self.tab1.tab5.img1)


        self.tab1.sub2.info = QLabel("Aguardando leitura." + ("\n"*12))

        self.tab1.tab1.setLayout(self.tab1.tab1.layout)
        self.tab1.tab2.setLayout(self.tab1.tab2.layout)
        self.tab1.tab3.setLayout(self.tab1.tab3.layout)
        self.tab1.tab4.setLayout(self.tab1.tab4.layout)
        self.tab1.tab5.setLayout(self.tab1.tab5.layout)


        self.tab1.sub2.layout.addWidget(self.tab1.tabs)
        self.tab1.sub2.layout.addWidget(self.tab1.sub2.info)
        self.tab1.sub2.setLayout(self.tab1.sub2.layout)

        self.tab1.layout.addWidget(self.tab1.sub1)
        self.tab1.layout.addWidget(self.tab1.sub2)
        self.tab1.setLayout(self.tab1.layout)

    def get_tab2(self):
        self.errorLogText = errorLogHandler().errorLogText
        self.tab2.layout = QVBoxLayout(self)
        self.errorLog = QLabel(self.errorLogText)
        self.errorLog.setAlignment(Qt.AlignTop)
        self.errorLog.setWordWrap(False)
        self.errorLog.setMargin(16)
        self.scrollErrorLog = QScrollArea()
        self.scrollErrorLog.setWidget(self.errorLog)
        self.tab2.layout.addWidget(self.scrollErrorLog)
        self.tab2.setLayout(self.tab2.layout)

    def get_tab3(self):
        self.database = DBhandler()
        self.tab3.layout = QVBoxLayout()
        self.table = QTableWidget()
        self.setMyData(self.database.dbdict)
        self.tab3.layout.addWidget(self.table)
        self.tab3.setLayout(self.tab3.layout)

    def get_tab4(self):
        self.tab4.layout = QFormLayout(self)
        self.config1 = QLabel("Banco de horas:")
        self.param1 = QLineEdit("arroz")
        self.config2 = QLabel("Arquivo de relatório")
        self.param2 = QLineEdit(self.var.errorLogFile)

        self.tab4.layout.addWidget(self.config1)
        self.tab4.layout.addWidget(self.param1)
        self.tab4.setLayout(self.tab4.layout)

    def get_tab5(self):
        self.tab5.layout = QVBoxLayout(self)
        self.about = QLabel(creditText)
        self.about.setWordWrap(True)
        self.errorLog.setMargin(16)
        self.tab5.layout.addWidget(self.about)
        self.tab5.setLayout(self.tab5.layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())



