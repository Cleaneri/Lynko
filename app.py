import os
import secrets
import string
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this")
database_url = os.environ.get("DATABASE_URL", "sqlite:///lynko_local.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("RENDER", "") == "true"

db = SQLAlchemy(app)
csrf = CSRFProtect(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    links = db.relationship("ShortLink", backref="owner", cascade="all, delete-orphan")


class ShortLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(12), unique=True, nullable=False, index=True)
    target_url = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)


def current_user():
    user_id = request.cookies.get("lynko_user")  # not used for authentication
    from flask import session
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def make_code(length=8):
    alphabet = string.ascii_letters + string.digits
    for _ in range(10):
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        if not ShortLink.query.filter_by(code=code).first():
            return code
    raise RuntimeError("Could not generate a unique short code")


def valid_target(value):
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


@app.route("/")
def index():
    user = current_user()
    links = ShortLink.query.filter_by(user_id=user.id).order_by(ShortLink.created_at.desc()).all() if user else []
    return render_template("index.html", page="home", links=links)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(username) < 3 or len(username) > 32:
            flash("Kullanıcı adı 3-32 karakter olmalı.", "error")
        elif "@" not in email or len(email) > 254:
            flash("Geçerli bir e-posta adresi gir.", "error")
        elif len(password) < 8:
            flash("Şifre en az 8 karakter olmalı.", "error")
        elif User.query.filter(func.lower(User.username) == username.lower()).first():
            flash("Bu kullanıcı adı zaten kullanılıyor.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Bu e-posta zaten kayıtlı.", "error")
        else:
            user = User(username=username, email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            from flask import session
            session.clear()
            session["user_id"] = user.id
            flash("Hesabın oluşturuldu. Lynko'ya hoş geldin!", "success")
            return redirect(url_for("index"))
    return render_template("index.html", page="register", links=[])


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            (func.lower(User.username) == identity.lower()) |
            (func.lower(User.email) == identity.lower())
        ).first()
        if user and check_password_hash(user.password_hash, password):
            from flask import session
            session.clear()
            session["user_id"] = user.id
            flash("Giriş başarılı.", "success")
            return redirect(url_for("index"))
        flash("Kullanıcı bilgileri veya şifre hatalı.", "error")
    return render_template("index.html", page="login", links=[])


@app.post("/logout")
def logout():
    from flask import session
    session.clear()
    flash("Oturum kapatıldı.", "success")
    return redirect(url_for("index"))


@app.post("/create")
def create_link():
    user = current_user()
    if not user:
        flash("Bağlantı oluşturmak için önce giriş yapmalısın.", "error")
        return redirect(url_for("login"))

    target = request.form.get("target_url", "").strip()
    if len(target) > 4000 or not valid_target(target):
        flash("Geçerli ve http:// veya https:// ile başlayan bir bağlantı gir.", "error")
        return redirect(url_for("index"))

    link = ShortLink(code=make_code(), target_url=target, user_id=user.id)
    db.session.add(link)
    db.session.commit()
    flash("Kısa bağlantın hazır!", "success")
    return redirect(url_for("index"))


@app.post("/delete/<int:link_id>")
def delete_link(link_id):
    user = current_user()
    if not user:
        abort(401)
    link = ShortLink.query.filter_by(id=link_id, user_id=user.id).first_or_404()
    db.session.delete(link)
    db.session.commit()
    flash("Bağlantı silindi.", "success")
    return redirect(url_for("index"))


@app.post("/account/delete")
def delete_account():
    user = current_user()
    if not user:
        abort(401)
    password = request.form.get("password", "")
    if not check_password_hash(user.password_hash, password):
        flash("Hesabı silmek için şifreni doğru girmelisin.", "error")
        return redirect(url_for("index"))
    db.session.delete(user)  # Kullanıcının bağlantıları da silinir.
    db.session.commit()
    from flask import session
    session.clear()
    flash("Hesabın ve bağlantıların silindi.", "success")
    return redirect(url_for("index"))


@app.route("/<string:code>")
def follow_short_link(code):
    # Uygulamanın diğer sayfa yolları kısa kod olarak yorumlanmasın.
    if code in {"register", "login", "logout", "create", "delete", "account"}:
        abort(404)
    link = ShortLink.query.filter_by(code=code).first_or_404()
    return redirect(link.target_url, code=302)


@app.errorhandler(404)
def not_found(_error):
    return render_template("index.html", page="not_found", links=[]), 404


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
