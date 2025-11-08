import sys

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QScreen, QFontDatabase, QCloseEvent, QIcon
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QMainWindow, QLabel, QVBoxLayout, QMessageBox, \
    QListWidget, QLineEdit, QComboBox, QListWidgetItem, QPushButton, QTabWidget, QStyle, QTableView, QHeaderView

import backend as bck
import shared_constrains as shared_constrains


class QTitleLabel(QLabel):
    """
    Label with increased font size.
    Implemented in stylesheet.txt
    """
    pass

class WarningToast(QLabel):
    """
    QLabel for warning messages.
    Implemented in stylesheet.txt
    """
    def __init__(self, text: str):
        super().__init__(text)

class LinkedListWidgetItem(QListWidgetItem):
    def __init__(self, *args):
        super().__init__(*args)
        self.linkedIndex: int = -1


class CustomWindow(QMainWindow):
    def __init__(self, back: bck.AppBackend):
        super().__init__()
        self.resize(1100, 800)
        self.centerOnScreen()
        self.loadStylesheet()
        self.setWindowIcon(QIcon("assets/icon.png"))

    def centerOnScreen(self):
        monitor = QScreen.virtualSiblings(super().screen())[0].availableGeometry()
        self.move(QPoint(monitor.left() + monitor.width() // 2 - self.width() // 2,
                         monitor.top() + monitor.height() // 2 - self.height() // 2))

    def loadStylesheet(self) -> None:
        with open("assets/stylesheet.txt", "r", encoding="utf-8") as fr:
            style = fr.read()
        # Load font
        fontId = QFontDatabase.addApplicationFont("assets/NerdFontMono-Light.ttf")
        if fontId >= 0:
            families = QFontDatabase.applicationFontFamilies(fontId)
            style = style.replace("!!nerdFontMono!!", f"font-family: \"{families[0]}\";")
        else:
            QMessageBox.warning(self, "Внимание", "Не удалось активировать шрифт. Убедитесь, что по пути "
                                                  "assets/NerdFonoMono-Light.ttf расположен рабочий шрифт."
                                                  "\nРабота будет продолжена с системным шрифтом")
            style = style.replace("!!nerdFontMono!!", "")
        shared_constrains.stylesheet = style
        self.setStyleSheet(style)


class AboutWindow(CustomWindow):
    def __init__(self, window: CustomWindow, back: bck.AppBackend):
        super().__init__(back)
        self.setWindowTitle("About DenisJava's WebRequests")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QTitleLabel("DenisJava's WebRequests"))
        layout.addWidget(QLabel(shared_constrains.about))
        self.back = back
        self.back.antiGC["about"] = self
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.resize(self.minimumSizeHint())
        self.centerOnScreen()
        self.show()

    def closeEvent(self, a0):
        self.back.antiGC["about"] = None
        super().closeEvent(a0)


class LibraryWindow(CustomWindow):
    def __init__(self, window: CustomWindow, back: bck.AppBackend, lib: str):
        super().__init__(back)
        self.setWindowTitle(f"About {lib}")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QTitleLabel(lib))
        with open(f"about/{lib}.txt", "r", encoding="utf-8") as fr:
            layout.addWidget(QLabel(fr.read()))
        self.windowId = f"lib_{lib}"
        self.back = back
        self.back.antiGC[self.windowId] = self
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.resize(self.minimumSizeHint())
        self.centerOnScreen()
        self.show()

    def closeEvent(self, a0):
        self.back.antiGC[self.windowId] = None
        super().closeEvent(a0)


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

    def emitDataUpdate(self, back: bck.AppBackend, selected: bck.AppRequest):
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


class CookiesViewWidget(QWidget):
    def __init__(self, back: bck.AppBackend):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(WarningToast(shared_constrains.cookies_warning))
        self.table = QTableView()
        self.table.setDisabled(True)
        self.emptyStore = bck.CookieStore()
        self.table.setModel(self.emptyStore)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)

    def emitDataUpdate(self, back: bck.AppBackend, selected: bck.AppRequest):
        if selected is None:
            self.table.setDisabled(True)
            self.table.setModel(self.emptyStore)
        else:
            self.table.setDisabled(False)
            self.table.setModel(selected.cookies)
            self.table.model().beginResetModel()
            self.table.model().endResetModel()


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
        self.tabWidget = QTabWidget(dashboard)
        self.tabWidget.addTab(QPushButton("Тест", self.tabWidget), "Body")
        self.tabWidget.addTab(QPushButton("Тест 2", self.tabWidget), "Headers")
        self.cookies = CookiesViewWidget(back)
        self.tabWidget.addTab(self.cookies, QIcon("assets/bidirectional.png"), "Cookies")
        dashboardLayout.addWidget(self.tabWidget)
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
        selected: bck.AppRequest = back.model.getSelectedRequest()
        if selected is None:
            self.requestName.setText(shared_constrains.no_request_selected)
        else:
            self.requestName.setText(selected.name)
        self.urlSelectorWidget.emitDataUpdate(back, selected)
        self.cookies.emitDataUpdate(back, selected)

    def updateRequestList(self, back: bck.AppBackend):
        self.requestList.clear()
        self.requestList.addItem(LinkedListWidgetItem(shared_constrains.new_http_request))
        for i, req in enumerate(back.model.requests):
            item = LinkedListWidgetItem(req.name)
            item.setIcon(QIcon("assets/http.svg"))
            item.linkedIndex = i
            self.requestList.addItem(item)


class MainWindow(CustomWindow):
    def __init__(self, back: bck.AppBackend):
        super().__init__(back)
        self.setWindowTitle("DenisJava's WebRequests")
        self.widget: MainWidget = MainWidget(back)
        self.setCentralWidget(self.widget)
        self.back = back
        self.back.window = self

        # MenuBar
        filesMenu = self.menuBar().addMenu("Файл")
        filesMenu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), "Открыть...") \
            .triggered.connect(back.openFile)
        filesMenu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), "Сохранить") \
            .triggered.connect(back.saveFile)
        filesMenu.addSeparator()
        filesMenu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserStop), "Выход") \
            .triggered.connect(back.exit)

        requestMenu = self.menuBar().addMenu("Запрос")

        createRequestMenu = requestMenu.addMenu("Новый")
        createRequestMenu.addAction("HTTP/HTTPS Запрос").triggered.connect(
            lambda: back.handleSpecialListItem(shared_constrains.new_http_request))

        requestMenu.addAction(shared_constrains.delete_request).triggered.connect(
            lambda: back.handleSpecialListItem(shared_constrains.delete_request))
        requestMenu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_CommandLink), "Отправить") \
            .triggered.connect(back.sendRequest)

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
        if f"lib_{lib}" in self.back.antiGC:
            return
        w = LibraryWindow(self, self.back, lib)

    def closeEvent(self, event: QCloseEvent):
        self.back.exit()

    def emitDataUpdate(self, back: bck.AppBackend):
        self.widget.emitDataUpdate(back)
