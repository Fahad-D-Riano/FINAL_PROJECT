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