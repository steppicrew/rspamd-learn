import sqlite3


class DB:
    def __init__(self, db_file: str):
        self.connection = sqlite3.connect(db_file)
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS done (value TEXT NOT NULL UNIQUE, status CHAR(1))")
        cursor.close()
        self.connection.commit()

    def add(self, value: str, status: str):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO done (value, status) VALUES (?, ?)",
            (value, status)
        )
        cursor.close()
        self.connection.commit()

    def get(self, value: str):
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT status FROM done WHERE value = ?",
            (value,)
        )
        result = cursor.fetchone()
        cursor.close()
        return None if result is None else str(result[0])
