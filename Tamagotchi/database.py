import sqlite3
import time

class DatabaseManager:
    """Handles SQL persistence to keep the pet 'alive' on disk."""
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        self._initialize_items()

    def create_tables(self):
        """Creates the 14-column schema, now including pet name and points."""
        query = """
        CREATE TABLE IF NOT EXISTS pet_stats (
            id INTEGER PRIMARY KEY,
            fullness REAL, happiness REAL, energy REAL, health REAL,
            discipline REAL, care_mistakes INTEGER,
            is_alive INTEGER, birth_time REAL, last_update REAL,
            life_stage TEXT, state TEXT, name TEXT, points INTEGER
        )
        """
        self.conn.execute(query)

        # Inventory Table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                item_id INTEGER PRIMARY KEY,
                quantity INTEGER NOT NULL
            )
        """)

        # Items Table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                effect_stat TEXT,
                effect_value REAL
            )
        """)
        self.conn.commit()

    def _initialize_items(self):
        """Populate the items table with default items if it's empty."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM items")
        if cursor.fetchone()[0] == 0:
            default_items = [
                ('Standard Meal', 'A basic, balanced meal.', 'fullness', 20),
                ('Candy', 'A tasty treat that boosts happiness.', 'happiness', 15),
                ('Energy Drink', 'A quick boost of energy.', 'energy', 30),
                ('Medicine', 'Helps recover from sickness.', 'health', 25),
            ]
            self.conn.executemany("""
                INSERT INTO items (name, description, effect_stat, effect_value)
                VALUES (?, ?, ?, ?)
            """, default_items)
            self.conn.commit()

    def get_inventory(self):
        """Retrieves the player's inventory."""
        cursor = self.conn.execute("SELECT i.name, inv.quantity, i.description, i.effect_stat, i.effect_value FROM inventory inv JOIN items i ON inv.item_id = i.id")
        return cursor.fetchall()

    def add_item_to_inventory(self, item_name, quantity=1):
        """Adds a specified quantity of an item to the inventory."""
        cursor = self.conn.execute("SELECT id FROM items WHERE name = ?", (item_name,))
        item_id = cursor.fetchone()
        if item_id:
            cursor.execute("SELECT quantity FROM inventory WHERE item_id = ?", (item_id[0],))
            current_quantity = cursor.fetchone()
            if current_quantity:
                new_quantity = current_quantity[0] + quantity
                self.conn.execute("UPDATE inventory SET quantity = ? WHERE item_id = ?", (new_quantity, item_id[0]))
            else:
                self.conn.execute("INSERT INTO inventory (item_id, quantity) VALUES (?, ?)", (item_id[0], quantity))
            self.conn.commit()

    def remove_item_from_inventory(self, item_name, quantity=1):
        """Removes a specified quantity of an item from the inventory."""
        cursor = self.conn.execute("SELECT id FROM items WHERE name = ?", (item_name,))
        item_id = cursor.fetchone()
        if item_id:
            cursor.execute("SELECT quantity FROM inventory WHERE item_id = ?", (item_id[0],))
            current_quantity = cursor.fetchone()
            if current_quantity and current_quantity[0] >= quantity:
                new_quantity = current_quantity[0] - quantity
                if new_quantity > 0:
                    self.conn.execute("UPDATE inventory SET quantity = ? WHERE item_id = ?", (new_quantity, item_id[0]))
                else:
                    self.conn.execute("DELETE FROM inventory WHERE item_id = ?", (item_id[0],))
                self.conn.commit()
                return True
        return False

    def get_item(self, item_name):
        """Retrieves a single item's details by name."""
        cursor = self.conn.execute("SELECT * FROM items WHERE name = ?", (item_name,))
        return cursor.fetchone()

    def save_pet(self, pet_data):
        query = """
        INSERT OR REPLACE INTO pet_stats 
        (id, fullness, happiness, energy, health, discipline, care_mistakes, 
         is_alive, birth_time, last_update, life_stage, state, name, points)
        VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        self.conn.execute(query, (
            pet_data['fullness'], pet_data['happiness'], pet_data['energy'], 
            pet_data['health'], pet_data['discipline'], pet_data['care_mistakes'],
            1 if pet_data['is_alive'] else 0, pet_data['birth_time'], time.time(),
            pet_data['life_stage'], pet_data['state'], pet_data['name'], pet_data['points']
        ))
        self.conn.commit()

    def load_pet(self):
        cursor = self.conn.execute("SELECT * FROM pet_stats WHERE id = 1")
        return cursor.fetchone()