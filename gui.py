from core import *

from time import sleep
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

        self.main_widget = MainWidget(self)
        self.setCentralWidget(self.main_widget)

        self.show()


class MainWidget(QWidget):

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

        self.tab1.readings = None

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.console)
        self.setLayout(self.layout)

    def getCurrentTime(self):
        currentTime = str(datetime.today())#.replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        return currentTime[:19]

    def outputToConsole(self, txt):
        time = self.getCurrentTime()
        self.console.setText(time + " >> " + str(txt))

    def imgToPixmap(self, img):
        if(len(img.shape) == 2):
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        height, width, channel = img.shape
        bytesPerLine = 3 * width
        qImg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        return qImg

    def loadDatabase(self):
        self.database = DBhandler()
        self.table.setColumnCount(len(self.database.dbdict.items()))
        self.table.setHorizontalHeaderLabels(self.database.dbdict.keys())
        self.table.setRowCount(self.database.length)
        for column, key in enumerate(self.database.dbdict):
            self.table.horizontalHeaderItem(column).setTextAlignment(Qt.AlignHCenter)
            for row, item in enumerate(self.database.dbdict[key]):
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
            self.outputToConsole(str(len(fileList)) + " novos arquivos adicionadas à lista. Aguardando leitura.")

    def getFiles(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFiles)
        #dlg.setFilter(self.var.cvFormats)
        filenames = QStringListModel()

        if dlg.exec_():
            filenames = dlg.selectedFiles()
            self.tab1.fileList = filenames
            self.getList()
            self.outputToConsole(str(len(filenames)) + " novos arquivos adicionadas à lista. Aguardando leitura.")

    def getList(self):
        self.pendingReading = True
        self.listedFiles.clear()
        for item in self.tab1.fileList:
            self.listedFiles.addItem(QListWidgetItem(item))

    def saveDB(self):
        try:
            self.tab1.readings.saveInfo()
            self.loadDatabase()
            self.listedFiles.clear()
            self.tab1.fileList = []
            self.eraseViews()
            self.outputToConsole("Banco de horas atualizado com sucesso.")
            self.btn_Save.setEnabled(False)
        except:
            self.outputToConsole("Erro ao atualizar banco de dados. Certifique-se de que o arquivo está fechado.")

    def runFileReader(self):
        self.outputToConsole("Lendo imagens...")
        if(len(self.tab1.fileList) > 0):
            self.pendingReading = False
            self.tab1.readings = FileReader(self.tab1.fileList)
            self.changeViews()
            self.refreshLog()
            self.btn_Save.setEnabled(True)
            self.btn_Save.clicked.connect(self.saveDB)
            self.outputToConsole("Leitura de imagens completa. Confira os detalhes e clique em 'Salvar Dados'.")
        else:
            self.outputToConsole("Nenhuma imagem foi selecionada.")

    def selMonth1(self, index):
        self.tab3.firstMonth = self.var.months[index]
        if(len(self.tab3.firstMonth) > 0 and len(self.tab3.secondMonth) > 0):
            self.tab3.btn_Generate.setEnabled(True)
        self.outputToConsole("Primeiro mês selecionado: " + self.tab3.firstMonth)

    def selMonth2(self, index):
        self.tab3.secondMonth = self.var.months[index]
        if(len(self.tab3.firstMonth) > 0 and len(self.tab3.secondMonth) > 0):
            self.tab3.btn_Generate.setEnabled(True)
        self.outputToConsole("Segundo mês selecionado: " + self.tab3.secondMonth)

    def runGenerateCertificates(self):
        months = []
        months.append(self.tab3.firstMonth)
        months.append(self.tab3.secondMonth)
        db = DBoutput(20, months)
        self.tab3.btn_Generate.setEnabled(False)
        self.outputToConsole(str(db.certificateCount) + " certificados gerados.")

    def searchDB(self):
        if (len(self.tab3.foundItems) > 0):
            for item in self.tab3.foundItems:
                item.setBackground(Qt.transparent)
            self.tab3.foundItems = []
        if(len(self.tab3.searchText) > 0):
            self.tab3.foundItems = self.table.findItems(self.tab3.searchText, Qt.MatchContains)
            if(len(self.tab3.foundItems) > 0):
                for item in self.tab3.foundItems:
                    item.setBackground(Qt.yellow)
                self.table.scrollToItem(self.tab3.foundItems[0], QAbstractItemView.PositionAtTop)
                self.outputToConsole(str(len(self.tab3.foundItems)) + " correspondências encontradas.")
            else:
                self.outputToConsole("Nenhuma correspondência foi encontrada.")
        else:
            self.outputToConsole("Insira algo para pesquisar e tente novamente.")

    def clearSearch(self):
        if(len(self.tab3.foundItems) > 0):
            for item in self.tab3.foundItems:
                item.setBackground(Qt.transparent)
            self.tab3.foundItems = []
        self.outputToConsole("Seleção limpa com sucesso.")
        self.tab3.search.setText("")

    def changeSearchText(self):
        self.tab3.searchText = self.tab3.search.text()

    def changeViews(self):
        factor = 0.7
        self.tab1.sub2.setFixedSize(self.tab1.sub2.size())
        boxSize = self.tab1.sub2
        scale = QSize(int(boxSize.width()* factor), int(boxSize.height() * factor))
        row = self.listedFiles.currentRow()
        if (row == -1):
            row = 0
        if(not self.pendingReading):
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.readings.forms[row].imgread))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab1.img1.setPixmap(img)
            except:
                self.tab1.tab1.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.readings.forms[row].imgcontour))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab2.img1.setPixmap(img)
            except:
                self.tab1.tab2.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.readings.forms[row].imgundist))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab3.img1.setPixmap(img)
            except:
                self.tab1.tab3.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.readings.forms[row].imgnormal))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab4.img1.setPixmap(img)
            except:
                self.tab1.tab4.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.readings.forms[row].imgAnottated))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab5.img1.setPixmap(img)
            except:
                self.tab1.tab5.img1.setText("Erro ao ler imagem.")
            self.tab1.sub2.info.setText(self.tab1.readings.logToStr(self.tab1.readings.forms[row].errorLog))
            width = self.tab1.sub2.width() * 0.8
            height = self.tab1.sub2.height() * 0.3
            self.tab1.sub2.info.setMinimumWidth(width)
            self.tab1.sub2.info.setMinimumHeight(height)

    def eraseViews(self):
        self.tab1.tab1.img1.setText("Aguardando leitura.")
        self.tab1.tab2.img1.setText("Aguardando leitura.")
        self.tab1.tab3.img1.setText("Aguardando leitura.")
        self.tab1.tab4.img1.setText("Aguardando leitura.")
        self.tab1.tab5.img1.setText("Aguardando leitura.")

    def refreshLog(self):
        self.errorLog.clear()
        self.errorLog.setText(errorLogHandler().errorLogText)

    def initUI(self):
        self.console = QLabel(self.getCurrentTime() + "\t>>\tFormCV iniciado com sucesso.")
        self.console.setAutoFillBackground(True)
        self.console.setMargin(8)
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
        self.tab1.sub2.box = QGroupBox("Detalhes da Leitura")
        self.tab1.sub2.box.layout = QVBoxLayout(self)

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
        self.btn_Save = QPushButton("Salvar dados")
        self.btn_Save.setEnabled(False)
        self.tab1.sub1.layout.addWidget(self.btn_Folder)
        self.tab1.sub1.layout.addWidget(self.btn_Files)
        self.tab1.sub1.layout.addWidget(self.listedFiles)
        self.tab1.sub1.layout.addWidget(self.btn_Run)
        self.tab1.sub1.layout.addWidget(self.btn_Save)
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
        self.tab1.tabs.addTab(self.tab1.tab1, "Entrada")
        self.tab1.tabs.addTab(self.tab1.tab2, "Detecção")
        self.tab1.tabs.addTab(self.tab1.tab3, "Correção")
        self.tab1.tabs.addTab(self.tab1.tab4, "Normalização")
        self.tab1.tabs.addTab(self.tab1.tab5, "Saída")

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


        self.tab1.sub2.info = QLabel("Aguardando leitura." + ("\n" * 12))
        self.tab1.sub2.info.setAlignment(Qt.AlignTop)
        self.tab1.sub2.info.setWordWrap(False)
        self.tab1.sub2.info.setMargin(16)
        self.tab1.sub2.infoArea = QScrollArea()
        self.tab1.sub2.infoArea.setWidget(self.tab1.sub2.info)
        self.tab1.sub2.infoArea.ensureWidgetVisible(self.tab1.sub2.info)

        self.tab1.tab1.setLayout(self.tab1.tab1.layout)
        self.tab1.tab2.setLayout(self.tab1.tab2.layout)
        self.tab1.tab3.setLayout(self.tab1.tab3.layout)
        self.tab1.tab4.setLayout(self.tab1.tab4.layout)
        self.tab1.tab5.setLayout(self.tab1.tab5.layout)


        self.tab1.sub2.box.layout.addWidget(self.tab1.tabs)
        self.tab1.sub2.box.layout.addWidget(self.tab1.sub2.infoArea)
        self.tab1.sub2.layout.addWidget(self.tab1.sub2.box)
        self.tab1.sub2.box.setLayout(self.tab1.sub2.box.layout)
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
        self.tab3.firstMonth = []
        self.tab3.secondMonth = []
        self.tab3.searchText = ""
        self.tab3.foundItems = []

        self.tab3.box1 = QGroupBox("Banco de Horas")
        self.tab3.box1.layout = QVBoxLayout()
        self.tab3.box1.searchBar = QWidget()
        self.tab3.box1.searchBar.layout = QHBoxLayout()


        self.tab3.search = QLineEdit()
        self.tab3.search.textChanged.connect(self.changeSearchText)
        self.tab3.btn_Search = QPushButton("Pesquisar")
        self.tab3.btn_Search.clicked.connect(self.searchDB)
        self.tab3.btn_Clear = QPushButton("Limpar")
        self.tab3.btn_Clear.clicked.connect(self.clearSearch)

        self.tab3.box1.searchBar.layout.addWidget(self.tab3.search)
        self.tab3.box1.searchBar.layout.addWidget(self.tab3.btn_Search)
        self.tab3.box1.searchBar.layout.addWidget(self.tab3.btn_Clear)

        self.tab3.layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        self.loadDatabase()

        self.tab3.box1.searchBar.setLayout(self.tab3.box1.searchBar.layout)
        self.tab3.box1.setLayout(self.tab3.box1.layout)
        self.tab3.box1.layout.addWidget(self.tab3.box1.searchBar)
        self.tab3.box1.layout.addWidget(self.table)
        self.tab3.layout.addWidget(self.tab3.box1)

        self.tab3.box2 = QGroupBox("Gerar Certificados")
        self.tab3.box2.layout = QHBoxLayout(self)
        self.tab3.monthSel1 = QComboBox()
        self.tab3.monthSel1.addItems(self.var.months)
        self.tab3.monthSel1.activated.connect(self.selMonth1)
        self.tab3.box2.layout.addWidget(self.tab3.monthSel1)
        self.tab3.monthSel2 = QComboBox()
        self.tab3.monthSel2.addItems(self.var.months)
        self.tab3.monthSel2.activated.connect(self.selMonth2)
        self.tab3.box2.layout.addWidget(self.tab3.monthSel2)
        self.tab3.btn_Generate = QPushButton('Gerar Certificados')
        self.tab3.btn_Generate.setEnabled(False)
        self.tab3.btn_Generate.clicked.connect(self.runGenerateCertificates)
        self.tab3.box2.layout.addWidget(self.tab3.btn_Generate)
        self.tab3.box2.setLayout(self.tab3.box2.layout)
        self.tab3.layout.addWidget(self.tab3.box2)


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
        self.about.setAlignment(Qt.AlignTop)
        self.about.setMargin(16)
        self.tab5.layout.addWidget(self.about)
        self.tab5.setLayout(self.tab5.layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())



