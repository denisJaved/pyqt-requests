from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QWidget, QScrollArea

from src import backend as bck, shared_constrains as shared_constrains
from src.frontend.app_components import CustomWindow, QTitleLabel


class AboutWindow(CustomWindow):
    """
    Window for displaying information about the application
    """
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


class InfoWindow(CustomWindow):
    """
    Window for displaying information about libraries used in the application or documentation.
    Text displayed should be stored in ./about/ directory relative to the projects root.
    """
    def __init__(self, window: CustomWindow, back: bck.AppBackend, lib: str):
        super().__init__(back)
        self.setWindowTitle(f"About {lib}")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QTitleLabel(lib))
        with open(f"about/{lib}.txt", "r", encoding="utf-8") as fr:
            label = QLabel(fr.read())
            scroll = QScrollArea()
            scroll.setWidget(label)
            layout.addWidget(scroll)
        self.windowId = f"lib_{lib}"
        self.back = back
        self.back.antiGC[self.windowId] = self
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.resize(self.sizeHint())
        self.centerOnScreen()
        self.show()

    def closeEvent(self, a0):
        del self.back.antiGC[self.windowId]
        super().closeEvent(a0)
