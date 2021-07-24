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
