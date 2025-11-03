import sys

from PyQt6.QtCore import QPoint, Qt, QUrl
from PyQt6.QtGui import QScreen, QFontDatabase, QCloseEvent, QTextDocument
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QMainWindow, QDialog, QLabel, QVBoxLayout, QMessageBox, \
    QListWidget, QLineEdit, QComboBox, QListWidgetItem, QPushButton, QTextBrowser

import backend as bck
from backend import AppRequest
import shared_constrains as shared_constrains


class QTitleLabel(QLabel):
    """
    Label with increased font size.
    Implemented in stylesheet.txt
    """
    pass

class LinkedListWidgetItem(QListWidgetItem):
    def __init__(self, *args):
        super().__init__(*args)
        self.linkedIndex: int = -1


class CustomWindow(QMainWindow):
    def __init__(self, back: bck.AppBackend):
        super().__init__()
        # Move window to center of main screen
        self.stylesheet = None
        monitor = QScreen.virtualSiblings(super().screen())[0].availableGeometry()
        self.resize(1100, 800)
        self.move(QPoint(monitor.left() + monitor.width() // 2 - self.width() // 2,
                         monitor.top() + monitor.height() // 2 - self.height() // 2))
        self.loadStylesheet()


    def loadStylesheet(self) -> None:
        with open("src/stylesheet.txt", "r", encoding="utf-8") as fr:
            style = fr.read()
        # Load font
        fontId = QFontDatabase.addApplicationFont("src/NerdFontMono-Light.ttf")
        if fontId >= 0:
            families = QFontDatabase.applicationFontFamilies(fontId)
            style = style.replace("!!nerdFontMono!!", f"font-family: \"{families[0]}\";")
        else:
            QMessageBox.warning(self, "Внимание", "Не удалось активировать шрифт. Убедитесь, что по пути "
                                                  "src/NerdFonoMono-Light.ttf расположен рабочий шрифт"
                                                  "\nРабота будет продолжена с системным шрифтом")
            style = style.replace("!!nerdFontMono!!", "")
        # noinspection PyUnboundLocalVariable
        self.stylesheet = style
        self.setStyleSheet(style)


class AboutWindow(QDialog):
    def __init__(self, window: CustomWindow, back: bck.AppBackend):
        super().__init__()
        self.setWindowTitle("About DenisJava's WebRequests")
        self.setStyleSheet(window.stylesheet)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QTitleLabel("DenisJava's WebRequests"))
        layout.addWidget(QLabel(shared_constrains.about))
        self.show()


class LibraryWindow(QDialog):
    def __init__(self, window: CustomWindow, back: bck.AppBackend, lib: str):
        super().__init__()
        self.setWindowTitle(f"About {lib}")
        self.setStyleSheet(window.stylesheet)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QTitleLabel(lib))
        with open(f"about/{lib}.txt", "r", encoding="utf-8") as fr:
            layout.addWidget(QLabel(fr.read()))
        self.show()


class UrlSelectorWidget(QWidget):
    def __init__(self, back: bck.AppBackend):
        super().__init__()
        layout = QHBoxLayout(self)
        self.methodSelector = QComboBox(self)
        self.methodSelector.addItems(shared_constrains.http_methods)
        self.methodSelector.currentTextChanged.connect(
            lambda: back.updateCurrentRequest("method", self.methodSelector.currentText()))
        layout.addWidget(self.methodSelector)
        self.lineEdit = QLineEdit(self)
        self.lineEdit.textEdited.connect(lambda: back.updateCurrentRequest("url", self.lineEdit.text()))
        layout.addWidget(self.lineEdit)
        self.sendBtn = QPushButton("Отправить", self)
        self.sendBtn.clicked.connect(back.sendRequest)
        layout.addWidget(self.sendBtn)
        layout.setSpacing(0)
        self.setLayout(layout)

    def emitDataUpdate(self, back: bck.AppBackend):
        selected: AppRequest = back.model.getSelectedRequest()
        if selected is None:
            self.methodSelector.setCurrentIndex(0)
            self.methodSelector.setDisabled(True)
            self.lineEdit.setText("")
            self.lineEdit.setDisabled(True)
            return
        self.methodSelector.setCurrentIndex(shared_constrains.http_methods.index(selected.method))
        self.methodSelector.setDisabled(False)
        self.lineEdit.setText(selected.url)
        self.lineEdit.setDisabled(False)



