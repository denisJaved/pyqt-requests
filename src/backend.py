from PyQt6.QtWidgets import QApplication

import frontend as _frontend


class AppBackend:
    def __init__(self):
        self.window: _frontend.MainWindow | None = None
        self.application: QApplication | None = None

    def showQtAboutWindow(self):
        self.application.aboutQt()

    def showAboutWindow(self):
        window = _frontend.AboutWindow(self.window, self)
        window.exec()