def get_db_connection():

    import pyodbc

    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=ca;"
            "UID=sa;"
            "PWD=binh1811;"
            "TrustServerCertificate=yes;",
        )
        return conn
    except pyodbc.Error as e:
        print(f"Error while connecting to SQL Server: {e}")
        return None
