# CONTEXT.md — Hồ sơ bàn giao dự án X.509 CA System

> **Mục đích:** File này ghi lại toàn bộ trạng thái hiện tại của dự án để bất kỳ ai (hoặc AI session tiếp theo) có thể đọc vào và tiếp tục làm ngay mà không bị mất context.

---

## 1. Tóm tắt dự án

**Tên đề tài:** Hệ thống Web/Desktop quản lý và cấp phát chứng nhận số theo tiêu chuẩn X.509.

**Stack đã chọn:**
| Layer | Công nghệ |
|---|---|
| Backend | Python 3.11+ / Flask 3.0 |
| Database | MySQL (kết nối qua `pyodbc`) |
| Frontend | HTML/CSS/JS thuần + Jinja2 template |
| Crypto | `cryptography` library (PyCA) |
| Kiến trúc | Monolithic (1 repo, 1 process) |

---

## 2. Cấu trúc thư mục hiện tại

```
x509_ca/
├── app.py               ✅ HOÀN THÀNH — Flask app, toàn bộ routes
├── database.py          ✅ HOÀN THÀNH — Kết nối pyodbc + schema SQL + init_db()
├── models.py            ✅ HOÀN THÀNH — Toàn bộ CRUD (users, certs, requests, logs)
├── crypto.py            ✅ HOÀN THÀNH — X.509 logic: tạo Root CA, CSR, ký cert
├── requirements.txt     ✅ HOÀN THÀNH
├── .env.example         ✅ HOÀN THÀNH — Copy thành .env và điền giá trị
│
├── templates/
│   ├── base.html                  ✅ Sidebar nav + flash messages
│   ├── login.html                 ✅ Trang đăng nhập (với deco panel)
│   ├── register.html              ✅ Đăng ký tài khoản
│   ├── change_password.html       ✅ Đổi mật khẩu
│   ├── dashboard_admin.html       ✅ Dashboard admin (stats + recent logs)
│   ├── dashboard_user.html        ✅ Dashboard khách hàng
│   ├── request_cert.html          ✅ Form yêu cầu chứng nhận mới
│   ├── download_private_key.html  ✅ Trang tải private key (hiện 1 lần)
│   ├── my_requests.html           ✅ Danh sách yêu cầu của tôi
│   ├── my_certs.html              ✅ Danh sách chứng nhận của tôi
│   ├── admin_root_ca.html         ✅ Danh sách Root CA
│   ├── admin_create_root_ca.html  ✅ Form tạo Root CA
│   ├── admin_requests.html        ✅ Danh sách yêu cầu (admin)
│   ├── admin_request_detail.html  ✅ Chi tiết + phê duyệt / từ chối
│   ├── admin_certs.html           ✅ Danh sách chứng nhận + search
│   ├── admin_cert_detail.html     ✅ Chi tiết cert + thu hồi
│   ├── admin_users.html           ✅ Danh sách users
│   ├── admin_create_user.html     ✅ Form tạo user (admin)
│   ├── admin_logs.html            ✅ Audit log
│   └── verify_cert.html           ✅ Public verify (không cần login)
│
├── static/
│   ├── css/style.css   ✅ HOÀN THÀNH — Dark theme, full responsive
│   └── js/main.js      ✅ HOÀN THÀNH — Auto-dismiss flash, copy PEM
```

---

## 3. Những gì ĐÃ làm được ✅

### Backend (app.py)
- [x] Login / Logout / Register / Change Password
- [x] Session-based auth với decorator `@login_required`, `@admin_required`
- [x] Dashboard admin (stats) và dashboard user
- [x] Tạo Root CA (admin) → lưu vào DB
- [x] Khách hàng submit yêu cầu → sinh CSR + key pair tự động
- [x] Private key trả về qua session 1 lần → user phải tải ngay
- [x] Admin xem danh sách yêu cầu, lọc theo status
- [x] Admin phê duyệt (chọn Root CA → ký CSR → lưu cert)
- [x] Admin từ chối (kèm lý do)
- [x] Admin thu hồi chứng nhận (revoke)
- [x] Tải cert/root CA dưới dạng file `.pem`
- [x] Tìm kiếm chứng nhận
- [x] Public endpoint `/verify/<id>` không cần login
- [x] Audit log ghi tất cả hành động quan trọng
- [x] `seed_admin_if_empty()` tạo admin mặc định khi chạy lần đầu

