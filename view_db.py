import sqlite3

# Change "data.db" to your database file name
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)

# View data from each table
for table_name in tables:
    print(f"\nData from {table_name[0]}:")
    cursor.execute(f"SELECT * FROM {table_name[0]}")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

conn.close()