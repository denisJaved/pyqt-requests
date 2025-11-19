import base64
from io import BytesIO

from PIL import Image
from PyQt6.QtCore import QPoint, Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QScreen, QFontDatabase, QGuiApplication, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QListWidgetItem, QMainWindow, QMessageBox, QWidget, QVBoxLayout, \
    QHBoxLayout, QSizePolicy, QPlainTextEdit, QScrollArea, QFileDialog

import src.backend as bck
import src.shared_constrains as shared_constrains
import src.utils as utils


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
    """
    Base class for project's windows
    """

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
        if shared_constrains.STYLESHEET is not None:
            self.setStyleSheet(shared_constrains.STYLESHEET)
            return
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
        QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
        shared_constrains.STYLESHEET = style
        self.setStyleSheet(shared_constrains.STYLESHEET)


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
