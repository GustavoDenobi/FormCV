from core import *

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class App(QMainWindow):

    def __init__(self):
        super().__init__()
        scriptDir = os.path.dirname(os.path.realpath(__file__))
        self.setWindowIcon(QIcon(scriptDir + os.path.sep + 'img/Icon.ico'))
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

        self.tab1.reading = None
        self.tab1.forms = []

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.console)
        self.setLayout(self.layout)
        self.outputToConsole("Inicialização completa.")
        if(self.var.checkBackup()):
            self.outputToConsole("Backup realizado.")

    def getCurrentTime(self):
        currentTime = str(datetime.today())#.replace(":", "").replace(" ", "").replace(".", "").replace("-", "")
        return currentTime[:19]

    def outputToConsole(self, txt):
        time = self.getCurrentTime()
        self.console.setText(time + " >>\t" + str(txt))
        self.console.repaint()

    def imgToPixmap(self, img):
        if(len(img.shape) == 2):
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        height, width, channel = img.shape
        bytesPerLine = 3 * width
        qImg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        return qImg

    def loadDatabase(self):
        self.tab3.foundItems = []
        self.database = DBhandler()
        self.table.clear()
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
        dlg = QFileDialog(directory=self.var.imgDir)
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
            self.outputToConsole(str(len(self.tab1.fileList)) + " arquivos válidos adicionadas à lista. "
                                 + "Aguardando leitura.")

    def getFiles(self):
        dlg = QFileDialog(directory=self.var.imgDir)
        dlg.setFileMode(QFileDialog.ExistingFiles)
        filenames = QStringListModel()

        if dlg.exec_():
            filenames = dlg.selectedFiles()
            for file in filenames:
                for format in self.var.cvFormats:
                    if file.endswith(format):
                        self.tab1.fileList.append(file)
            self.getList()
            self.outputToConsole(str(len(self.tab1.fileList)) + " arquivos válidos adicionadas à lista. "
                                 + "Aguardando leitura.")

    def getList(self):
        self.pendingReading = True
        self.listedFiles.clear()
        for item in self.tab1.fileList:
            self.listedFiles.addItem(QListWidgetItem(item))

    def clearSelection(self):
        self.listedFiles.clear()
        self.tab1.fileList = []
        self.pendingReading = False
        self.clearViews()
        self.tab1.forms = []
        self.tab1.reading = None
        self.btn_Save.setEnabled(False)

    def saveDB(self):
        if(self.tab1.reading.saveDB()):
            self.loadDatabase()
            self.listedFiles.clear()
            self.tab1.fileList = []
            self.tab1.forms = []
            self.tab1.reading = None
            self.clearViews()
            self.outputToConsole("Banco de horas atualizado com sucesso.")
            self.btn_Save.setEnabled(False)
        else:
            self.outputToConsole("Erro ao atualizar banco de dados. Certifique-se de que o arquivo está fechado.")

    def runFileReader(self):
        self.outputToConsole("Lendo imagens...")
        if(len(self.tab1.fileList) > 0):
            self.pendingReading = False
            imgCount = len(self.tab1.fileList)
            self.tab1.forms = []
            count = 0
            for file in self.tab1.fileList:
                self.tab1.forms.append(ImgRead(file))
                if(self.tab1.forms[count].terminalError):
                    self.listedFiles.item(count).setBackground(QBrush(QColor(250, 150, 150)))
                elif(self.tab1.forms[count].hasHeaderError):
                    self.listedFiles.item(count).setBackground(QBrush(QColor(250, 200, 100)))
                elif(self.tab1.forms[count].hasWarnings):
                    self.listedFiles.item(count).setBackground(QBrush(QColor(250, 250, 50)))
                else:
                    self.listedFiles.item(count).setBackground(QBrush(QColor(150, 250, 150)))
                count += 1
                self.update()
                self.outputToConsole("Lendo imagem " + str(count) + " de " + str(imgCount) + "...")
                self.refreshProgBar(max = imgCount, current = count)



            self.tab1.reading = FileReader(self.tab1.forms)
            self.changeViews()
            self.refreshLog()
            self.btn_Save.setEnabled(True)
            self.btn_Save.clicked.connect(self.saveDB)
            self.outputToConsole("Leitura de imagens completa. Confira os detalhes e clique em 'Salvar Dados'.")
        else:
            self.outputToConsole("Nenhuma imagem foi selecionada.")

    def runGenerateCertificates(self):
        dlg1 = QFileDialog(caption = "Local para salvar certificados", directory=self.var.certificateDir)
        dlg1.setFileMode(QFileDialog.Directory)
        filenames = QStringListModel()

        if dlg1.exec_():
            filename = dlg1.selectedFiles()[0]
            self.var.paramTuner("certificateDir", filename)
            self.tab4.label1.setText(self.var.certificateDir)

            months = []
            months.append(self.tab3.firstMonth)
            months.append(self.tab3.secondMonth)
            gen = certificateGenerator(months, self.tab3.consult)
            count = 0
            for cert in range(gen.certCount):
                gen.saveCertificate(cert)
                count += 1
                self.update()
                self.refreshCertProgBar(max=gen.certCount, current=count)

            self.tab3.btn_Generate.setEnabled(False)
            self.outputToConsole("Sucesso! "
                                 + str(gen.certCount)
                                 + " certificados gerados. Arquivos salvos em:  "
                                 + self.var.certificateDir)

    def runConsultantManager(self):
        txt = self.tab3.box3.lineRA.text()
        if(len(txt) == 8):
            if(txt.isnumeric()):
                consultant = self.database.retrieveConsultant(txt)
                self.tab3.box3.lineConsult.setEnabled(True)
                self.tab3.box3.lineNome.setEnabled(True)
                self.tab3.box3.btn_Save.setEnabled(True)
                self.tab3.box3.btn_Cancel.setEnabled(True)
                self.tab3.box3.btn_Cancel.clicked.connect(self.clearConsultant)
                self.tab3.box3.btn_Save.clicked.connect(self.saveConsultant)
                if(consultant is False):
                    self.tab3.box3.lineRA.setStyleSheet("color: green;")
                    self.outputToConsole("RA não encontrado no Banco de Dados. "
                                         + "Modo de adição de consultor inicializado.")
                    self.tab3.box3.btn_Save.setText("Adicionar Consultor")

                else:
                    self.outputToConsole("RA encontrado no Banco de Dados. "
                                         + "Modo de edição/exclusão de consultor inicializado.")
                    self.tab3.box3.btn_Delete.setEnabled(True)
                    self.tab3.box3.lineNome.setText(consultant["NOME"])
                    self.tab3.box3.lineConsult.setText(consultant["CONSULTORIA"])
                    self.tab3.box3.btn_Delete.setStyleSheet("")
                    self.tab3.box3.btn_Delete.clicked.connect(self.confirmDeleteConsultant)
                    self.tab3.box3.lineRA.setStyleSheet("color: orange;")
                    self.tab3.box3.btn_Save.setText("Salvar Consultor")
            else:
                self.outputToConsole("O número de Registro de Aluno (RA) deve conter 8 números.")
                self.tab3.box3.lineRA.setStyleSheet("color: red;")
        else:
            self.tab3.box3.lineNome.setText("")
            self.tab3.box3.lineConsult.setText("")
            self.tab3.box3.lineNome.setEnabled(False)
            self.tab3.box3.lineConsult.setEnabled(False)
            self.tab3.box3.btn_Save.setEnabled(False)
            self.tab3.box3.btn_Cancel.setEnabled(False)
            self.tab3.box3.btn_Delete.setEnabled(False)
            self.tab3.box3.btn_Save.setText("Salvar Consultor")
            self.tab3.box3.lineRA.setStyleSheet("color: black;")

    def clearConsultant(self):
        self.tab3.box3.lineRA.setText("")
        self.tab3.box3.lineNome.setText("")
        self.tab3.box3.lineConsult.setText("")
        self.tab3.box3.lineNome.setEnabled(False)
        self.tab3.box3.lineConsult.setEnabled(False)
        self.tab3.box3.btn_Save.setEnabled(False)
        self.tab3.box3.btn_Cancel.setEnabled(False)
        self.tab3.box3.btn_Delete.setEnabled(False)
        self.tab3.box3.btn_Save.setText("Salvar Consultor")
        self.tab3.box3.lineRA.setStyleSheet("color: black;")

    def saveConsultant(self):
        consultant = {'RA': self.tab3.box3.lineRA.text(),
                      'NOME': self.tab3.box3.lineNome.text(),
                      'CONSULTORIA': self.tab3.box3.lineConsult.text()}
        if(len(consultant["NOME"]) > 0 and len(consultant["CONSULTORIA"]) > 0):
            status = self.database.saveConsultant(consultant)
            if(status == 1):
                self.outputToConsole("Consultor salvo com sucesso.")
                self.clearConsultant()
                self.loadDatabase()
            else:
                self.outputToConsole("Ops, algo deu errado. Não foi possível salvar o Banco de Dados.")
        else:
            self.outputToConsole("Preencha todos os campos.")

    def confirmDeleteConsultant(self):
        self.tab3.box3.btn_Delete.setText("Confirmar deleção")
        self.tab3.box3.btn_Delete.clicked.connect(self.deleteConsultant)
        self.tab3.box3.btn_Delete.setStyleSheet("color: red;")

    def deleteConsultant(self):
        self.tab3.box3.btn_Delete.setStyleSheet("")
        self.database.delConsultant(str(self.tab3.box3.lineRA.text()))
        self.outputToConsole("Consultor removido com sucesso.")
        self.clearConsultant()
        self.loadDatabase()

    def refreshProgBar(self, min = 0, max = 1, current = 0, reset = False):
        if(reset):
            self.progBar.reset()
        else:
            self.progBar.setRange(min, max)
            self.progBar.setValue(current)

    def refreshCertProgBar(self, min = 0, max = 1, current = 0, reset = False):
        if(reset):
            self.tab3.certProgBar.reset()
        else:
            self.tab3.certProgBar.setRange(min, max)
            self.tab3.certProgBar.setValue(current)

    def selMonth1(self, index):
        self.tab3.firstMonth = self.var.months[index]
        if(len(self.tab3.firstMonth) > 0 and len(self.tab3.secondMonth) > 0):
            self.tab3.btn_Generate.setEnabled(True)
            self.refreshCertProgBar(reset = True)
        self.outputToConsole("Primeiro mês selecionado: " + self.tab3.firstMonth)

    def selMonth2(self, index):
        self.tab3.secondMonth = self.var.months[index]
        if(len(self.tab3.firstMonth) > 0 and len(self.tab3.secondMonth) > 0):
            self.tab3.btn_Generate.setEnabled(True)
            self.refreshCertProgBar(reset=True)
        self.outputToConsole("Segundo mês selecionado: " + self.tab3.secondMonth)

    def selConsult(self, index):
        if(index > 0):
            self.tab3.consult = self.database.consultList[index - 1]
        else:
            self.tab3.consult = "Todas"
        self.outputToConsole("Consultoria selecionada: " + self.tab3.consult)

    def searchDB(self):
        if(len(self.tab3.foundItems) > 0):
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
        factor = 0.68
        self.tab1.sub2.setFixedSize(self.tab1.sub2.size())
        boxSize = self.tab1.sub2
        scale = QSize(int(boxSize.width() * factor), int(boxSize.height() * factor))
        row = self.listedFiles.currentRow()
        if (row == -1):
            row = 0
        if(not self.pendingReading):
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.forms[row].imgresize))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab1.img1.setPixmap(img)
            except:
                self.tab1.tab1.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.forms[row].imgcontour))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab2.img1.setPixmap(img)
            except:
                self.tab1.tab2.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.forms[row].imgUndist))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab3.img1.setPixmap(img)
            except:
                self.tab1.tab3.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.forms[row].imgnormal))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab4.img1.setPixmap(img)
            except:
                self.tab1.tab4.img1.setText("Erro ao ler imagem.")
            try:
                img = QPixmap(self.imgToPixmap(self.tab1.forms[row].imgAnottated))
                img = img.scaled(scale, Qt.KeepAspectRatio)
                self.tab1.tab5.img1.setPixmap(img)
            except:
                self.tab1.tab5.img1.setText("Erro ao ler imagem.")
            self.tab1.sub2.info.setText(self.tab1.reading.logToStr(self.tab1.forms[row].log))
            self.tab1.sub2.info.resize(self.tab1.sub2.info.sizeHint())
            self.tab1.sub2.infoArea.resize(self.tab1.sub2.infoArea.sizeHint())
            #width = self.tab1.sub2.width() * 0.8
            #height = self.tab1.sub2.height() * 0.3
            #self.tab1.sub2.info.setMinimumWidth(width)
            #self.tab1.sub2.info.setMinimumHeight(height)

    def clearViews(self):
        self.tab1.tab1.img1.setText("Aguardando leitura.")
        self.tab1.tab2.img1.setText("Aguardando leitura.")
        self.tab1.tab3.img1.setText("Aguardando leitura.")
        self.tab1.tab4.img1.setText("Aguardando leitura.")
        self.tab1.tab5.img1.setText("Aguardando leitura.")
        self.tab1.sub2.info.setText("Aguardando leitura.")
        self.refreshProgBar(reset=True)

    def refreshLog(self):
        self.errorLog.text.clear()
        self.errorLog.text.setText(errorLogHandler().errorLogText)
        self.errorLog.text.resize(self.errorLog.text.sizeHint())
        self.errorLog.resize(self.errorLog.sizeHint())

    def exportLog(self):
        dlg = QFileDialog()
        dlg.setDirectory(self.var.logDir)
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setAcceptMode(QFileDialog.AcceptOpen)
        dir = QStringListModel()

        if dlg.exec_():
            try:
                io = errorLogHandler()
                dir = dlg.selectedFiles()[0]
                io.errorLogExporter(dir)
                self.outputToConsole("Relatório exportado com sucesso. Arquivo localizado em: " + dir)
            except:
                self.outputToConsole("Ops, algo deu errado.")

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
        self.tab1.sub1.manageSelection = QWidget(self)
        self.tab1.sub1.manageSelection.layout = QHBoxLayout(self)
        self.tab1.sub1.layout = QVBoxLayout(self)
        self.tab1.sub1.box = QGroupBox("Realizar Leitura")
        self.tab1.sub1.box.layout = QVBoxLayout(self)
        self.tab1.sub2.layout = QVBoxLayout(self)
        self.tab1.sub2.box = QGroupBox("Detalhes da Leitura")
        self.tab1.sub2.box.layout = QVBoxLayout(self)

        ## sub1
        self.tab1.fileList = []
        self.btn_Folder = QPushButton("Selecionar pasta...")
        self.btn_Folder.clicked.connect(self.getFolder)
        self.btn_Files = QPushButton("Selecionar imagens...")
        self.btn_Files.clicked.connect(self.getFiles)
        self.btn_Clear = QPushButton("Cancelar")
        self.btn_Clear.clicked.connect(self.clearSelection)
        self.listedFiles = QListWidget()
        self.listedFiles.currentRowChanged.connect(self.changeViews)
        self.btn_Run = QPushButton("Ler imagens listadas")
        self.btn_Run.clicked.connect(self.runFileReader)
        self.progBar = QProgressBar()
        self.btn_Save = QPushButton("Salvar dados")
        self.btn_Save.setEnabled(False)
        self.tab1.sub1.manageSelection.layout.addWidget(self.btn_Folder)
        self.tab1.sub1.manageSelection.layout.addWidget(self.btn_Files)
        self.tab1.sub1.manageSelection.layout.addWidget(self.btn_Clear)
        self.tab1.sub1.manageSelection.setLayout(self.tab1.sub1.manageSelection.layout)
        self.tab1.sub1.box.layout.addWidget(self.tab1.sub1.manageSelection)
        self.tab1.sub1.box.layout.addWidget(self.listedFiles)
        self.tab1.sub1.box.layout.addWidget(self.btn_Run)
        self.tab1.sub1.box.layout.addWidget(self.progBar)
        self.tab1.sub1.box.layout.addWidget(self.btn_Save)
        self.tab1.sub1.box.setLayout(self.tab1.sub1.box.layout)
        self.tab1.sub1.layout.addWidget(self.tab1.sub1.box)
        self.tab1.sub1.box.setLayout(self.tab1.sub1.box.layout)
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


        #self.tab1.sub2.info = QLabel("Aguardando leitura." + ("\n" * 12))
        self.tab1.sub2.info = QLabel("Aguardando leitura.")
        self.tab1.sub2.info.setAlignment(Qt.AlignTop)
        self.tab1.sub2.info.setWordWrap(False)
        self.tab1.sub2.info.setMargin(16)
        self.tab1.sub2.infoArea = QScrollArea()
        #self.tab1.sub2.infoArea.resize(self.tab1.sub2.infoArea.sizeHint())
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
        self.errorLog = QWidget()
        self.errorLog.layout = QHBoxLayout(self)
        self.errorLog.text = QLabel(self.errorLogText)
        self.errorLog.text.setAlignment(Qt.AlignTop)
        self.errorLog.text.setWordWrap(False)
        self.errorLog.text.setMargin(16)
        self.errorLog.layout.addWidget(self.errorLog.text)
        self.errorLog.setLayout(self.errorLog.layout)
        self.scrollErrorLog = QScrollArea()
        self.scrollErrorLog.setWidget(self.errorLog)
        self.tab2.layout.addWidget(self.scrollErrorLog)

        self.tab2.btn_Export = QPushButton("Exportar Relatório...")
        self.tab2.btn_Export.clicked.connect(self.exportLog)
        self.tab2.layout.addWidget(self.tab2.btn_Export)

        self.tab2.setLayout(self.tab2.layout)

    def get_tab3(self):
        self.tab3.firstMonth = []
        self.tab3.secondMonth = []
        self.tab3.consult = "Todas"
        self.tab3.searchText = ""
        self.tab3.foundItems = []

        self.tab3.layout = QGridLayout()

        self.tab3.box1 = QGroupBox("Banco de Horas")
        self.tab3.box1.layout = QVBoxLayout()
        self.tab3.box1.dbtable = QWidget()
        self.tab3.box1.dbtable.layout = QVBoxLayout()
        self.tab3.box1.searchBar = QWidget()
        self.tab3.box1.searchBar.layout = QHBoxLayout()
        self.tab3.search = QLineEdit()
        self.tab3.search.setPlaceholderText(" Pesquise pelo RA, nome ou consultoria...")
        self.tab3.search.textChanged.connect(self.changeSearchText)
        self.tab3.btn_Search = QPushButton("Pesquisar")
        self.tab3.btn_Search.clicked.connect(self.searchDB)
        self.tab3.btn_Clear = QPushButton("Limpar")
        self.tab3.btn_Clear.clicked.connect(self.clearSearch)
        self.tab3.box1.searchBar.layout.addWidget(self.tab3.search)
        self.tab3.box1.searchBar.layout.addWidget(self.tab3.btn_Search)
        self.tab3.box1.searchBar.layout.addWidget(self.tab3.btn_Clear)
        self.tab3.box1.searchBar.setLayout(self.tab3.box1.searchBar.layout)
        self.tab3.box1.dbtable.layout.addWidget(self.tab3.box1.searchBar)
        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        self.loadDatabase()
        self.tab3.box1.dbtable.layout.addWidget(self.table)
        self.tab3.box1.dbtable.setLayout(self.tab3.box1.dbtable.layout)
        self.tab3.box1.layout.addWidget(self.tab3.box1.searchBar)
        self.tab3.box1.layout.addWidget(self.tab3.box1.dbtable)
        self.tab3.box1.setLayout(self.tab3.box1.layout)

        self.tab3.box2 = QGroupBox("Gerar Certificados")
        self.tab3.box2.layout = QVBoxLayout(self)
        self.tab3.label_Generate = QLabel("Selecione 2 meses de exercício e uma consultoria."
                                          + " Para gerar os certificados, clique em Gerar Certificados.")
        self.tab3.label_Generate.setAlignment(Qt.AlignCenter)
        self.tab3.box2.layout.addWidget(self.tab3.label_Generate)
        self.tab3.box2.buttons = QWidget()
        self.tab3.box2.buttons.layout = QHBoxLayout()
        self.tab3.monthSel1 = QComboBox()
        self.tab3.monthSel1.addItems(self.var.months)
        self.tab3.monthSel1.activated.connect(self.selMonth1)
        self.tab3.box2.buttons.layout.addWidget(self.tab3.monthSel1)
        self.tab3.monthSel2 = QComboBox()
        self.tab3.monthSel2.addItems(self.var.months)
        self.tab3.monthSel2.activated.connect(self.selMonth2)
        self.tab3.box2.buttons.layout.addWidget(self.tab3.monthSel2)
        self.tab3.consultSel = QComboBox()
        self.tab3.consultSel.addItem("Todas")
        self.tab3.consultSel.addItems(self.database.consultList)
        self.tab3.consultSel.activated.connect(self.selConsult)
        self.tab3.box2.buttons.layout.addWidget(self.tab3.consultSel)
        self.tab3.btn_Generate = QPushButton('Gerar Certificados')
        self.tab3.btn_Generate.setEnabled(False)
        self.tab3.btn_Generate.clicked.connect(self.runGenerateCertificates)
        self.tab3.box2.buttons.layout.addWidget(self.tab3.btn_Generate)
        self.tab3.box2.buttons.setLayout(self.tab3.box2.buttons.layout)
        self.tab3.box2.layout.addWidget(self.tab3.box2.buttons)
        self.tab3.certProgBar = QProgressBar()
        self.tab3.box2.layout.addWidget(self.tab3.certProgBar)
        self.tab3.box2.setLayout(self.tab3.box2.layout)

        self.tab3.box3 = QGroupBox("Gerenciar consultor")
        self.tab3.box3.layout = QVBoxLayout()
        self.tab3.box3.manager = QWidget()
        self.tab3.box3.manager.layout = QFormLayout()
        self.tab3.box3.lineRA = QLineEdit()
        self.tab3.box3.lineRA.setPlaceholderText(" Insira o RA para começar...")
        self.tab3.box3.lineRA.setMaxLength(8)
        self.tab3.box3.lineRA.textChanged.connect(self.runConsultantManager)
        self.tab3.box3.lineNome = QLineEdit()
        self.tab3.box3.lineNome.setEnabled(False)
        self.tab3.box3.lineConsult = QLineEdit()
        self.tab3.box3.lineConsult.setEnabled(False)
        self.tab3.box3.buttons = QWidget()
        self.tab3.box3.buttons.layout = QHBoxLayout()
        self.tab3.box3.btn_Save = QPushButton("Salvar Consultor")
        self.tab3.box3.btn_Save.setEnabled(False)
        self.tab3.box3.btn_Delete = QPushButton("Excluir Consultor")
        self.tab3.box3.btn_Delete.setEnabled(False)
        self.tab3.box3.btn_Cancel = QPushButton("Cancelar")
        self.tab3.box3.btn_Cancel.setEnabled(False)
        self.tab3.box3.buttons.layout.addWidget(self.tab3.box3.btn_Save)
        self.tab3.box3.buttons.layout.addWidget(self.tab3.box3.btn_Delete)
        self.tab3.box3.buttons.layout.addWidget(self.tab3.box3.btn_Cancel)
        self.tab3.box3.buttons.setLayout(self.tab3.box3.buttons.layout)
        self.tab3.box3.manager.layout.addRow("RA:", self.tab3.box3.lineRA)
        self.tab3.box3.manager.layout.addRow("Nome:", self.tab3.box3.lineNome)
        self.tab3.box3.manager.layout.addRow("Consultoria", self.tab3.box3.lineConsult)
        self.tab3.box3.manager.layout.addRow("", self.tab3.box3.buttons)
        self.tab3.box3.manager.setLayout(self.tab3.box3.manager.layout)
        self.tab3.box3.layout.addWidget(self.tab3.box3.manager)
        self.tab3.box3.setLayout(self.tab3.box3.layout)

        self.tab3.spacer = QSpacerItem(1,1)


        self.tab3.layout.addWidget(self.tab3.box1, 0, 0, 0, 1)
        self.tab3.layout.addWidget(self.tab3.box3, 0, 1)
        self.tab3.layout.addWidget(self.tab3.box2, 1, 1)
        self.tab3.layout.addItem(self.tab3.spacer, 2, 1)
        self.tab3.layout.setRowStretch(2, 1)
        self.tab3.setLayout(self.tab3.layout)

    def changeConfig0(self):
        dlg0 = QFileDialog()
        dlg0.setFileMode(QFileDialog.ExistingFile)
        filenames = QStringListModel()

        if dlg0.exec_():
            dlg0.setDirectory(self.var.databaseFile)
            filename = dlg0.selectedFiles()[0]
            if(filename.endswith(".csv")):
                self.var.paramTuner("databaseFile", filename)
                self.outputToConsole("Configuração atualizada.")
                self.tab4.label0.setText(filename)
                self.loadDatabase()
            else:
                self.outputToConsole("Tipo de arquivo inválido.")

    def changeConfig1(self):
        dlg1 = QFileDialog(directory=self.var.certificateDir)
        dlg1.setFileMode(QFileDialog.Directory)
        filenames = QStringListModel()

        if dlg1.exec_():
            filename = dlg1.selectedFiles()[0]
            self.var.paramTuner("certificateDir", filename)
            self.tab4.label1.setText(self.var.certificateDir)
            self.outputToConsole("Configuração atualizada.")

    def changeConfig2(self):
        dlg2 = QFileDialog(directory=self.var.logDir)
        dlg2.setFileMode(QFileDialog.Directory)
        filenames = QStringListModel()

        if dlg2.exec_():
            filename = dlg2.selectedFiles()[0]
            self.var.paramTuner("logDir", filename)
            self.tab4.label2.setText(self.var.logDir)
            self.outputToConsole("Configuração atualizada.")

    def changeConfig3(self):
        dlg3 = QFileDialog(directory=self.var.imgDir)
        dlg3.setFileMode(QFileDialog.Directory)
        filenames = QStringListModel()

        if dlg3.exec_():
            filename = dlg3.selectedFiles()[0]
            self.var.paramTuner("imgDir", filename)
            self.tab4.label3.setText(self.var.imgDir)
            self.outputToConsole("Configuração atualizada.")

    def changeConfig4(self):
        value = self.tab4.config4.value()
        self.var.paramTuner("imgPreviewSize", str(value))
        self.outputToConsole("Configuração atualizada. Tamanho da imagem de preview: " + str(value))

    def changeConfig5(self):
        value = float(self.tab4.config5.value())/100
        self.var.paramTuner("threshold", str(value))
        self.outputToConsole("Configuração atualizada. Limiar de leitura: " + str(value))
        self.tab4.config5.setToolTip("Valor atual: "
                                     + str(self.var.threshold * 100)
                                     + "%\nValor padrão: 20%\n"
                                     + "Este valor determina a tolerância de distorções na leitura de imagens.\n"
                                     + "Consulte a documentação para mais detalhes.")

    def changeConfig6(self):
        value = self.tab4.config6.value()
        self.var.paramTuner("minimumHours", str(value))
        self.outputToConsole("Configuração atualizada. Tempo mínimo para emissão de certificado: "
                             + str(value)
                             + " horas.")
        self.tab4.config6.setToolTip("Valor atual: "
                                     + str(self.var.minimumHours)
                                     + " horas\nValor padrão: 20 horas\n"
                                     + "Este valor determina o mínimo de horas que um consultor precisa atingir em 2 "
                                     + "meses de atividade.")

    def checkFileExists(self, path):
        txt = path
        try:
            isExistent = os.lstat(txt)
            isExistent = True
        except:
            isExistent = False
        return isExistent

    def changeLabel0(self):
        txt = self.tab4.label0.text()
        if(self.checkFileExists(txt)):
            self.var.paramTuner("databaseFile", txt)
            self.tab4.label0.setStyleSheet("")
            self.outputToConsole("Configuração atualizada:   Banco de Horas - " + txt)
            self.loadDatabase()
            self.tab3.consultSel.clear()
            self.tab3.consultSel.addItems(self.database.consultList)
            self.tab3.consult = "Todas"
        else:
            self.tab4.label0.setStyleSheet("color: red;")
            self.outputToConsole("Arquivo inexistente.")

    def changeLabel1(self):
        self.var.paramTuner("certificateDir", self.tab4.label1.text())
        self.outputToConsole("Configuração atualizada.")

    def changeLabel2(self):
        self.var.paramTuner("logDir", self.tab4.label2.text())
        self.outputToConsole("Configuração atualizada.")

    def changeLabel3(self):
        self.var.paramTuner("imgDir", self.tab4.label3.text())
        self.outputToConsole("Configuração atualizada.")

    def get_tab4(self):
        self.tab4.layout = QFormLayout(self)
        self.tab4.layout.setLabelAlignment(Qt.AlignLeft)
        self.tab4.layout.setRowWrapPolicy(QFormLayout.DontWrapRows)

        self.tab4.params = ["Banco de Horas:",
                            "Arquivo de certificados:",
                            "Pasta de Relatórios:",
                            "Pasta de Imagens:",
                            "Tamanho da imagem de preview:",
                            "Limiar de leitura:",
                            "Tempo mínimo para certificado:"]
        self.tab4.param0 = QLabel(self.tab4.params[0])
        self.tab4.param1 = QLabel(self.tab4.params[1])
        self.tab4.param2 = QLabel(self.tab4.params[2])
        self.tab4.param3 = QLabel(self.tab4.params[3])
        self.tab4.param4 = QLabel(self.tab4.params[4])
        self.tab4.param5 = QLabel(self.tab4.params[5])
        self.tab4.param6 = QLabel(self.tab4.params[6])

        self.tab4.label0 = QLineEdit(self.var.databaseFile)
        if(not self.checkFileExists(self.var.databaseFile)):
            self.tab4.label0.setStyleSheet("color: red;")
            self.outputToConsole("Configurações inválidas.")
            self.tabs.setCurrentWidget(self.tab4)
        self.tab4.label1 = QLineEdit(self.var.certificateDir)
        self.tab4.label2 = QLineEdit(self.var.logDir)
        self.tab4.label3 = QLineEdit(self.var.imgDir)

        self.tab4.config0 = QPushButton("...")
        self.tab4.config1 = QPushButton("...")
        self.tab4.config2 = QPushButton("...")
        self.tab4.config3 = QPushButton("...")
        self.tab4.config4 = QSpinBox()
        self.tab4.config5 = QSlider(Qt.Horizontal)
        self.tab4.config6 = QSlider(Qt.Horizontal)

        self.tab4.config4.setMaximum(20)
        self.tab4.config4.setMinimum(1)
        self.tab4.config4.setValue(self.var.imgPreviewSize)
        self.tab4.config4.setToolTip("Valor padrão: " + str(self.var.imgPreviewSize))

        self.tab4.config5.setRange(0, 100)
        self.tab4.config5.setSingleStep(1)
        self.tab4.config5.setValue(int(self.var.threshold * 100))
        self.tab4.config5.setTickPosition(QSlider.TicksBelow)
        self.tab4.config5.setTickInterval(1)
        self.tab4.config5.setToolTip("Valor atual: "
                                     + str(self.var.threshold * 100)
                                     + "%\nValor padrão: 20%\n"
                                     + "Este valor determina a tolerância de distorções na leitura de imagens.\n"
                                     + "Consulte a documentação para mais detalhes.")

        self.tab4.config6.setRange(0, 60)
        self.tab4.config6.setSingleStep(1)
        self.tab4.config6.setValue(int(self.var.minimumHours))
        self.tab4.config6.setTickPosition(QSlider.TicksBelow)
        self.tab4.config6.setTickInterval(5)
        self.tab4.config6.setToolTip("Valor atual: "
                                     + str(self.var.minimumHours)
                                     + " horas\nValor padrão: 20 horas\n"
                                     + "Este valor determina o mínimo de horas que um consultor precisa atingir em 2 "
                                     + "meses de atividade para receber um certificado.")

        self.tab4.label0.textChanged.connect(self.changeLabel0)
        self.tab4.label1.textChanged.connect(self.changeLabel1)
        self.tab4.label2.textChanged.connect(self.changeLabel2)
        self.tab4.label3.textChanged.connect(self.changeLabel3)
        self.tab4.config0.clicked.connect(self.changeConfig0)
        self.tab4.config1.clicked.connect(self.changeConfig1)
        self.tab4.config2.clicked.connect(self.changeConfig2)
        self.tab4.config3.clicked.connect(self.changeConfig3)
        self.tab4.config4.valueChanged.connect(self.changeConfig4)
        self.tab4.config5.sliderReleased.connect(self.changeConfig5)
        self.tab4.config6.sliderReleased.connect(self.changeConfig6)

        self.tab4.config0layout = QHBoxLayout(self)
        self.tab4.config0layout.addWidget(self.tab4.label0)
        self.tab4.config0layout.addWidget(self.tab4.config0)
        self.tab4.config1layout = QHBoxLayout()
        self.tab4.config1layout.addWidget(self.tab4.label1)
        self.tab4.config1layout.addWidget(self.tab4.config1)
        self.tab4.config2layout = QHBoxLayout()
        self.tab4.config2layout.addWidget(self.tab4.label2)
        self.tab4.config2layout.addWidget(self.tab4.config2)
        self.tab4.config3layout = QHBoxLayout()
        self.tab4.config3layout.addWidget(self.tab4.label3)
        self.tab4.config3layout.addWidget(self.tab4.config3)

        self.tab4.layout.addRow(self.tab4.param0, self.tab4.config0layout)
        self.tab4.layout.addRow(self.tab4.param1, self.tab4.config1layout)
        self.tab4.layout.addRow(self.tab4.param2, self.tab4.config2layout)
        self.tab4.layout.addRow(self.tab4.param3, self.tab4.config3layout)
        self.tab4.layout.addRow(self.tab4.param4, self.tab4.config4)
        self.tab4.layout.addRow(self.tab4.param5, self.tab4.config5)
        self.tab4.layout.addRow(self.tab4.param6, self.tab4.config6)


        self.tab4.setLayout(self.tab4.layout)

    def get_tab5(self):
        self.tab5.layout = QVBoxLayout(self)
        self.about = QLabel(creditText)
        self.about.setWordWrap(True)
        self.about.setAlignment(Qt.AlignTop)
        self.about.setMargin(16)
        self.tab5.layout.addWidget(self.about)

