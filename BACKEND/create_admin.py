import sqlite3
import bcrypt


def create_admin():
    con = sqlite3.connect("database.db")
    cursor = con.cursor()

    cursor.execute(
        """
        SELECT id FROM users
        WHERE username = ?
        """,
        ("admin",),
    )
    existing = cursor.fetchone()
    if existing is not None:
        print("Admin user already exists with id:", existing[0])
        con.close()
        return

    # hash mật khẩu admin bằng bcrypt trước khi lưu
    raw_password = "admin"
    hashed_password = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    cursor.execute(
        """
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (?, ?, ?, 'admin')
        """,
        ("admin", hashed_password, "Nguyễn Át Min"),
    )
    con.commit()

    cursor.execute(
        """
        SELECT id FROM users
        WHERE username = ?
        """,
        ("admin",),
    )
    user = cursor.fetchone()
    con.close()

    if user is not None:
        print("Admin user created with id:", user[0], "(fullname: Nguyễn Át Min, username: admin, password: admin)")
    else:
        print("Failed to create admin user.")


if __name__ == "__main__":
    create_admin()
