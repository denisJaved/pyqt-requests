import sys

from PyQt6.QtWidgets import QApplication

import src.backend as backend
import src.frontend.app_layout

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_backend = backend.AppBackend()
    ex = src.frontend.app_layout.MainWindow(app_backend)
    app_backend.application = app
    app_backend.emitDataUpdate()
    ex.show()
    sys.exit(app.exec())