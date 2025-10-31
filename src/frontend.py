from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QScreen, QFontDatabase, QCloseEvent
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMainWindow, QDialog, QLabel, QVBoxLayout, QMessageBox, \
    QListWidget, QLineEdit, QComboBox

import backend as bck

about = """
DenisJava's WebRequests - приложение с графическим интерфейсом
для тестирования/экспериментирования с HTTP(и HTTPS) запросами.

Автор: Веретенников Денис Андреевич
"""

class QTitleLabel(QLabel):
    pass


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
            style = style.replace("!!nerdFontMono!!", families[0])
        else:
            QMessageBox.warning(self, "Внимание", "Не удалось активировать шрифт. Убедитесь, что по пути "
                                                  "src/NerdFonoMono-Light.ttf расположен рабочий шрифт"
                                                  "\nРабота будет продолжена с системным шрифтом")
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
        layout.addWidget(QLabel(about))
        self.show()


class UrlSelectorWidget(QWidget):
    def __init__(self, back: bck.AppBackend):
        super().__init__()
        layout = QHBoxLayout(self)
        self.methodSelector = QComboBox(self)
        self.methodSelector.addItem("GET")
        self.methodSelector.addItem("POST")
        self.methodSelector.addItem("PUT")
        self.methodSelector.addItem("DELETE")
        self.methodSelector.addItem("HEAD")
        self.methodSelector.addItem("TRACE")
        self.methodSelector.addItem("PATCH")
        self.methodSelector.addItem("OPTIONS")
        layout.addWidget(self.methodSelector)
        self.lineEdit = QLineEdit(self)
        layout.addWidget(self.lineEdit)
        layout.setSpacing(0)
        self.setLayout(layout)


class MainWidget(QWidget):
    def __init__(self, back: bck.AppBackend):
        super().__init__()

        dashboard = QWidget()
        dashboardLayout = QVBoxLayout(dashboard)
        dashboardLayout.addWidget(UrlSelectorWidget(back))
        dashboardLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        dashboard.setLayout(dashboardLayout)

        layout = QHBoxLayout(self)
        self.requestList: QListWidget = QListWidget()
        layout.addWidget(self.requestList)
        layout.addWidget(dashboard)
        layout.setStretchFactor(dashboard, 1)
        self.setLayout(layout)


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

    def closeEvent(self, event: QCloseEvent):
        self.backend.exit()
