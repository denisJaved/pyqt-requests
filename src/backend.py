from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QListWidgetItem

import frontend as _frontend
import shared_constrains as shared_constraints
import json
import requests
import threading

class AppRequest:
    def __init__(self, model, name: str):
        self.name = name
        self.method = "GET"
        self.url = "http://localhost/"
        self.model = model

    @staticmethod
    def fromJSON(data: dict, model):
        req = AppRequest(model, data["n"])
        req.method = data["m"]
        req.url = data["url"]
        return req

    def toJSON(self) -> dict:
        return {
            "n": self.name,
            "p": "HTTP(S)", # "p" key is reserved for future use to specify protocol of this AppRequest
            "m": self.method,
            "url": self.url,
        }

    def execute(self):
        window: _frontend.MainWindow = self.model.back.window
        window.statusBar().showMessage("Отправка запроса...")
        # noinspection PyBroadException
        try:
            resp: requests.Response = requests.request(method=self.method, url=self.url)
            window.statusBar().showMessage(f"Ответ на запрос получен за {round(resp.elapsed.total_seconds(), 3)} секунд")
        except requests.exceptions.ConnectionError:
            window.statusBar().showMessage("Запрос не успешен! Не удалось установить соединение с сервером.")
        except Exception as e:
            window.statusBar().showMessage("Во время запроса произошла неизвестная ошибка!")
            raise e


class AppDataModel:
    def __init__(self, back):
        self.requests: list[AppRequest] = []
        self.selectedRequest: int = -1 # index of selected request. Or -1 if no request is selected
        self.back = back

    @staticmethod
    def readFile(file: str, back):
        model = AppDataModel(back)
        with open(file, "r", encoding="utf-8") as fr:
            data = json.load(fr)
        for request in data.get("r", []):
            model.requests.append(AppRequest.fromJSON(request, model))
        model.selectedRequest = int(data.get("s", -1))
        return model

    def getSelectedRequest(self) -> AppRequest | None:
        if self.selectedRequest == -1:
            return None
        return self.requests[self.selectedRequest]

    def savefile(self, file: str):
        root = {
            "r": [],
            "s": self.selectedRequest
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
        self.model = AppDataModel(self)

    def showQtAboutWindow(self):
        self.application.aboutQt()

    def showAboutWindow(self):
        window = _frontend.AboutWindow(self.window, self)
        window.exec()

    def openFile(self):
        file = QFileDialog.getOpenFileName(
            self.window, "Выбрать файл", "",
            "DenisJava's WebRequests (*.djwr)")[0]
        self.openFile0(file)

    def openFile0(self, file: str):
        try:
            self.model = AppDataModel.readFile(file, self)
        except IOError:
            QMessageBox.warning(self.window, "Внимание", "Не удалось прочитать файл!")
        self.emitDataUpdate()

    def saveFile(self):
        file = QFileDialog.getOpenFileName(
            self.window, "Выбрать файл", "",
            "DenisJava's WebRequests (*.djwr)")[0]
        try:
            self.model.savefile(file)
            QMessageBox.information(self.window, "Операция успешна", "Файл успешно записан.")
        except IOError:
            QMessageBox.warning(self.window, "Внимание", "Не удалось записать файл!")
        self.emitDataUpdate()

    def exit(self):
        """
        Exits the application
        """
        # TODO: Show Unsaved Changes confirmation
        quit(0)

    def emitDataUpdate(self) -> None:
        """
        Updates frontend widgets according to backend data
        """
        self.window.emitDataUpdate(self)

    def selectRequest(self, items: list[QListWidgetItem]):
        if len(items) == 0:
            return
        # noinspection PyTypeChecker
        item: _frontend.LinkedListWidgetItem = items[0]
        if item.linkedIndex == -1:
            # linkedIndex is -1, so this item is not linked to AppRequest
            if item.text() == shared_constraints.new_http_request:
                self.model.selectedRequest = len(self.model.requests)
                req: AppRequest = AppRequest(self.model, "Новый запрос")
                self.model.requests.append(req)
        else:
            if item.linkedIndex < len(self.model.requests):
                self.model.selectedRequest = item.linkedIndex
        self.emitDataUpdate()

    def updateCurrentRequest(self, prop: str, value):
        selected = self.model.getSelectedRequest()
        if selected is not None:
            setattr(selected, prop, value)

    def sendRequest(self):
        selected = self.model.getSelectedRequest()
        if selected is not None:
            threading.Thread(target=selected.execute).start()