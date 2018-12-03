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
        self.tab1.layout = QVBoxLayout(self)
        self.label1 = QLabel(self.var.imgDir)
        self.pushButton1 = QPushButton("Iniciar leitura")
        self.pushButton1.clicked.connect(self.run_FileReader)
        self.tab1.layout.addWidget(self.label1)
        self.tab1.layout.addWidget(self.pushButton1)
        self.tab1.setLayout(self.tab1.layout)

        # RELATORIO
        self.errorLogText = errorLogHandler().errorLogText
        self.tab2.layout = QVBoxLayout(self)
        self.errorLog = QLabel(self.errorLogText)
        self.errorLog.setWordWrap(False)
        self.errorLog.setMargin(16)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.errorLog)
        self.tab2.layout.addWidget(self.scroll)
        self.tab2.setLayout(self.tab2.layout)

        # BANCO DE HORAS
        self.fileName = self.var.databaseFile
        self.model = QStandardItemModel(self)
        self.tableView = QTableView(self)
        self.tableView.setModel(self.model)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.pushButtonLoad = QPushButton(self)
        self.pushButtonLoad.setText("Load Csv File!")
        self.pushButtonLoad.clicked.connect(self.on_pushButtonLoad_clicked)
        self.pushButtonWrite = QPushButton(self)
        self.pushButtonWrite.setText("Write Csv File!")
        self.pushButtonWrite.clicked.connect(self.on_pushButtonWrite_clicked)
        self.tab3.layoutVertical = QVBoxLayout(self)
        self.tab3.layoutVertical.addWidget(self.tableView)
        self.tab3.layoutVertical.addWidget(self.pushButtonLoad)
        self.tab3.layoutVertical.addWidget(self.pushButtonWrite)
        self.tab3.setLayout(self.tab3.layoutVertical)

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

    def loadCsv(self, fileName):
        with open(fileName, "rb") as fileInput:
            for row in csv.reader(fileInput):
                items = [
                    QStandardItem(field)
                    for field in row
                ]
                self.model.appendRow(items)

    def writeCsv(self, fileName):
        with open(fileName, "wb") as fileOutput:
            writer = csv.writer(fileOutput)
            for rowNumber in range(self.model.rowCount()):
                fields = [
                    self.model.data(
                        self.model.index(rowNumber, columnNumber),
                        Qt.DisplayRole
                    )
                    for columnNumber in range(self.model.columnCount())
                ]
                writer.writerow(fields)

    @pyqtSlot()
    def on_pushButtonWrite_clicked(self):
        self.writeCsv(self.fileName)

    @pyqtSlot()
    def on_pushButtonLoad_clicked(self):
        self.loadCsv(self.fileName)

    @pyqtSlot()
    def run_FileReader(self):
        self.var.imgDir = "C:\\Dropbox\\INOVEC\\FormCV\\IMG\\Outubro\\Ambivet\\arroz"
        self.label1.setText(self.var.imgDir)
        FileReader(multiple=False,
                   imgAddress="C:\\Dropbox\\INOVEC\\FormCV\\IMG\\Outubro\\Ambivet\\20181113_143229.jpg",
                   showErrorImage=True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())



