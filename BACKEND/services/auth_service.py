import sqlite3
import bcrypt

from database.init_db import DB_PATH


def register_user(username: str, password: str, full_name: str) -> dict:
    """Handle user registration logic.

    Returns a dict with at least a `status` field.
    """
    if not username or not password or not full_name:
        return {"status": "failure", "message": "All fields are required"}

    con = sqlite3.connect(DB_PATH, timeout=5)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        (username,),
    )
    user = cursor.fetchone()
    if user is not None:
        con.close()
        return {"status": "failure"}

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    cursor.execute(
        """
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (?, ?, ?, 'user')
        """,
        (username, hashed, full_name),
    )
    con.commit()
    con.close()

    return {"status": "success"}


def verify_user(username: str, password: str) -> dict:
    """Verify user credentials.

    Returns dict with status and user info on success.
    """
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT id, full_name, role, password_hash
        FROM users
        WHERE username = ?
        """,
        (username,),
    )
    user = cursor.fetchone()
    con.close()

    if user is not None:
        stored_hash = user["password_hash"]
        if stored_hash and bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            return {
                "status": "success",
                "id": user["id"],
                "full_name": user["full_name"],
                "role": user["role"],
            }
    return {"status": "failure"}


def change_password(user_id: int, new_password: str) -> dict:
    """Change password for a given user id."""
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    con = sqlite3.connect(DB_PATH)
    cursor = con.cursor()
    cursor.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE id = ?
        """,
        (hashed, user_id),
    )
    con.commit()
    con.close()

    return {"status": "success"}
