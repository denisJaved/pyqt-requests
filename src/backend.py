import http.cookiejar
import json
import threading
from typing import Any

import requests
import requests.cookies
from PyQt6.QtCore import QAbstractTableModel, Qt, QVariant
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QListWidgetItem

import frontend as _frontend
import shared_constrains as shared_constraints


def noneIfStrNull(s: str) -> str | None:
    return None if s is None or s.strip() == "" else s


class CookieStore(QAbstractTableModel):
    def __init__(self, store=None):
        super().__init__()

        # key -> list(value, secure, version, domain, path, port, comment, expires, discard)
        self.store: dict[str, list] = {} if store is None else store
        # list[self.store key]
        self.sorting: list[str] = []
        self.headers = ["Name", "Value", "Is Secure", "Version", "Domain", "Path", "Port", "Comment", "Expires", "Discard"]

    @staticmethod
    def fromJSON(data: dict, model):
        return CookieStore(data)

    def toJSON(self) -> dict:
        return self.store

    def toJar(self):
        cookieJar: requests.cookies.RequestsCookieJar = requests.cookies.RequestsCookieJar()
        for name in self.store:
            value, secure, version, domain, path, port, comment, expires, discard = self.store[name]
            domain = noneIfStrNull(domain)
            path = noneIfStrNull(path)
            port = noneIfStrNull(port)
            cookieJar.set_cookie(http.cookiejar.Cookie(
                version = version,
                name = name,
                value = value,
                port = port,
                port_specified = port is not None,
                domain = domain,
                domain_specified = domain is not None,
                domain_initial_dot = False,
                path = path,
                path_specified = path is not None,
                secure = secure,
                expires = expires,
                discard = discard,
                comment = comment,
                comment_url = None,
                rest = {}
            ))

    def addCookie(self, name: str, value: str, secure: bool, version: int, domain: str, path: str, port: str, comment: str,
                  expires: int):
        if name not in self.store:
            self.sorting.append(name)
        self.store[name] = [value, secure, -1 if version is None else version,
                            domain, path, port, "<no comment>" if comment is None else comment, expires, False]

    def clear(self):
        self.store.clear()
        self.sorting.clear()

    def rowCount(self, parent = None):
        return len(self.store)

    def columnCount(self, parent = None):
        return 10 # see type hint for self.store in __init__

    def data(self, index, role = Qt.ItemDataRole.DisplayRole):
        if index.isValid() and (role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole)):
            try:
                key = self.sorting[index.row()]
                return key if index.column() == 0 else self.store[key][index.column() - 1]
            except KeyError:
                return "<INVALID KEY>" # Required because Qt6 sometimes calls QAbstractTableModel.data with deleted keys
        return QVariant()

    def setData(self, index, value, role = Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole and index.isValid():
            if index.column() == 0:
                self.store[value] = self.store.pop(self.sorting[index.row()])
                self.sorting[index.row()] = value
            else:
                self.store[self.sorting[index.row()]][index.column() - 1] = value
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def headerData(self, section, orientation, role = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return QVariant()
        if orientation == Qt.Orientation.Horizontal and 0 <= section < self.columnCount():
            return self.headers[section]
        return section + 1

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        return (Qt.ItemFlag.ItemIsSelectable |
                Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsEditable)


class AppRequest:
    def __init__(self, model, name: str):
        self.name = name
        self.method = "GET"
        self.url = "http://localhost/"
        self.model = model
        self.cookies = CookieStore()

    @staticmethod
    def fromJSON(data: dict, model):
        req = AppRequest(model, data["n"])
        req.method = data["m"]
        req.url = data["url"]
        req.cookies = CookieStore.fromJSON(data.get("c", {}), model)
        return req

    def toJSON(self) -> dict:
        return {
            "n": self.name,
            "p": "HTTP(S)", # "p" key is reserved for future use to specify protocol of this AppRequest
            "m": self.method,
            "url": self.url,
            "c": self.cookies.toJSON()
        }

    def execute(self):
        window: _frontend.MainWindow = self.model.back.window
        window.statusBar().showMessage("Отправка запроса...")
        # noinspection PyBroadException
        try:
            resp: requests.Response = requests.request(method=self.method, url=self.url, cookies=self.cookies.toJar())
            window.statusBar().showMessage(f"Ответ на запрос получен за {round(resp.elapsed.total_seconds(), 3)} секунд")
            self.cookies.clear()
            for cookie in resp.cookies:
                self.cookies.addCookie(cookie.name, cookie.value, cookie.secure, cookie.version,
                                       cookie.domain, cookie.path, cookie.port,
                                       cookie.comment, cookie.expires)
            self.model.back.emitDataUpdate()
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
        self.antiGC: dict[str, Any] = {}

    def showQtAboutWindow(self):
        self.application.aboutQt()

    def showAboutWindow(self):
        if "about" in self.antiGC:
            return
        window = _frontend.AboutWindow(self.window, self)
        self.antiGC["about"] = window
        window.show()

    def openFile(self):
        file = QFileDialog.getOpenFileName(
            self.window, "Выбрать файл", "",
            "DenisJava's WebRequests (*.djwr)")[0]
        self.openFile0(file)

    def openFile0(self, file: str):
        try:
            self.model = AppDataModel.readFile(file, self)
        except KeyError:
            QMessageBox.warning(self.window, "Внимание", "Файл не совместим с этой версией DenisJava's WebRequests")
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
            self.handleSpecialListItem(item.text())
        else:
            if item.linkedIndex < len(self.model.requests):
                self.model.selectedRequest = item.linkedIndex
            self.emitDataUpdate()

    def handleSpecialListItem(self, itemText: str):
        if itemText == shared_constraints.new_http_request:
            self.model.selectedRequest = len(self.model.requests)
            req: AppRequest = AppRequest(self.model, "Новый запрос")
            self.model.requests.append(req)
        elif itemText == shared_constraints.delete_request:
            self.model.requests.pop(self.model.selectedRequest)
            self.model.selectedRequest = max(0, self.model.selectedRequest - 1)
        self.emitDataUpdate()

    def updateCurrentRequest(self, prop: str, value):
        selected = self.model.getSelectedRequest()
        if selected is not None:
            setattr(selected, prop, value)

    def sendRequest(self):
        selected = self.model.getSelectedRequest()
        if selected is not None:
            threading.Thread(target=selected.execute).start()