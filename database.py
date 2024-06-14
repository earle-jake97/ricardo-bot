import sqlite3

# Connect to the SQLite database (it will create the file if it doesn't exist)
conn = sqlite3.connect('currency.db')
c = conn.cursor()

# Create a table to store user balances and usernames
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER NOT NULL DEFAULT 0,
    pp INTEGER NOT NULL DEFAULT 0,
    participation_percentage FLOAT NOT NULL DEFAULT 0.0
)
''')



# Commit the changes and close the connection
conn.commit()
conn.close()

import sqlite3

# Connect to the database
conn = sqlite3.connect('currency.db')
c = conn.cursor()

# Add new columns to the users table if they don't already exist
try:
    c.execute('ALTER TABLE users ADD COLUMN pp INTEGER NOT NULL DEFAULT 0')
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("Column 'pp' already exists.")
    else:
        raise

try:
    c.execute('ALTER TABLE users ADD COLUMN participation_percentage FLOAT NOT NULL DEFAULT 0.0')
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("Column 'participation_percentage' already exists.")
    else:
        raise

conn.commit()
conn.close()
