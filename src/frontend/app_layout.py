import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QCloseEvent
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QWidget, QHBoxLayout, QComboBox, QLineEdit, QPushButton, QTableView, \
    QHeaderView, QTabWidget, QListWidget, QStyle

from src import backend as bck, shared_constrains as shared_constrains, utils
from src.frontend.app_components import CustomWindow, QTitleLabel, WarningToast, IconButton, AssetViewWidget, \
    LinkedListWidgetItem


class AboutWindow(CustomWindow):
    def __init__(self, window: CustomWindow, back: bck.AppBackend):
        super().__init__(back)
        self.setWindowTitle("About DenisJava's WebRequests")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QTitleLabel("DenisJava's WebRequests"))
        layout.addWidget(QLabel(shared_constrains.ABOUT))
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
        self.methodSelector.addItems(shared_constrains.HTTP_METHODS)
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
        self.methodSelector.setCurrentIndex(shared_constrains.HTTP_METHODS.index(selected.method))
        self.methodSelector.setDisabled(False)
        self.lineEdit.setText(selected.url)
        self.lineEdit.setDisabled(False)


class CookiesViewWidget(QWidget):
    def __init__(self, back: bck.AppBackend):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(WarningToast(shared_constrains.COOKIES_WARNING))
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


class HeadersViewWidget(QWidget):
    def __init__(self, back: bck.AppBackend, isRequestSide: bool):
        super().__init__()
        self.isRequestSide = isRequestSide
        layout = QVBoxLayout()

        controls = QWidget()
        controlsLayout = QHBoxLayout()
        controlsLayout.addStretch()
        controlsCreate = IconButton(QIcon("assets/create.png"))
        controlsCreate.clicked.connect(self.createHandler)
        controlsLayout.addWidget(controlsCreate)
        controls.setLayout(controlsLayout)
        controlsLayout.setContentsMargins(5, 8, 5, 0)
        layout.addWidget(controls)

        self.table = QTableView()
        self.table.setDisabled(True)
        self.emptyStore = bck.HeaderStore(False)
        self.table.setModel(self.emptyStore)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.model: bck.HeaderStore = self.emptyStore

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)

    def createHandler(self):
        self.model["..."] = "..."

    def emitDataUpdate(self, back: bck.AppBackend, selected: bck.AppRequest):
        if selected is None:
            self.table.setDisabled(True)
            self.table.setModel(self.emptyStore)
        else:
            self.table.setDisabled(False)
            self.model = selected.requestHeaders if self.isRequestSide else selected.responseHeaders
            self.table.setModel(self.model)
            self.table.model().changeListener = self.changeListener
            self.table.model().beginResetModel()
            self.table.model().endResetModel()

    def changeListener(self, model: bck.HeaderStore):
        if model is self.table.model():
            self.table.model().beginResetModel()
            self.table.model().endResetModel()
        else:
            model.changeListener = lambda x: None


class BodyViewWidget(QTabWidget):
    def __init__(self, back: bck.AppBackend):
        super().__init__()
        self.back = back
        self.requestView = AssetViewWidget(True, utils.Holder({}))
        self.requestView.dataTypeChanged.connect(lambda x, y: self.back.model.getSelectedRequest()
                                                 .setContentTypeHeader(x, y))
        self.addTab(self.requestView, QIcon("assets/request.png"), "Request")
        self.responseView = AssetViewWidget(False, utils.Holder({}))
        self.addTab(self.responseView, QIcon("assets/response.png"), "Response")

    def emitDataUpdate(self, back: bck.AppBackend, selected: bck.AppRequest):
        if selected is not None:
            self.requestView.importJsonHolder(selected.requestBody)
            self.responseView.importJsonHolder(selected.responseBody)
        else:
            self.requestView.updateAsset(0, "")
            self.responseView.updateAsset(0, "")


class SidedHeadersViewWidget(QTabWidget):
    def __init__(self, back: bck.AppBackend):
        super().__init__()
        self.back = back
        self.requestView = HeadersViewWidget(back, True)
        self.addTab(self.requestView, QIcon("assets/request.png"), "Request")
        self.responseView = HeadersViewWidget(back, False)
        self.addTab(self.responseView, QIcon("assets/response.png"), "Response")

    def emitDataUpdate(self, back: bck.AppBackend, selected: bck.AppRequest):
        self.requestView.emitDataUpdate(back, selected)
        self.responseView.emitDataUpdate(back, selected)


class MainWidget(QWidget):
    def __init__(self, back: bck.AppBackend):
        super().__init__()

        self.back = back
        dashboard = QWidget()
        dashboardLayout = QVBoxLayout(dashboard)
        self.requestName = QLineEdit(self)
        self.requestName.setText(shared_constrains.NO_REQUEST_SELECTED)
        self.requestName.setObjectName("requestName")
        self.requestName.textEdited.connect(self.requestNameChanged)
        dashboardLayout.addWidget(self.requestName)
        self.urlSelectorWidget: UrlSelectorWidget = UrlSelectorWidget(back)
        dashboardLayout.addWidget(self.urlSelectorWidget)
        self.tabWidget = QTabWidget(dashboard)
        self.bodyView = BodyViewWidget(back)
        self.tabWidget.addTab(self.bodyView, "Body")
        self.sidedHeadersViewWidget = SidedHeadersViewWidget(back)
        self.tabWidget.addTab(self.sidedHeadersViewWidget, "Headers")
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
            self.requestName.setText(shared_constrains.NO_REQUEST_SELECTED)
        else:
            self.requestName.setText(selected.name)
        self.urlSelectorWidget.emitDataUpdate(back, selected)
        self.cookies.emitDataUpdate(back, selected)
        self.bodyView.emitDataUpdate(back, selected)
        self.sidedHeadersViewWidget.emitDataUpdate(back, selected)

    def updateRequestList(self, back: bck.AppBackend):
        self.requestList.clear()
        self.requestList.addItem(LinkedListWidgetItem(shared_constrains.NEW_HTTP_REQUEST))
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
            lambda: back.handleSpecialListItem(shared_constrains.NEW_HTTP_REQUEST))

        requestMenu.addAction(shared_constrains.DELETE_REQUEST).triggered.connect(
            lambda: back.handleSpecialListItem(shared_constrains.DELETE_REQUEST))
        requestMenu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_CommandLink), "Отправить") \
            .triggered.connect(back.sendRequest)

        secretsMenu = self.menuBar().addMenu("Секреты")

        testsMenu = self.menuBar().addMenu("Тестирование")

        helpMenu = self.menuBar().addMenu("Помощь")
        helpMenu.addAction("О программе").triggered.connect(self.showAboutWindow)

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

    def showAboutWindow(self):
        if "about" in self.back.antiGC:
            return
        window = AboutWindow(self, self.back)
        self.back.antiGC["about"] = window
        window.show()

    def closeEvent(self, event: QCloseEvent):
        self.back.exit()

    def emitDataUpdate(self, back: bck.AppBackend):
        self.widget.emitDataUpdate(back)
