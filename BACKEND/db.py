def get_db_connection():
    import mysql.connector
    from mysql.connector import Error

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="password",
            database="ea_db",
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None
