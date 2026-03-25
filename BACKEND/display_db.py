import sqlite3

con = sqlite3.connect("database.db")
cursor = con.cursor()
cursor.execute(
    """
    SELECT * FROM users
    """
)
rows = cursor.fetchall()
con.commit()
con.close()

for row in rows:
    print(row)