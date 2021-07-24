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
