from flask import Flask, render_template, request, session, url_for, redirect
from flask_login import login_required, LoginManager, UserMixin, current_user, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime
import json
import os
from dotenv import load_dotenv

project_folder = os.path.expanduser("~/ToDo")
load_dotenv(os.path.join(project_folder, ".env"))
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", default="secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login = LoginManager(app)
login.login_view = "todo"


class User (UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), index=True, unique=True)
    email = db.Column(db.String(255), index=True, unique=True)
    password_hash = db.Column(db.String(200))
    todo_items = db.relationship("ToDo", backref="author", lazy="dynamic")
    tag_items = db.relationship("Tags", backref="author", lazy="dynamic")


class ToDo (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), index=True)
    tag = db.Column(db.String(100), index=True)
    body = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime, index=True)
    completed = db.Column(db.Boolean, default=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))


class Tags (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    @login.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route("/", methods=["POST"])
def index ():
    if current_user.is_authenticated:
        return redirect(url_for("todo"))
    if request.form:
        if "login" in request.form:
            session["form_data"] = ["login"]
            return redirect(url_for("request_processor"))
        elif "sign_up" in request.form:
            session["form_data"] = ["sign_up"]
            return redirect(url_for("request_processor"))
        elif "forgot_password" in request.form:
            session["form_data"] = ["forgot_password"]
            return redirect(url_for("request_processor"))
        elif "submit_signup" in request.form:
            password = generate_password_hash(request.form["password"], "sha256")
            form_inputs = {"username": request.form["username"],
                           "password": password,
                           "password_length": len(request.form["password"]),
                           "matched_passwords": request.form["password"] == request.form["confirm_password"],
                           "email": request.form["email"]}
            session["form_data"] = ["submit_signup", form_inputs]
            return redirect(url_for("request_processor"))
        elif "submit_login" in request.form:
            user = User.query.filter_by(username=request.form["username"]).first()
            form_inputs = {}
            if user is None:
                form_inputs["login"] = False
            else:
                if check_password_hash(user.password_hash, request.form["password"]):
                    login_user(user)
                    return redirect(url_for("todo"))
                form_inputs["login"] = False
            session["form_data"] = ["submit_login", form_inputs]
            return redirect(url_for("request_processor"))
        elif "back_to_main" in request.form:
            return redirect(url_for("index"))

    return render_template("index.html")

@app.route("/", methods=["GET"])
def request_processor():
    if current_user.is_authenticated:
        return redirect(url_for("todo"))
    if "form_data" not in session:
        return render_template("index.html")
    form_data = session["form_data"]
    session.pop("form_data")
    if form_data[0] == "login":
        return render_template("login.html")
    elif form_data[0] == "sign_up":
        return render_template("signup.html")
    elif form_data[0] == "forgot_password":
        return render_template("login.html", recovery_password=True)
    elif form_data[0] == "submit_signup":
        # Validate inputs
        # Check username
        username = form_data[1]["username"]
        password = form_data[1]["password"]
        matched_passwords = form_data[1]["matched_passwords"]
        password_length = form_data[1]["password_length"]
        email = form_data[1]["email"]
        if not 1 <= len(username) <= 100:
            # Length check / Presence check
            return render_template("signup.html", values=[username, email],
                                   error_msg="Enter a username not exceeding 100 in length.")
        else:
            # Validation check
            for char in username:
                # Numbers, upper-case alphabets, lower_case alphabets, -, _
                curr_char = ord(char)
                if not (48 <= curr_char <= 57 or 65 <= curr_char <= 90 or 97 <= curr_char <= 122 or
                        curr_char == 45 or curr_char == 95):
                    return render_template("signup.html", values=[username, email],
                                           error_msg="Enter a username consisting of alphanumeric "
                                                     "characters and dashes.")
        db_usernames = db.session.query(User.username).all()
        for name in db_usernames:
            if name[0] == username:
                return render_template("signup.html", values=[username, email],
                                       error_msg="Username is already taken.")
        # Check email
        db_email = db.session.query(User.email).all()
        for mail in db_email:
            if mail[0] == email:
                return render_template("signup.html", values=[username, email],
                                       error_msg="Email is already taken.")
        # Check password
        if not matched_passwords:
            return render_template("signup.html", values=[username, email],
                                   error_msg="Passwords do not match.")
        if password_length < 5:
            return render_template("signup.html", values=[username, email],
                                   error_msg="Password should be at least 5 characters.")
        # Passed validation checks, add to database
        user = User(username=username, email=email,
                    password_hash=password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("todo"))
    elif form_data[0] == "submit_login":
        if not form_data[1]["login"]:
            return render_template("login.html", error_msg="User name or password is incorrect.")

    return render_template("index.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for("index"))