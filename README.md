# PROJECT-EA
🔐 PROJECT-EA — Certificate Authority Management System

> Hệ thống quản lý Chứng nhận số X.509, hỗ trợ toàn bộ vòng đời chứng nhận SSL/TLS — từ tạo Root CA, cấp phát, đến thu hồi — thông qua giao diện Web trực quan.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-Educational-green)
![Branch](https://img.shields.io/badge/Branch-refactoring-orange)

---

## 📋 Mục lục

- [Giới thiệu](#giới-thiệu)
- [Tính năng](#tính-năng)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Tech Stack](#tech-stack)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cài đặt & Chạy](#cài-đặt--chạy)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
- [Lưu ý bảo mật](#lưu-ý-bảo-mật)
- [Roadmap](#roadmap)
- [Đóng góp](#đóng-góp)
- [Giấy phép](#giấy-phép)

---

## Giới thiệu

**PROJECT-EA** là một hệ thống PKI (Public Key Infrastructure) xây dựng trên Flask, cho phép tổ chức tự vận hành CA nội bộ để:

- Cấp phát **chứng nhận số X.509** cho các website/dịch vụ
- Quản lý toàn bộ **vòng đời chứng nhận**: tạo, ký, gia hạn, thu hồi
- Phân quyền **Admin / Customer** với luồng phê duyệt rõ ràng
- Theo dõi hoạt động hệ thống qua **dashboard quản trị**

---

## Tính năng

### 🔑 Xác thực & Phân quyền

| Tính năng | Mô tả |
|---|---|
| Đăng ký / Đăng nhập | Session-based authentication |
| Đổi mật khẩu | Người dùng tự đổi |
| Phân quyền | Role-based: Admin / Customer |

### 📜 Certificate Authority

| Tính năng | Mô tả |
|---|---|
| Tạo Root CA | Sinh cặp khóa RSA và tự ký CA certificate |
| Tạo cặp khóa | Sinh key pair cho từng khách hàng |
| Tải private key | Download key về máy cục bộ |
| Tạo CSR | Certificate Signing Request |
| Cấp phát chứng nhận | Ký CSR và phát hành certificate |
| Gia hạn chứng nhận | Renew trước khi hết hạn |
| Thu hồi chứng nhận | Revoke và cập nhật CRL |
| Quản lý CRL | Certificate Revocation List |

### 🛠️ Quản trị (Admin)

| Tính năng | Mô tả |
|---|---|
| Dashboard | Tổng quan hoạt động hệ thống |
| Duyệt yêu cầu | Approve / Reject certificate request |
| Theo dõi revoke | Danh sách chứng nhận đã thu hồi |
| Theo dõi hoạt động | System activity tracking |

---

## Kiến trúc hệ thống

```
┌──────────────────────────────────────────┐
│             Web Browser                  │
│           HTML / CSS / JS                │
└───────────────────┬──────────────────────┘
                    │ HTTP
┌───────────────────▼──────────────────────┐
│            Flask Application             │
│   routes/ → controllers/ → services/    │
└───────────────────┬──────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼──────────┐   ┌────────▼─────────────────┐
│  Cryptography    │   │     SQLite Database       │
│  (Python lib)    │   │  Users / Certs / CA /     │
│  X.509 / RSA     │   │  Requests / CRL           │
└──────────────────┘   └──────────────────────────┘
```

### Luồng phê duyệt chứng nhận

```
Customer                        Admin
   │                              │
   ├─ Tạo key pair                │
   ├─ Tạo CSR ─────────────────► Review
   │                              ├─ Approve ──► Certificate issued
   │                              └─ Reject  ──► Thông báo từ chối
   ◄─ Download certificate ───────┘
```

---

## Tech Stack

| Lớp | Công nghệ |
|---|---|
| **Backend** | Python 3.10+, Flask, Flask-CORS |
| **Cryptography** | `cryptography` (Python library) |
| **Database** | SQLite |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Config** | `python-dotenv` |
| **Chuẩn** | X.509 v3, SSL/TLS |

---

## Yêu cầu hệ thống

- Python **3.10+**
- pip
- Git

---

## Cài đặt & Chạy

### 1. Clone repository

```bash
git clone https://github.com/datpro1234567/PROJECT-EA.git
cd PROJECT-EA/project
git checkout refactoring
```

### 2. Tạo môi trường ảo

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` bao gồm:

```txt
Flask
Flask-Cors
python-dotenv
cryptography
```

### 4. Cấu hình biến môi trường

Tạo file `.env` tại thư mục gốc:

```env
SECRET_KEY=change-this-to-a-random-secret
DEBUG=True
```

> ⚠️ Không commit file `.env` lên repository. Hãy đảm bảo `.env` có trong `.gitignore`.

### 5. Khởi tạo database

Chạy `schema.sql` để tạo các bảng:

```bash
sqlite3 app.db < schema.sql
```

### 6. Chạy ứng dụng

```bash
python run.py
```

Truy cập tại: **http://localhost:5000**

---

## Cấu trúc dự án

```
PROJECT-EA/
└── project/
    ├── run.py               # Entry point — khởi chạy Flask app
    ├── db.py                # Kết nối và khởi tạo SQLite database
    ├── validators.py        # Validation dữ liệu đầu vào
    ├── schema.sql           # DDL: định nghĩa bảng database
    ├── debug_queries.sql    # SQL queries dùng khi debug
    ├── requirements.txt     # Python dependencies
    │
    ├── routes/              # Đăng ký blueprint / khởi tạo app
    ├── controllers/         # Xử lý request, trả về response
    ├── services/            # Business logic: PKI, crypto operations
    │
    ├── views/               # HTML templates (Jinja2)
    └── static/              # CSS, JavaScript assets
```

---

## Hướng dẫn sử dụng

### Luồng Customer

1. **Đăng ký** tài khoản tại `/register`
2. **Đăng nhập** tại `/login`
3. **Tạo cặp khóa** RSA cá nhân
4. **Tạo CSR** và gửi yêu cầu cấp phát chứng nhận
5. Chờ Admin **phê duyệt** — nhận thông báo kết quả
6. **Tải về** chứng nhận đã được ký (`.pem` / `.crt`)
7. **Yêu cầu thu hồi** nếu cần thiết

### Luồng Admin

1. **Tạo Root CA**: sinh cặp khóa và certificate tự ký
2. **Duyệt yêu cầu**: Approve / Reject từng CSR từ customer
3. **Theo dõi chứng nhận**: quản lý danh sách đã cấp, đã thu hồi
4. **Gia hạn / Thu hồi**: thực hiện khi cần thiết
5. **Dashboard**: theo dõi hoạt động toàn hệ thống

---

## Lưu ý bảo mật

> ⚠️ Dự án hiện đang ở giai đoạn phát triển / học thuật. **Không dùng trực tiếp trong môi trường production** khi chưa áp dụng các cải tiến bảo mật dưới đây.

| Hạng mục | Khuyến nghị |
|---|---|
| 🔒 Credentials | Lưu toàn bộ vào `.env`, không hardcode |
| 🌐 HTTPS | Bắt buộc dùng HTTPS khi deploy |
| 🗝️ Private Key | Mã hóa private key khi lưu vào DB |
| 🛡️ CSRF | Thêm CSRF protection cho form |
| 🚦 Rate Limiting | Giới hạn request để chống brute-force |
| 📝 Logging | Thêm centralized logging |
| ✅ Testing | Viết automated tests trước khi production |

---

## Roadmap

- [ ] Tách REST API riêng biệt
- [ ] JWT authentication
- [ ] Docker support
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Unit & integration testing
- [ ] Certificate chain validation
- [ ] OCSP (Online Certificate Status Protocol) support
- [ ] Audit logging

---

## Giấy phép

Dự án này được phát triển cho mục đích **học thuật và nghiên cứu**.

---

</div>
