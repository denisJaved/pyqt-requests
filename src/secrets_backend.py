import pathlib
import sqlite3

class SecretsStorage:
    def __init__(self):
        self.databaseConnection = sqlite3.connect("secrets.db")

    def executeFile(self, name, args=()) -> sqlite3.Cursor:
        expression = pathlib.Path(f"src/sql/{name}.sql").read_text()
        return self.databaseConnection.execute(expression, args)

    def buildTables(self):
        self.executeFile("secrets_table")