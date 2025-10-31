from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
import frontend as _frontend
import json

class AppRequest:
    def __init__(self):
        pass

    @staticmethod
    def fromJSON(data: dict):
        req = AppRequest()
        return req

    def toJSON(self) -> dict:
        return {}


class AppDataModel:
    def __init__(self):
        self.requests: list[AppRequest] = []

    @staticmethod
    def readFile(file: str):
        model = AppDataModel()
        with open(file, "r", encoding="utf-8") as fr:
            data = json.load(fr)
        for request in data.get("r", []):
            model.requests.append(AppRequest.fromJSON(request))
        return model

    def savefile(self, file: str):
        root = {
            "r": []
        }
        for request in self.requests:
            root["r"].append(request.toJSON())
        with open(file, "w", encoding="utf-8") as fw:
            fw.write(json.dumps(root, indent=4))

# noinspection PyMethodMayBeStatic
class AppBackend:
    def __init__(self):
        self.window: _frontend.MainWindow | None = None
        self.application: QApplication | None = None
        self.newChanges = False
        self.model = AppDataModel()

    def showQtAboutWindow(self):
        self.application.aboutQt()

    def showAboutWindow(self):
        window = _frontend.AboutWindow(self.window, self)
        window.exec()

    def openFile(self):
        file = QFileDialog.getOpenFileName(
            self.window, "Выбрать файл", "",
            "DenisJava's WebRequests (*.djwr)")[0]
        try:
            self.model = AppDataModel.readFile(file)
        except IOError:
            QMessageBox.warning(self.window, "Внимание", "Не удалось прочитать файл!")
        self.updateWidgets()

    def saveFile(self):
        file = QFileDialog.getOpenFileName(
            self.window, "Выбрать файл", "",
            "DenisJava's WebRequests (*.djwr)")[0]
        try:
            self.model.savefile(file)
            QMessageBox.information(self.window, "Операция успешна", "Файл успешно записан.")
        except IOError:
            QMessageBox.warning(self.window, "Внимание", "Не удалось записать файл!")
        self.updateWidgets()

    def exit(self):
        # TODO: Show confirmation dialog if newChanges == True
        quit(0)

    def updateWidgets(self):
        pass