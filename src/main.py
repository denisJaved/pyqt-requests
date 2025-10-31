import sys
import frontend
import backend
from PyQt6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_backend = backend.AppBackend()
    ex = frontend.MainWindow(app_backend)
    app_backend.application = app
    ex.show()
    sys.exit(app.exec())