import pyodbc

def getConnection():
    con = pyodbc.connect(
    """
    DRIVER={ODBC Driver 17 for SQL Server};
    SERVER=.;
    DATABASE=DB;
    TRUSTED_CONNECTION=YES;
    """
    )
    return con

    
