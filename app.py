'''imports modules
- flask allows us to use the python webframe application
- render_templates allows us to use .html pages
- url_for allows us to directly link  back to .html pages
'''
from flask import Flask, render_template, url_for, request, redirect, flash, session
from werkzeug.security import check_password_hash

from models import init_db, create_user, get_user_by_username

# instantiate flask

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"

# ROUTE: GET INDEX PAGE 
@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
def index():
    return render_template("index.html")

# ROUTE: GET ABOUT PAGE
@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html", title="About")

# ROUTE: GET CONTACT PAGE
@app.route("/contact", methods=["GET"])
def contact():
    return render_template("contact.html", title="Contact")

# ROUTE: LOGIN PAGE
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter both username and password", "error")
            return redirect(url_for("login"))

        user = get_user_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash("Logged in successfully", "success")
            return redirect(url_for("portfolio"))

        flash("Invalid username or password", "error")
        return redirect(url_for("login"))

    return render_template("login.html", title="Login")

# ROUTE: SIGNUP PAGE
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            flash("Username and password are required", "error")
            return redirect(url_for("signup"))

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("signup"))

        if get_user_by_username(username):
            flash("That username is already taken", "error")
            return redirect(url_for("signup"))

        create_user(username, password)
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html", title="Sign Up")

# ROUTE: GET PORTFOLIO PAGE
@app.route("/portfolio", methods=["GET"])
def portfolio():
    return render_template("portfolio.html", title="Portfolio")

# ROUTE: GET CREATE PORTFOLIO PAGE
@app.route("/create_portfolio", methods=["GET"])
def create_portfolio():
    return render_template("create_portfolio.html", title="Create_Portfolio")
# start app
if __name__ == "__main__":
    app.run(debug=True)