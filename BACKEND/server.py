from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_cors import CORS
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
import os
import sqlite3

app = Flask(__name__)

# Allow requests from the React frontend (Vite default: http://localhost:5173)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5173"}})

CERTS_DIR = "certs"
# Ensure certs directory exists
if not os.path.exists(CERTS_DIR):
    os.makedirs(CERTS_DIR)
app.secret_key = "secret123"

# --- HELPER: Database Connection ---
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/submit", methods=["POST"])
def submit():
    """API used by the React frontend to register a new user.

    Expects JSON body: {"name": "...", "password": "..."}
    Returns JSON with success flag and message.
    """

    data = request.get_json(silent=True) or {}
    username = data.get("name")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "Missing name or password"}), 400

    conn = get_db_connection()
    try:
        # NOTE: In a real app, hash the password before storing.
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password, "user"),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Username already exists"}), 409
    finally:
        conn.close()

    return jsonify({"success": True, "message": "User created"}), 201

@app.route("/")
def home():
    return render_template("index.html")

 
@app.route("/create_csr", methods=["GET", "POST"])
def create_csr():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        domain = request.form["domain"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("INSERT INTO csr_requests (user_id, domain, status) VALUES (?, ?, ?)",
                  (session["user_id"], domain, "pending"))

        conn.commit()
        conn.close()

        return "CSR request submitted!"

    return render_template("create_csr.html")

@app.route("/admin_generate_root", methods=["POST"])
def admin_generate_root():
    if session.get("role") != "admin":
        return "Access denied"
    
    # 1. Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # 2. Key/Cert Information
    # In a real app, these details should come from a form or config
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GoodWeb CA Authority"),
        x509.NameAttribute(NameOID.COMMON_NAME, "GoodWeb Root CA"),
    ])

    # 3. Create Root Certificate (Self-signed)
    cert = x509.CertificateBuilder()\
        .subject_name(subject)\
        .issuer_name(issuer)\
        .public_key(key.public_key())\
        .serial_number(x509.random_serial_number())\
        .not_valid_before(datetime.datetime.utcnow())\
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))\
        .sign(key, hashes.SHA256())

    # 4. Save to server
    key_path = os.path.join(CERTS_DIR, "root_key.pem")
    cert_path = os.path.join(CERTS_DIR, "root_cert.pem")

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Save info to DB (Optional but good for tracking)
    conn = get_db_connection()
    c = conn.cursor()
    # Check if root_ca table entry exists, if not create, else update (or just append a new active CA)
    # For simplicity, we'll just insert a new record
    c.execute("INSERT INTO root_ca (private_key_pem, certificate_pem) VALUES (?, ?)",
              ("Stored in file system (safe practice)", "Stored in file system"))
    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return "Access denied"

    conn = get_db_connection()
    requests = conn.execute("SELECT * FROM csr_requests").fetchall()
    
    # Check if Root CA exists
    root_ca_exists = os.path.exists(os.path.join(CERTS_DIR, "root_key.pem")) and \
                     os.path.exists(os.path.join(CERTS_DIR, "root_cert.pem"))

    conn.close()

    return render_template("admin.html", requests=requests, root_ca_exists=root_ca_exists)

@app.route("/approve/<int:req_id>")
def approve(req_id):
    if session.get("role") != "admin":
        return "Access denied"

    conn = get_db_connection()
    # In a real app, here we would sign the certificate.
    # For now, just mark as approved.
    conn.execute("UPDATE csr_requests SET status='approved' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        try:
            # Note: In a real app, hash the password here!
            conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                      (username, password, "user"))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists"
        finally:
            conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, password)).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            if user["role"] == "admin":
                return redirect("/admin")
            return redirect("/")
        else:
            return "Login failed"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    # host='0.0.0.0' allows access from other machines (e.g. over VPN)
    app.run(debug=True, host='0.0.0.0', port=5000)