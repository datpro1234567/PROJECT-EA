from db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash


def create_user(username, email, password):
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        hashed_pw = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, hashed_pw),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def authenticate_user(username, password):
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, username, password_hash, role FROM users WHERE username = %s",
            (username,),
        )
        user = cursor.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            return {
                "user_id": user["user_id"],
                "username": user["username"],
                "role": user.get("role", "user"),
            }
        return None
    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def check_user_exists(username, email):
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE username = %s OR email = %s",
            (username, email),
        )
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
