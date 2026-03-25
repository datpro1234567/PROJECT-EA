import sqlite3


TABLES = {
    1: "users",
    2: "user_keys",
    3: "csr_requests",
    4: "certificates",
    5: "revocation_requests",
    6: "certificate_revocation_list",
    7: "system_config",
    8: "ca_keys",
    9: "logs",
}


def show_table(table_name: str) -> None:
    con = sqlite3.connect("database.db")
    cursor = con.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    con.close()

    print(f"\nTable: {table_name}")
    if not rows:
        print("(empty)")
        return

    for row in rows:
        print(row)


def main() -> None:
    while True:
        print("Chọn bảng để hiển thị:")
        for idx, name in TABLES.items():
            print(f"{idx}. {name}")
        print("0. Thoát")

        try:
            choice = int(input("Nhập số: ").strip())
        except ValueError:
            print("Lựa chọn không hợp lệ")
            return

        if choice == 0:
            return

        table_name = TABLES.get(choice)
        if not table_name:
            print("Lựa chọn không hợp lệ")
            return

        show_table(table_name)
        pause = input("\nNhấn Enter để tiếp tục")


if __name__ == "__main__":
    main()