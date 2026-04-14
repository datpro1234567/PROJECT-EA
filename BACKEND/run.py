from routes import create_app

# 2. KHỞI TẠO ỨNG DỤNG
app = create_app()

if __name__ == "__main__":
    print(">>> KHOI DONG SERVER TAI PORT 5000...")

    # 4. KÍCH HOẠT SERVER
    app.run(host="0.0.0.0", port=5000, debug=True)