### Database (database.py + models.py)
- [x] Schema 5 bảng: `users`, `root_certificates`, `certificate_requests`, `certificates`, `audit_logs`
- [x] Toàn bộ CRUD qua pyodbc
- [x] Password hashing (SHA256 + salt, không dùng plaintext)

### Crypto (crypto.py)
- [x] Tạo RSA 2048-bit key pair
- [x] Tạo Root CA self-signed (X.509v3, BasicConstraints CA=True)
- [x] Tạo CSR với Subject + SAN extension
- [x] Ký CSR bằng Root CA → X.509 certificate hợp lệ
- [x] Helper: kiểm tra cert còn hạn, trích xuất thông tin cert

---

## 4. Những gì CÒN THIẾU ❌ (cần làm tiếp)

### Ưu tiên cao (cần cho đồ án)
- [ ] **`app.py` load .env**: Thêm `from dotenv import load_dotenv; load_dotenv()` ở đầu file
- [ ] **Upload CSR thủ công**: Đề bài yêu cầu user có thể upload file CSR riêng thay vì để server tự sinh. Cần thêm route và form upload `.pem` / `.csr`
- [ ] **Renew certificate**: Route `/admin/certificates/<id>/renew` — ký lại cert cũ với thời hạn mới
- [ ] **Trang profile user**: Xem thông tin tài khoản cá nhân
- [ ] **Phân trang (pagination)**: Bảng chứng nhận và log có thể rất dài

### Ưu tiên trung bình
- [ ] **Xem cert của người khác (admin)**: Admin xem chứng nhận của 1 user cụ thể
- [ ] **Deactivate/activate user**: Admin vô hiệu hóa tài khoản (`is_active = 0`)
- [ ] **Export danh sách**: Tải CSV danh sách chứng nhận
- [ ] **CRL (Certificate Revocation List)**: Tạo file CRL chuẩn X.509 để download
- [ ] **Thông báo trạng thái qua email**: Khi cert được duyệt/từ chối

### Ưu tiên thấp (nice-to-have)
- [ ] **Mã hóa Private Key Root CA trong DB**: Dùng Fernet từ `cryptography` với key từ `.env`
- [ ] **Dark/Light mode toggle**
- [ ] **Responsive mobile** (sidebar collapse)
- [ ] **Loading state** khi tạo Root CA (mất ~1–2 giây)

---

## 5. Hướng dẫn cài đặt và chạy

### Bước 1: Cài đặt Python dependencies
```bash
pip install -r requirements.txt
```

### Bước 2: Cài MySQL ODBC Driver
- Windows: Tải từ https://dev.mysql.com/downloads/connector/odbc/
- Chọn "MySQL ODBC 8.0 Unicode Driver"

### Bước 3: Tạo file .env
```bash
cp .env.example .env
# Mở .env và điền DB_PASSWORD, SECRET_KEY
```

### Bước 4: Chạy ứng dụng
```bash
python app.py
```
- Lần đầu chạy: tự động tạo database `x509_ca` và bảng
- Tự động tạo tài khoản admin: `admin` / `Admin@123`
- Truy cập: http://localhost:5000

### Bước 5: Luồng test cơ bản
1. Đăng nhập admin → Tạo Root CA
2. Đăng ký tài khoản customer
3. Login customer → Yêu cầu chứng nhận → Tải private key
4. Login admin → Phê duyệt → Chọn Root CA → Cấp cert
5. Login customer → Tải cert → Verify tại `/verify/<id>`

