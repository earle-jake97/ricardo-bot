import sqlite3

# Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('currency.db')
c = conn.cursor()

# Create the 'ricardo_hp' table if it doesn't exist
c.execute('''
CREATE TABLE IF NOT EXISTS ricardo_hp (
    id INTEGER PRIMARY KEY,
    hp INTEGER NOT NULL,
    death_count INTEGER NOT NULL,
    initial_hp INTEGER NOT NULL
)
''')

# Initialize Ricardo's HP and death count if they don't already exist
c.execute('INSERT OR IGNORE INTO ricardo_hp (id, hp, death_count, initial_hp) VALUES (1, 50000, 0, 50000)')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database initialized successfully.")
