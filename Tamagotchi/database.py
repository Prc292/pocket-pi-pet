import sqlite3
import time

class DatabaseManager:
    """Handles SQL persistence to keep the pet 'alive' on disk."""
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        """Creates the 12-column schema."""
        query = """
        CREATE TABLE IF NOT EXISTS pet_stats (
            id INTEGER PRIMARY KEY,
            fullness REAL, happiness REAL, energy REAL, health REAL,
            discipline REAL, care_mistakes INTEGER,
            is_alive INTEGER, birth_time REAL, last_update REAL,
            life_stage TEXT, state TEXT
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def save_pet(self, pet_data):
        query = """
        INSERT OR REPLACE INTO pet_stats 
        (id, fullness, happiness, energy, health, discipline, care_mistakes, 
         is_alive, birth_time, last_update, life_stage, state)
        VALUES (1,?,?,?,?,?,?,?,?,?,?,?)
        """
        self.conn.execute(query, (
            pet_data['fullness'], pet_data['happiness'], pet_data['energy'], 
            pet_data['health'], pet_data['discipline'], pet_data['care_mistakes'],
            1 if pet_data['is_alive'] else 0, pet_data['birth_time'], time.time(),
            pet_data['life_stage'], pet_data['state']
        ))
        self.conn.commit()

    def load_pet(self):
        cursor = self.conn.execute("SELECT * FROM pet_stats WHERE id = 1")
        return cursor.fetchone()