---

## 6. Các điểm kỹ thuật cần chú ý khi làm tiếp

### pyodbc với MySQL
```python
# Nếu lỗi "Data source name not found":
# → Kiểm tra tên driver trong DB_CONFIG khớp với tên trong ODBC Data Sources
# → Windows: tìm trong Control Panel > ODBC Data Sources > Drivers tab
```

### Jinja2 filter tùy chỉnh (nếu cần thêm)
```python
# Thêm vào app.py sau khi tạo app:
@app.template_filter('datetime_format')
def datetime_format(value, fmt='%d/%m/%Y %H:%M'):
    if value is None: return '—'
    return value.strftime(fmt)
```

### Upload CSR (việc cần làm tiếp)
```python
# Route cần thêm vào app.py:
@app.route("/request-cert/upload", methods=["GET","POST"])
@login_required
def request_cert_upload():
    if request.method == "POST":
        csr_file = request.files.get("csr_file")
        csr_pem = csr_file.read().decode("utf-8")
        # validate CSR bằng crypto.py, rồi lưu vào DB
        ...
```

### Renew certificate
```python
# Cần thêm hàm vào crypto.py:
def renew_cert(old_cert_pem, ca_cert_pem, ca_key_pem, days=365):
    # Load cert cũ, lấy public key + subject, sign lại với serial mới
    ...
```

---

## 7. Mapping tính năng đề bài → Code

| Yêu cầu đề bài | File | Function/Route |
|---|---|---|
| Đăng nhập admin | app.py | `POST /login` |
| Đổi mật khẩu | app.py | `/change-password` |
| Thiết lập thông số kỹ thuật (Root CA) | app.py | `/admin/root-ca/create` |
| Phát sinh Public/Private key | crypto.py | `generate_key_pair()` |
| Phát sinh Root Certificate | crypto.py | `create_root_ca()` |
| Từ chối yêu cầu X.509 | app.py | `POST /admin/requests/<id>/reject` |
| Phê duyệt yêu cầu X.509 | app.py | `POST /admin/requests/<id>/approve` |
| Quản lý cert (revoke, renew) | app.py | `/admin/certificates/<id>/revoke` |
| Quản lý phí duyệt *(nếu có)* | models.py | Có thể thêm bảng `fees` |
| Cập nhật danh sách thu hồi | models.py | `revoke_certificate()` |
| Theo dõi nhật ký | models.py | `log_action()` / `/admin/logs` |
| Đăng ký khách hàng | app.py | `POST /register` |
| Gửi CSR | app.py | `POST /request-cert` |
| Phát sinh Public/Private key cá nhân | crypto.py | `create_csr()` |
| Yêu cầu chứng nhận X.509 | app.py | `/request-cert` |
| Tải chứng nhận về | app.py | `/my-certs/<id>/download` |
| Tra cứu / xem cert người khác | app.py | `/verify/<id>` *(public)* |
| Upload file CSR | ❌ CHƯA LÀM | Xem mục 4 |

---

## 8. Câu hỏi mở cần quyết định

1. **Đề bài có yêu cầu giao diện Desktop app không?** — Đề nói "Web / Desktop app". Nếu cần desktop, có thể dùng `pywebview` để wrap Flask thành desktop app mà không cần viết lại.

2. **Mã hóa private key Root CA**: Hiện tại lưu plaintext trong DB (chỉ phù hợp demo). Nếu giảng viên hỏi về bảo mật, cần thêm mã hóa bằng `cryptography.fernet`.

3. **Phí duyệt chứng nhận**: Đề bài mention "Thuật toán bàn bạc giá phí". Chưa rõ yêu cầu cụ thể — cần hỏi lại giảng viên.

---

*Cập nhật lần cuối: Session 1 — hoàn thành core features (70%).*
*Session tiếp theo: Upload CSR, Renew, Pagination, mã hóa private key.*
