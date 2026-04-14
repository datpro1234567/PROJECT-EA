def get_db_connection():
    """Kết nối đến SQL Server (thay cho MySQL).

    Yêu cầu:
    - Cài ODBC Driver cho SQL Server (ví dụ: "ODBC Driver 18 for SQL Server").
    - Cài thư viện pyodbc trong môi trường Python.

    Chỉnh lại SERVER, UID, PWD cho đúng với máy của bạn.
    """

    import pyodbc

    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=ea_db;"
            "UID=sa;"
            "PWD=Lubaodat5?;"
            "TrustServerCertificate=yes;",
        )
        return conn
    except pyodbc.Error as e:
        print(f"Error while connecting to SQL Server: {e}")
        return None
