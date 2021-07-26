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

@app.route("/todo", methods=["GET", "POST"])
def todo():
    if not current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.form:
        if "logout" in request.form:
            return redirect(url_for("logout"))
        elif "delete_task" in list(request.form.keys())[0]:
            task = ToDo.query.filter(ToDo.id == int(request.form[list(request.form.keys())[0]])).first()
            db.session.delete(task)
            db.session.commit()
            return redirect(url_for("todo"))
        elif "completed_task" in list(request.form.keys())[0]:
            task = ToDo.query.filter(ToDo.id == int(request.form[list(request.form.keys())[0]])).first()
            task.completed = not task.completed
            db.session.commit()
            return redirect(url_for("todo"))
        elif "delete_tag" in request.form:
            tag = request.form["delete_tag"]

            db_tags = Tags.query.filter(Tags.user_id == current_user.id).all()
            for db_tag in db_tags:
                if tag == db_tag.tag:
                    db.session.delete(db_tag)
                    db.session.commit()
                    return redirect(url_for("todo"))
            return redirect(url_for("todo"))
        elif "create_todo" in request.form:
            # DD/MM/YYYY
            start_date = None
            due_date = None
            if request.form["todo_start_date"]:
                start_date = request.form["todo_start_date"].split("-")
                start_date = [int(d) for d in start_date]
                start_date = datetime(start_date[0], start_date[1], start_date[2])

            if request.form["todo_due_date"]:
                due_date = request.form["todo_due_date"].split("-")
                due_date = [int(d) for d in due_date]
                due_date = datetime(due_date[0], due_date[1], due_date[2])

            todo_item = ToDo(title=request.form["todo_title"],
                             tag=request.form["todo_tag"],
                             body=request.form["todo_body"],
                             start_date=start_date,
                             due_date=due_date,
                             author=current_user)
            db.session.add(todo_item)
            db.session.commit()
            if len(request.form["todo_tag"]) > 0:
                todo_tag = request.form["todo_tag"].split(",")
                count = todo_tag.count("")
                for x in range (count):
                    todo_tag.remove("")

                db_tags = Tags.query.filter(Tags.user_id == current_user.id).all()
                db_tags = [x.tag for x in db_tags]
                all_tags = []
                for tag in todo_tag:
                    add_this_tag = True
                    for db_tag in db_tags:
                        if db_tag == tag:
                            add_this_tag = False
                            break
                    if add_this_tag:
                        all_tags.append(tag)

                for tag in all_tags:
                    db.session.add(Tags(tag=tag, author=current_user))
                    db.session.commit()
            return redirect(url_for("todo"))
        elif "filter_views" in request.form:
            session["filter_views"] = request.form["filter_views"]
            return redirect(url_for("todo"))
        elif "edit_task_form" in list(request.form.keys()):
            keys = list(request.form.keys())
            keys.remove("edit_task_form")
            char = keys[0].split("_")
            id = int(char[len(char)-1])
            task = ToDo.query.filter(ToDo.id == id).first()
            # title, body, start_date, due_date
            for key in keys:
                if "title" in key:
                    task.title = request.form[key]
                elif "body" in key:
                    task.body = request.form[key]
                elif "start_date" in key and len(request.form[key]) > 0:
                    start_date = request.form[key].split("-")
                    start_date = [int(d) for d in start_date]
                    start_date = datetime(start_date[0], start_date[1], start_date[2])
                    task.start_date = start_date
                elif "due_date" in key and len(request.form[key]) > 0:
                    due_date = request.form[key].split("-")
                    due_date = [int(d) for d in due_date]
                    due_date = datetime(due_date[0], due_date[1], due_date[2])
                    task.due_date = due_date
            db.session.commit()
            return redirect(url_for("todo"))

    user_todos = []
    if (session and "filter_views" in session and
        session["filter_views"] != "filter_date_added"):
        filter_view = session["filter_views"]
        user_todos = current_user.todo_items.all()
        # id, title, tag, body, start_date, due_date, completed, user_id
        if filter_view == "filter_due_date":
            todos_dated = []
            todos_dated_dict = {}
            todos_dated_counter = 0
            todos_undated = []
            for todo in user_todos:
                if todo.due_date:
                    todos_dated.append((todo.due_date, todos_dated_counter))
                    todos_dated_dict[todos_dated_counter] = todo
                    todos_dated_counter += 1
                else:
                    todos_undated.append(todo)
            # Sort by date
            todos_dated.sort()
            user_todos = []
            for todo in todos_dated:
                user_todos.append(todos_dated_dict[todo[1]])
            for todo in todos_undated:
                user_todos.append(todo)
        else:
            # filter_tags_number
            todos_tag = []
            todos_tag_counter = 0
            todos_tag_dict = {}
            for todo in user_todos:
                todos_tag.append((todo.tag.count(","), todos_tag_counter))
                todos_tag_dict[todos_tag_counter] = todo
                todos_tag_counter += 1
            todos_tag.sort()
            user_todos = []
            for todo in todos_tag:
                user_todos.append(todos_tag_dict[todo[1]])  
    else:
        user_todos = current_user.todo_items.all()

    todos = []
    for user_todo in user_todos:
        start_date = user_todo.start_date
        due_date = user_todo.due_date
        days_left = ""
        if start_date and due_date:
            today_date = datetime.now()
            if start_date <= today_date <= due_date:
                days_left = due_date-today_date
                if "days" in str(days_left) or "day" in str(days_left):
                    days_left = str(days_left)
                    days_left = days_left[:days_left.find(",")] + " left"
                else:
                    days_left = str(days_left)
                    days_left = days_left.split(":")
                    days_left = [float(x) for x in days_left]
                    hours = days_left[0]
                    minutes = days_left[1]
                    seconds = days_left[2]

                    if hours != 0.0:
                        days_left = str(hours) + " hour" + (hours != 1.0)*"s" + " left"
                    elif minutes != 0.0:
                        days_left = str(minutes) + " minutes" + (minutes !=1.0)*"s" + " left"
                    elif seconds != 0.0:
                        days_left = str(seconds) + " seconds" + (seconds !=1.0)*"s" + " left"
                    else:
                        days_left = ""
            if start_date:
               start_date = start_date.strftime("%d/%m/%Y")
        if due_date:
            due_date = due_date.strftime("%d/%m/%Y")
        todo_tag = []
        if len(user_todo.tag) > 0:
            todo_tag = user_todo.tag.split(",")
            count = todo_tag.count("")
            for x in range(count):
                todo_tag.remove("")
        todos.append({"Title": user_todo.title, "Body": user_todo.body,
                      "Tag": todo_tag, "Start date": start_date,
                      "Due date": due_date, "Days left": days_left,
                      "id": user_todo.id, "completed": user_todo.completed})
        user_tags = current_user.tag_items.all()
    tags = []
    for user_tag in user_tags:
        tags.append(user_tag.tag)

    if session and "filter_views" in session:
        filter_view = session["filter_views"]
        session.pop("filter_views")
        if filter_view == "filter_date_added":
            filter_view = "Sort by date added"
        elif filter_view == "filter_due_date":
            filter_view = "Sort by due date"
        else:
            # filter_tags_number
            filter_view = "Sort by number of tags"
    else:
        filter_view = ""
    return render_template("todo.html", todos=todos, todos_json=json.dumps(todos), tags=tags,
                            filter_view=filter_view, username=current_user.username)