class MainWidget(QWidget):
    def __init__(self, back: bck.AppBackend):
        super().__init__()

        self.back = back
        dashboard = QWidget()
        dashboardLayout = QVBoxLayout(dashboard)
        self.requestName = QLineEdit(self)
        self.requestName.setText(shared_constrains.no_request_selected)
        self.requestName.setObjectName("requestName")
        self.requestName.textEdited.connect(self.requestNameChanged)
        dashboardLayout.addWidget(self.requestName)
        self.urlSelectorWidget: UrlSelectorWidget = UrlSelectorWidget(back)
        dashboardLayout.addWidget(self.urlSelectorWidget)
        dashboardLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        dashboard.setLayout(dashboardLayout)

        layout = QHBoxLayout(self)
        self.requestList: QListWidget = QListWidget()
        self.requestList.itemClicked.connect(lambda: back.selectRequest(self.requestList.selectedItems()))
        layout.addWidget(self.requestList)
        layout.addWidget(dashboard)
        layout.setStretchFactor(dashboard, 1)
        self.setLayout(layout)

    def requestNameChanged(self):
        selected = self.back.model.getSelectedRequest()
        if selected is None:
            return
        selected.name = self.requestName.text()
        self.updateRequestList(self.back)

    def emitDataUpdate(self, back: bck.AppBackend):
        self.updateRequestList(back)
        selected = back.model.getSelectedRequest()
        if selected is None:
            self.requestName.setText(shared_constrains.no_request_selected)
        else:
            self.requestName.setText(selected.name)
        self.urlSelectorWidget.emitDataUpdate(back)

    def updateRequestList(self, back: bck.AppBackend):
        self.requestList.clear()
        self.requestList.addItem(LinkedListWidgetItem(shared_constrains.new_http_request))
        for i, req in enumerate(back.model.requests):
            item = LinkedListWidgetItem(req.name)
            item.linkedIndex = i
            self.requestList.addItem(item)


class MainWindow(CustomWindow):
    def __init__(self, back: bck.AppBackend):
        super().__init__(back)
        self.setWindowTitle("DenisJava's WebRequests")
        self.widget: MainWidget = MainWidget(back)
        self.setCentralWidget(self.widget)
        self.backend = back
        self.backend.window = self

        # MenuBar
        filesMenu = self.menuBar().addMenu("Файл")
        filesMenu.addAction("Открыть...").triggered.connect(back.openFile)
        filesMenu.addAction("Сохранить").triggered.connect(back.saveFile)
        filesMenu.addSeparator()
        filesMenu.addAction("Выход").triggered.connect(back.exit)

        secretsMenu = self.menuBar().addMenu("Секреты")

        testsMenu = self.menuBar().addMenu("Тестирование")

        helpMenu = self.menuBar().addMenu("Помощь")
        helpMenu.addAction("О программе").triggered.connect(back.showAboutWindow)

        libsMenu = helpMenu.addMenu("Использованные библиотеки")
        libsMenu.addAction("PyQt6").triggered.connect(back.showQtAboutWindow)
        libsMenu.addAction("requests").triggered.connect(lambda: self.libraryAbout("requests"))

        self.statusBar().showMessage("")

        if "-dev" in sys.argv:
            self.statusBar().showMessage("DenisJava's WebRequests запущен в режиме разработчика")
            back.openFile0("test.djwr")

    def libraryAbout(self, lib: str):
        LibraryWindow(self, self.backend, lib).exec()

    def closeEvent(self, event: QCloseEvent):
        self.backend.exit()

    def emitDataUpdate(self, back: bck.AppBackend):
        self.widget.emitDataUpdate(back)
