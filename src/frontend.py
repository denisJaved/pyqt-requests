import base64
import sys
from io import BytesIO

from PyQt6.QtCore import QPoint, Qt, QSize, pyqtSignal
from PyQt6.QtGui import QScreen, QFontDatabase, QCloseEvent, QIcon, QPixmap
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QMainWindow, QLabel, QVBoxLayout, QMessageBox, \
    QListWidget, QLineEdit, QComboBox, QListWidgetItem, QPushButton, QTabWidget, QStyle, QTableView, QHeaderView, \
    QSizePolicy, QFileDialog, QPlainTextEdit, QScrollArea

from PIL import Image

import backend as bck
import shared_constrains as shared_constrains
import utils


class QTitleLabel(QLabel):
    """
    Label with increased font size.
    Implemented in stylesheet.txt
    """
    pass


class IconButton(QPushButton):
    """
    Button that just displays icon without any text.
    """
    def __init__(self, icon: QIcon):
        super().__init__(icon, "")


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


class AssetViewWidget(QWidget):
    # Signals
    dataTypeChanged = pyqtSignal(int, utils.Holder)

    """
    Widget for viewing different types of data.
    Currently, text and images.

    Asset types are:
    0 - None (empty view)
    1 - Text
    2 - Image
    3 - Byte data (read only)
    """
    def __init__(self, allowEditing: bool, jsonHolder: utils.Holder):
        super().__init__()
        self.loadedAssetType = 0
        self.displayAssetType = 0
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Controls
        controls = QWidget()
        controlsLayout = QHBoxLayout()
        controlsTextType = IconButton(QIcon("assets/text.png"))
        controlsTextType.setProperty("targetType", 1)
        controlsTextType.clicked.connect(self.handleDisplayTypeBtn)
        controlsLayout.addWidget(controlsTextType)
        controlsImageType = IconButton(QIcon("assets/image.png"))
        controlsImageType.setProperty("targetType", 2)
        controlsImageType.clicked.connect(self.handleDisplayTypeBtn)
        controlsLayout.addWidget(controlsImageType)
        controlsLayout.addStretch()
        controlsExportFile = IconButton(QIcon("assets/exportFile.png"))
        controlsLayout.addWidget(controlsExportFile)
        if allowEditing:
            controlsUploadFile = IconButton(QIcon("assets/uploadFile.png"))
            controlsUploadFile.clicked.connect(self.importAsset)
            controlsLayout.addWidget(controlsUploadFile)
            controlsCreate = IconButton(QIcon("assets/create.png"))
            controlsCreate.clicked.connect(lambda: self.updateAsset(1, ""))
            controlsLayout.addWidget(controlsCreate)
        controlsErase = IconButton(QIcon("assets/erase.png"))
        controlsErase.clicked.connect(lambda: self.updateAsset(0, ""))
        controlsLayout.addWidget(controlsErase)
        controls.setLayout(controlsLayout)
        controlsLayout.setContentsMargins(5, 8, 5, 0)
        layout.addWidget(controls)

        # Displays
        noneDisplay = QWidget()
        noneDisplay.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        noneDisplayLayout = QHBoxLayout()
        noneDisplayLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        noneDisplayLayout.addWidget(QLabel("No data available"))
        noneDisplay.setLayout(noneDisplayLayout)
        layout.addWidget(noneDisplay)

        textDisplay = QPlainTextEdit(self)
        textDisplay.setObjectName("assetTextDisplay")
        textDisplay.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        textDisplay.setReadOnly(not allowEditing)
        textDisplay.textChanged.connect(self.handleTextDisplayEdit)
        layout.addWidget(textDisplay)

        imageDisplay = QWidget()
        imageDisplay.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        imageDisplayLayout = QHBoxLayout()
        imageDisplayLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        imageDisplayError = QLabel("Data can not be displayed as image")
        imageDisplayLayout.addWidget(imageDisplayError)

        imageScrollWrapper = QWidget()
        imageScrollWrapperLayout = QVBoxLayout()
        imageScrollWrapperLayout.setContentsMargins(0, 0, 0, 0)

        imageDisplayScroll = QScrollArea()
        imageDisplayLabel = QLabel()
        imageDisplayLabel.setObjectName("imageDisplayScroll")
        imageDisplayLabel.setVisible(False)
        imageDisplayScroll.setWidget(imageDisplayLabel)
        imageScrollWrapperLayout.addWidget(imageDisplayScroll)

        imageDisplayMeta = QPlainTextEdit()
        imageDisplayMeta.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        imageDisplayMeta.setReadOnly(True)
        imageDisplayMeta.setMaximumHeight(32)
        imageScrollWrapperLayout.addWidget(imageDisplayMeta)

        imageScrollWrapper.setLayout(imageScrollWrapperLayout)

        imageDisplayLayout.addWidget(imageScrollWrapper)
        imageDisplay.setLayout(imageDisplayLayout)
        layout.addWidget(imageDisplay)

        # Finish
        layout.setContentsMargins(0, 0, 0, 0)

        self.displayTypeButtons = [None, controlsTextType, controlsImageType]
        self.displayContentWidgets = [noneDisplay, textDisplay, imageDisplay]
        self.imageDisplayError = imageDisplayError
        self.imageDisplayLabel = imageDisplayLabel
        self.imageScrollWrapper = imageScrollWrapper
        self.imageDisplaySroll = imageDisplayScroll
        self.imageDisplayMeta = imageDisplayMeta
        self.emptyPixmap = QPixmap()
        self.allowEditing = allowEditing
        self.json = jsonHolder
        self.switchWidget()

    def handleTextDisplayEdit(self):
        if self.loadedAssetType == 1:
            self.json.value["d"] = self.displayContentWidgets[1].toPlainText()

    def handleDisplayTypeBtn(self):
        if self.loadedAssetType == 0:
            self.displayAssetType = 0
        else:
            self.displayAssetType = self.sender().property("targetType")
        self.switchWidget()

    def switchWidget(self):
        for i, x in enumerate(self.displayContentWidgets):
            if x is None:
                continue
            x.setVisible(i == self.displayAssetType)

    def importAsset(self):
        fileName = QFileDialog.getOpenFileName(
            self, 'Выбрать файл', '',
            'Все файлы (*);;JPG Изображение (*.jpg);;PNG Изображение (*.png);;Текстовый файл (*.txt)')[0]
        extension = fileName.split(".")[-1]
        try:
            if extension in ["jpg", "png", "jpeg", "webp", "tiff"]:
                with open(fileName, "rb") as fr:
                    self.updateAsset(2, fr.read())
            else:
                with open(fileName, "r", encoding="utf-8") as fr:
                    self.updateAsset(1, fr.read())
        except Exception:
            QMessageBox.warning(self.window(), "Внимание", "Не удалось прочитать файл!")

    def updateAsset(self, assetType: int, data, json=False):
        self.loadedAssetType = assetType
        self.displayAssetType = assetType
        self.displayContentWidgets[1].setPlainText("Data can not be displayed as text")
        self.displayContentWidgets[1].setDisabled(True)
        self.displayContentWidgets[1].setReadOnly(not self.allowEditing)
        self.imageScrollWrapper.setVisible(False)
        self.imageDisplayLabel.setPixmap(self.emptyPixmap)
        self.imageDisplayError.setVisible(True)
        self.json.value = {"t": assetType, "d": None}
        if assetType == 1:
            self.displayContentWidgets[1].setPlainText(data)
            self.displayContentWidgets[1].setDisabled(False)
            self.json.value["d"] = data
        elif assetType == 2:
            # Decode bytes if input is JSON
            imageBytes = base64.decodebytes(data.encode(encoding="utf-8")) if json else data

            imageFormat = "UNKNOWN-IMAGE-FORMAT"
            size = (-1, -1)
            with Image.open(BytesIO(imageBytes)) as pilImage:
                imageFormat = pilImage.format
                size = (pilImage.width, pilImage.height)


            # Display the image
            pixmap = QPixmap()
            pixmap.loadFromData(imageBytes)
            if pixmap.height() < 100 or pixmap.width() < 100:
                pixmap = pixmap.scaled(QSize(max(pixmap.width() * 2, 100), max(pixmap.height() * 2, 100)),
                                       Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                       Qt.TransformationMode.SmoothTransformation)
            self.imageDisplayLabel.setPixmap(pixmap)
            self.imageDisplayLabel.resize(self.imageDisplayLabel.sizeHint())
            self.imageScrollWrapper.setVisible(True)
            self.imageDisplayError.setVisible(False)

            # Write image to JSON
            self.json.value["d"] = data if json else base64.encodebytes(data).decode(encoding="utf-8")
            self.json.value["f"] = imageFormat

            # Show hex representation of image
            self.displayContentWidgets[1].setReadOnly(True)
            self.displayContentWidgets[1].setDisabled(False)
            bytes_hex = imageBytes.hex(sep=" ", bytes_per_sep=-4).split(" ")
            bytes_hex = map(lambda x: " ".join(x).upper(), [bytes_hex[i : i + 6] for i in range(0, len(bytes_hex), 6)])
            self.displayContentWidgets[1].setPlainText(f"{imageFormat} image hex representation.\n" + "\n".join(bytes_hex))
            self.imageDisplayMeta.setPlainText(f"{imageFormat} {size[0]}x{size[1]}px image. {len(imageBytes)} bytes")
            self.imageDisplayMeta.resize(self.imageDisplayMeta.sizeHint())
        elif assetType == 3:
            imageBytes = base64.decodebytes(data.encode(encoding="utf-8")) if json else data
            self.json.value["d"] = data if json else base64.encodebytes(data).decode(encoding="utf-8")
            self.displayContentWidgets[1].setReadOnly(True)
            self.displayContentWidgets[1].setDisabled(False)
            bytes_hex = imageBytes.hex(sep=" ", bytes_per_sep=-4).split(" ")
            bytes_hex = map(lambda x: " ".join(x).upper(), [bytes_hex[i: i + 6] for i in range(0, len(bytes_hex), 6)])
            self.displayContentWidgets[1].setPlainText("\n".join(bytes_hex))
        self.switchWidget()
        self.dataTypeChanged.emit(assetType, self.json)

    def importJson(self, json: dict):
        self.json.value = json
        self.updateAsset(json["t"], json["d"], True)

    def importJsonHolder(self, json: utils.Holder):
        self.json = json
        self.updateAsset(json.value["t"], json.value["d"], True)

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
        self.requestName.setText(shared_constrains.no_request_selected)
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
            self.requestName.setText(shared_constrains.no_request_selected)
        else:
            self.requestName.setText(selected.name)
        self.urlSelectorWidget.emitDataUpdate(back, selected)
        self.cookies.emitDataUpdate(back, selected)
        self.bodyView.emitDataUpdate(back, selected)
        self.sidedHeadersViewWidget.emitDataUpdate(back, selected)

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