#        self.tab5.logos = QWidget()
#        self.tab5.logos.layout = QVBoxLayout()
#        self.tab5.logos.empresarial = QLabel()
#        self.tab5.logos.empresarial.img = QPixmap("EMPRESARIAL.png")
#        self.tab5.logos.empresarial.img.scaled(5,1, Qt.KeepAspectRatio)
#        self.tab5.logos.empresarial.setPixmap(self.tab5.logos.empresarial.img)
#        self.tab5.logos.inovec = QLabel()
#        self.tab5.logos.inovec.img = QPixmap("LOGO.png")
#        self.tab5.logos.inovec.img.scaled(5,1, Qt.KeepAspectRatio)
#        self.tab5.logos.inovec.setPixmap(self.tab5.logos.inovec.img)
#        self.tab5.logos.formcv = QLabel()
#        self.tab5.logos.formcv.img = QPixmap("FORMCV.png")
#        self.tab5.logos.formcv.img.scaled(5,1, Qt.KeepAspectRatio)
#        self.tab5.logos.formcv.setPixmap(self.tab5.logos.formcv.img)
#        self.tab5.logos.layout.addWidget(self.tab5.logos.empresarial)
#        self.tab5.logos.layout.addWidget(self.tab5.logos.inovec)
#        self.tab5.logos.layout.addWidget(self.tab5.logos.formcv)
#        self.tab5.logos.setLayout(self.tab5.logos.layout)

#        self.tab5.layout.addWidget(self.tab5.logos)

        self.tab5.setLayout(self.tab5.layout)



