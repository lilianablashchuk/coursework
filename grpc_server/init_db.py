import sqlite3
import os
from server_data import lots as initial_lots

DB_FILE = "auction_grpc.db"

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

def init_lots():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("Ініціалізація таблиці lots")
    
    cursor.execute("""
        CREATE TABLE lots (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            creator TEXT,
            createdAt TEXT,
            startingPrice REAL NOT NULL,
            startTime TEXT, 
            durationMinutes INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lotId INTEGER,
            user TEXT,
            amount REAL,
            createdAt TEXT DEFAULT '',
            FOREIGN KEY (lotId) REFERENCES lots(id) ON DELETE CASCADE
        )
    """)

    sql_insert = """
    INSERT INTO lots (id, title, description, creator, createdAt, startingPrice, startTime, durationMinutes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    for lot in initial_lots:
        cursor.execute(sql_insert, (
            lot['id'], lot['title'], lot['description'], lot['creator'],
            lot['createdAt'], lot['startingPrice'], lot['startTime'], lot['durationMinutes']
        ))

    conn.commit()
    conn.close()
    print(f"Успішно додано {len(initial_lots)} лотів.")

if __name__ == "__main__":
    init_lots()
