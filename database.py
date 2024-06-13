import sqlite3

# Connect to the SQLite database (it will create the file if it doesn't exist)
conn = sqlite3.connect('currency.db')
c = conn.cursor()

# Create a table to store user balances and usernames
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER NOT NULL DEFAULT 0
)
''')

# Commit the changes and close the connection
conn.commit()
conn.close()
