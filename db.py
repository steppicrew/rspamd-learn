import sqlite3


class DB:
    def __init__(self, db_file: str):
        self.connection = sqlite3.connect(db_file)
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS done (value TEXT NOT NULL UNIQUE)")
        cursor.close()
        self.connection.commit()

    def add(self, value: str):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO done (value) VALUES (?)", (value,))
        cursor.close()
        self.connection.commit()

    def has(self, value: str):
        cursor = self.connection.cursor()
        cursor.execute("SELECT value FROM done WHERE value = ?", (value,))
        result = cursor.fetchone()
        cursor.close()
        return result
