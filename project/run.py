from routes import create_app
from db import get_db_connection

# 2. KHỞI TẠO ỨNG DỤNG
app = create_app()

if __name__ == "__main__":
    print(">>> KHOI DONG SERVER TAI PORT 5000...")

    # Kiểm tra kết nối DB ngay khi khởi động để debug
    conn = get_db_connection()
    if conn is not None:
        print("[DB] Ket noi SQL Server thanh cong.")
        conn.close()
    else:
        print("[DB] LOI: Khong the ket noi den SQL Server. kiem tra db.py / connection string.")

    # 4. KÍCH HOẠT SERVER
    app.run(host="0.0.0.0", port=5000, debug=True)
