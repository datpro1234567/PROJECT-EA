import sqlite3

con = sqlite3.connect("users.db")
cursor = con.cursor()
cursor.execute(
    """
    SELECT * FROM user
    """
)
rows = cursor.fetchall()
con.commit()
con.close()

for row in rows:
    print(row)