from core import *

import sys
import csv
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
        self.width = 900
        self.height = 600
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.table_widget = MyTableWidget(self)
        self.setCentralWidget(self.table_widget)

        self.show()


class MyTableWidget(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.var = Var()

        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tabs.resize(900, 600)

        # TAB INDEX
        self.tabs.addTab(self.tab1, "Leitura")
        self.tabs.addTab(self.tab2, "Relatório")
        self.tabs.addTab(self.tab3, "Banco de Horas")
        self.tabs.addTab(self.tab4, "Configurações")
        self.tabs.addTab(self.tab5, "Sobre")

        # LEITURA
        self.tab1.layout = QHBoxLayout(self)
        self.tab1.sub1 = QWidget()
        self.tab1.sub2 = QWidget()
        self.tab1.sub1.layout = QVBoxLayout(self)
        self.tab1.sub2.layout = QVBoxLayout(self)

        ## sub1
        self.label1 = QLabel(self.var.imgDir)
        self.btn_Folder = QPushButton("Selecionar pasta")
        self.btn_Folder.clicked.connect(self.getFolder)
        self.btn_Files = QPushButton("Selecionar imagens")
        self.btn_Files.clicked.connect(self.getFiles)
        self.tab1.sub1.layout.addWidget(self.label1)
        self.tab1.sub1.layout.addWidget(self.btn_Folder)
        self.tab1.sub1.layout.addWidget(self.btn_Files)
        self.tab1.sub1.setLayout(self.tab1.sub1.layout)

        ## sub2
        self.tab1.tabs = QTabWidget()
        self.tab1.tab1 = QWidget()
        self.tab1.tab2 = QWidget()
        self.tab1.tab3 = QWidget()
        self.tab1.tab4 = QWidget()
        self.tab1.tab5 = QWidget()
        self.tab1.tabs.addTab(self.tab1.tab1, "1")
        self.tab1.tabs.addTab(self.tab1.tab2, "2")
        self.tab1.tabs.addTab(self.tab1.tab3, "3")
        self.tab1.tabs.addTab(self.tab1.tab4, "4")
        self.tab1.tabs.addTab(self.tab1.tab5, "5")

        self.tab1.tab1.layout = QVBoxLayout()
        self.tab1.tab1.img1 = QLabel()
        self.tab1.tab1.img1.setPixmap(QPixmap(self.cv_to_qt(ImgRead().imgAnottated)))
        self.tab1.tab1.layout.addWidget(self.tab1.tab1.img1)
        self.tab1.tab1.setLayout(self.tab1.tab1.layout)


        self.tab1.sub2.layout.addWidget(self.tab1.tabs)
        self.tab1.sub2.setLayout(self.tab1.sub2.layout)

        self.tab1.layout.addWidget(self.tab1.sub1)
        self.tab1.layout.addWidget(self.tab1.sub2)
        self.tab1.setLayout(self.tab1.layout)

        # RELATORIO
        self.errorLogText = errorLogHandler().errorLogText
        self.tab2.layout = QVBoxLayout(self)
        self.errorLog = QLabel(self.errorLogText)
        self.errorLog.setWordWrap(False)
        self.errorLog.setMargin(16)
        self.scrollErrorLog = QScrollArea()
        self.scrollErrorLog.setWidget(self.errorLog)
        self.tab2.layout.addWidget(self.scrollErrorLog)
        self.tab2.setLayout(self.tab2.layout)

        # BANCO DE HORAS
        self.database = DBhandler()
        self.tab3.layout = QVBoxLayout()
        self.table = QTableWidget()
        self.setMyData(self.database.dbdict)
        #self.scrollDatabase = QScrollArea()
        #self.scrollDatabase.setWidget(self.table)
        self.tab3.layout.addWidget(self.table)
        self.tab3.setLayout(self.tab3.layout)

        # CONFIGS
        self.tab4.layout = QFormLayout(self)
        self.config1 = QLabel("Banco de horas:")
        self.param1 = QLineEdit(self.var.imgDir)
        self.config2 = QLabel("Arquivo de relatório")
        self.param2 = QLineEdit(self.var.errorLogFile)

        self.tab4.layout.addWidget(self.config1)
        self.tab4.layout.addWidget(self.param1)
        self.tab4.setLayout(self.tab4.layout)

        # SOBRE
        self.tab5.layout = QVBoxLayout(self)
        self.about = QLabel(creditText)
        self.about.setWordWrap(True)
        self.errorLog.setMargin(16)
        self.tab5.layout.addWidget(self.about)
        self.tab5.setLayout(self.tab5.layout)

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def cv_to_qt(self, img):
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

        if dlg.exec_():
            path = dlg.selectedFiles()
            self.var.paramTuner('imgDir', path[0])
            self.label1.setText(path[0])
            FileReader()

    def getFiles(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFiles)
        #dlg.setFilter(self.var.cvFormats)
        filenames = QStringListModel()

        if dlg.exec_():
            filenames = dlg.selectedFiles()
            self.label1.setText(str(filenames))
            FileReader(fromImgDir=False, imgAddress=filenames, showErrorImage=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())



