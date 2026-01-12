import sqlite3
import time

class DatabaseManager:
    """Handles SQL persistence to keep the pet 'alive' on disk."""
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        self._perform_migrations()
        self._initialize_items()
        self._initialize_plants()

    def _perform_migrations(self):
        """Perform database schema migrations."""
        # Migration: Rename 'points' column to 'coins' in pet_stats table
        cursor = self.conn.execute("PRAGMA table_info(pet_stats)")
        columns = [column[1] for column in cursor.fetchall()]
        if "points" in columns and "coins" not in columns:
            print("Performing migration: Renaming 'points' column to 'coins' in 'pet_stats' table.")
            self.conn.execute("ALTER TABLE pet_stats RENAME COLUMN points TO coins")
            self.conn.commit()

    def create_tables(self):
        """Creates the 14-column schema, now including pet name and points."""
        query = """
        CREATE TABLE IF NOT EXISTS pet_stats (
            id INTEGER PRIMARY KEY,
            fullness REAL, happiness REAL, energy REAL, health REAL,
            discipline REAL, care_mistakes INTEGER,
            is_alive INTEGER, birth_time REAL, last_update REAL,
            life_stage TEXT, state TEXT, name TEXT, coins INTEGER
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

        # Plants Table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS plants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                growth_time_seconds INTEGER,
                reward_item TEXT,
                reward_quantity INTEGER
            )
        """)

        # Garden Plots Table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS garden_plots (
                plot_id INTEGER PRIMARY KEY,
                plant_id INTEGER,
                plant_time REAL,
                last_watered_time REAL,
                FOREIGN KEY (plant_id) REFERENCES plants (id)
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
                ('Normal Seed', 'A common seed.', None, None),
                ('Super Meal', 'A super filling meal.', 'fullness', 50),
                ('Snack', 'A quick, free bite.', 'fullness', 10)
            ]
            self.conn.executemany("""
                INSERT INTO items (name, description, effect_stat, effect_value)
                VALUES (?, ?, ?, ?)
            """, default_items)
            self.conn.commit()

    def _initialize_plants(self):
        """Populate the plants table with default plants if it's empty."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM plants")
        if cursor.fetchone()[0] == 0:
            default_plants = [
                ('Berry Bush', 'A simple bush that grows berries.', 60, 'Candy', 1),
            ]
            self.conn.executemany("""
                INSERT INTO plants (name, description, growth_time_seconds, reward_item, reward_quantity)
                VALUES (?, ?, ?, ?, ?)
            """, default_plants)
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

    def get_plant(self, plant_id):
        """Retrieves a single plant's details by id."""
        cursor = self.conn.execute("SELECT * FROM plants WHERE id = ?", (plant_id,))
        return cursor.fetchone()

    def get_garden_plots(self):
        """Retrieves all garden plots."""
        cursor = self.conn.execute("SELECT * FROM garden_plots")
        return cursor.fetchall()

    def plant_seed(self, plot_id, plant_name):
        """Plants a seed in a specific plot."""
        plant_id = None
        if plant_name:
            cursor = self.conn.execute("SELECT id FROM plants WHERE name = ?", (plant_name,))
            plant_id = cursor.fetchone()[0] # Get the actual ID

        self.conn.execute("INSERT OR REPLACE INTO garden_plots (plot_id, plant_id, plant_time, last_watered_time) VALUES (?, ?, ?, ?)",
                          (plot_id, plant_id, time.time(), time.time()))
        self.conn.commit()

    def water_plant(self, plot_id):
        """Updates the last watered time for a plant."""
        self.conn.execute("UPDATE garden_plots SET last_watered_time = ? WHERE plot_id = ?", (time.time(), plot_id))
        self.conn.commit()

    def save_pet(self, pet_data):
        query = """
        INSERT OR REPLACE INTO pet_stats 
        (id, fullness, happiness, energy, health, discipline, care_mistakes, 
         is_alive, birth_time, last_update, life_stage, state, name, coins)
        VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        self.conn.execute(query, (
            pet_data['fullness'], pet_data['happiness'], pet_data['energy'], 
            pet_data['health'], pet_data['discipline'], pet_data['care_mistakes'],
            1 if pet_data['is_alive'] else 0, pet_data['birth_time'], time.time(),
            pet_data['life_stage'], pet_data['state'], pet_data['name'], pet_data['coins']
        ))
        self.conn.commit()

    def load_pet(self):
        cursor = self.conn.execute("SELECT * FROM pet_stats WHERE id = 1")
        return cursor.fetchone()