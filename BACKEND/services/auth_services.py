from db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash


def create_user(username, email, password):
    conn = get_db_connection()
    if not conn:
        print("Error creating user: cannot connect to database")
        return None

    try:
        cursor = conn.cursor()
        hashed_pw = generate_password_hash(password)
        default_role = "customer"
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, role, email)
            VALUES (?, ?, ?, ?)
            """,
            (username, hashed_pw, default_role, email),
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
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id AS user_id, username, password_hash, role
            FROM users
            WHERE username = ?
            """,
            (username,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        # Xây dict từ kết quả để tái sử dụng code cũ dễ hơn
        columns = [col[0] for col in cursor.description]
        user = dict(zip(columns, row))

        if user and check_password_hash(user["password_hash"], password):
            return {
                "user_id": user["user_id"],
                "username": user["username"],
                "role": user["role"],
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
        print("Error checking user existence: cannot connect to database")
        return None

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE username = ? OR email = ?",
            (username, email),
        )
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def change_user_password(user_id, old_password, new_password):
    conn = get_db_connection()
    if not conn:
        print("Error changing password: cannot connect to database")
        return None, "Database connection error."

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT password_hash
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return False, "User not found."

        current_hash = row[0]
        if not check_password_hash(current_hash, old_password):
            return False, "Old password is incorrect."

        new_hash = generate_password_hash(new_password)
        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (new_hash, user_id),
        )
        conn.commit()
        return True, "Password changed successfully."
    except Exception as e:
        print(f"Error changing password: {e}")
        conn.rollback()
        return None, "An error occurred while changing password."
    finally:
        cursor.close()
        conn.close()
