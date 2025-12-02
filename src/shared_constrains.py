ABOUT = """
DenisJava's WebRequests - приложение с графическим интерфейсом
для тестирования/экспериментирования с HTTP(и HTTPS) запросами.

Автор: Веретенников Денис Андреевич
"""
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD", "TRACE", "PATCH", "OPTIONS"]
NEW_HTTP_REQUEST = " + Новый HTTP/HTTPS запрос"
DELETE_REQUEST = "Удалить выбранный запрос"
NO_REQUEST_SELECTED = "< Выберете запрос чтобы начать"
COOKIES_WARNING = ("Файлы cookie часто используют для аутентификации и прочих мер безопасности!\nБудьте осторожны с "
                   "этим разделом. Только файлы cookie со значением secure=false сохранены в файл запроса!")
STYLESHEET: str | None = None