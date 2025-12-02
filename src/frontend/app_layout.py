import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QCloseEvent
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QComboBox, QLineEdit, QPushButton, QTableView, \
    QHeaderView, QTabWidget, QListWidget, QStyle, QLabel

from src import backend as bck, shared_constrains as shared_constrains, utils
from src.frontend.app_about import AboutWindow, InfoWindow
from src.frontend.app_components import CustomWindow, WarningToast, IconButton, AssetViewWidget, \
    LinkedListWidgetItem

# Window UI Layout:
#
# ┌──[ DenisJava's WebRequests ]───────────────[-]─[□]─[⨯]─┐
# │░File░Request░...░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ <-- QMenuBar (defined in MainWindow)
# │┌───────┐                                               │
# ││+ HTTP │   Request name <---------------------------------- QLineEdit (defined in MainWidget)
# ││...    │   [ GET ↓][https://example.com________][send]  <-- UrlSelectorWidget
# ││...    │   [Body][Headers][Cookie]                     │
# ││       │   ┌─────────────────────────────────────────┐ │
# ││       │   │                                         │  <-- QTabWidget (defined in MainWidget)
# ││       │   │                                         │ │    (Read more about tabs below)
# ││       │   │                                         │ │
# ││       │   │                                         │ │
# ││       │   │                                         │ │
# │└───────┘   └─────────────────────────────────────────┘ │
# └─ ^ ────────────────────────────────────────────────────┘
#    └ QListWidget (defined in MainWidget)
#
# Tabs in QTabWidget:
#     [Body]    : Contains two own tabs inside for request and response data.
#                 Each tab is filled with AssetViewWidget (app_components.py)
#
#     [Headers] : Contains two own tabs inside for request and response data.
#                 Each tab is filled with HeadersViewWidget
#
#     [Cookies] : Filled with CookiesViewWidget
#
# NOTICE: About windows defined in src.app_about

class UrlSelectorWidget(QWidget):
    """
    UrlSelectorWidget manages HTTP method selector, url's QLineEdit and submit button
    """
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
    """
    Displays cookies. This is widget is not request-response sided.
    """
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


class BodyViewWidget(QTabWidget):
    """
    Handles request and response side of HTTP body displays.
    AssetViewWidget is used to display contents of HTTP bodies.
    """
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


class HeadersViewWidget(QWidget):
    """
    Table for viewing and editing HTTP headers
    """
    def __init__(self, back: bck.AppBackend, isRequestSide: bool):
        super().__init__()
        self.isRequestSide = isRequestSide
        layout = QVBoxLayout()

        controls = QWidget()
        controlsLayout = QHBoxLayout()
        controlsLayout.addStretch()
        if isRequestSide:
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


class SidedHeadersViewWidget(QTabWidget):
    """
    Handles request and response side of HeadersViewWidget
    """
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
    """
    Main widget of MainWindow.
    Check line 13 for more information.
    """
    def __init__(self, back: bck.AppBackend):
        super().__init__()

        self.back = back
        dashboard = QWidget()
        dashboardLayout = QVBoxLayout(dashboard)

        requestNameWrapper = QWidget()
        requestNameWrapperLayout = QHBoxLayout()
        requestNameWrapper.setLayout(requestNameWrapperLayout)

        self.requestName = QLineEdit(self)
        self.requestName.setText(shared_constrains.NO_REQUEST_SELECTED)
        self.requestName.setObjectName("requestName")
        self.requestName.textEdited.connect(self.requestNameChanged)
        requestNameWrapperLayout.addWidget(self.requestName)

        self.statusCode = QLabel()
        self.statusCode.setObjectName("statusCode")
        requestNameWrapperLayout.addWidget(self.statusCode)

        dashboardLayout.addWidget(requestNameWrapper)
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
            self.statusCode.setText("XXX")
        else:
            self.requestName.setText(selected.name)
            self.statusCode.setText(selected.statusCode)
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
    """
    Windows that shows all the requests
    """
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
        libsMenu.addAction("pillow").triggered.connect(lambda: self.libraryAbout("pillow"))

        helpMenu.addAction("Список статус кодов").triggered.connect(lambda: self.libraryAbout("statusCodes"))

        self.statusBar().showMessage("")

        if "-dev" in sys.argv:
            self.statusBar().showMessage("DenisJava's WebRequests запущен в режиме разработчика")
            back.openFile0("test.djwr")

    def libraryAbout(self, lib: str):
        if f"lib_{lib}" in self.back.antiGC:
            return
        InfoWindow(self, self.back, lib)

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
