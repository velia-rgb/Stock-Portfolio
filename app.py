'''imports modules
- flask allows us to use the python webframe application
- render_templates allows us to use .html pages
- url_for allows us to directly link  back to .html pages
'''
from flask import Flask, render_template, url_for, request, redirect, flash, session
from werkzeug.security import check_password_hash

from models import (
    init_db,
    create_user,
    get_user_by_username,
    get_portfolios_for_user,
    create_portfolio_db,
    get_portfolio,
    get_holdings_for_portfolio,
    get_transactions_for_portfolio,
    get_holding,
    upsert_holding,
    sell_holding,
    record_transaction,
    get_current_price,
    delete_portfolio_db,
    update_portfolio_name,
    update_portfolio_cash,
)

# instantiate flask

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"

init_db()

# we don't need to use session anymore, we use portfolio_id instead
def get_current_portfolio_id():
    user_id = session.get("user_id")
    if not user_id:
        return None
    current_pid = session.get("current_portfolio_id")
    if current_pid:
        portfolio = get_portfolio(current_pid)
        if portfolio and portfolio.user_id == user_id:
            return current_pid
    # Fallback to first portfolio
    portfolios = get_portfolios_for_user(user_id)
    if portfolios:
        session["current_portfolio_id"] = portfolios[0].id
        return portfolios[0].id
    return None


@app.context_processor
def inject_login_state():
    return {"logged_in": session.get("user_id") is not None}


def login_required():
    return session.get("user_id") is not None


def current_user_id():
    return session.get("user_id")


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
            # Set current portfolio to first one
            portfolios = get_portfolios_for_user(user.id)
            if portfolios:
                session["current_portfolio_id"] = portfolios[0].id
            flash("Logged in successfully", "success")
            return redirect(url_for("portfolio_list"))

        flash("Invalid username or password", "error")
        return redirect(url_for("login"))

    return render_template("login.html", title="Login")

# ROUTE: portfolio_list page
@app.route("/portfolio_list", methods=["GET"])
def portfolio_list():
    if "user_id" not in session:
        return redirect(url_for("login"))

    portfolios = get_portfolios_for_user(session["user_id"])

    return render_template(
        "portfolio_list.html",
        portfolios=portfolios
    )

# ROUTE: delete one portfolio
@app.route("/portfolio/<int:portfolio_id>/delete", methods=["POST"])
def delete_portfolio(portfolio_id):
    if not login_required():
        flash("Please log in first", "error")
        return redirect(url_for("login"))

    portfolio_obj = get_portfolio(portfolio_id)
    if not portfolio_obj or portfolio_obj.user_id != session["user_id"]:
        flash("Portfolio not found", "error")
        return redirect(url_for("portfolio_list"))

    if delete_portfolio_db(portfolio_id):
        if session.get("current_portfolio_id") == portfolio_id:
            remaining = get_portfolios_for_user(session["user_id"])
            if remaining:
                session["current_portfolio_id"] = remaining[0].id
            else:
                session.pop("current_portfolio_id", None)

        flash("Portfolio deleted", "success")
    else:
        flash("Could not delete portfolio", "error")

    return redirect(url_for("portfolio_list"))

# ROUTE: Edit function
@app.route("/portfolio/<int:portfolio_id>/edit", methods=["GET", "POST"])
def edit_portfolio(portfolio_id):
    if not login_required():
        flash("Please log in first", "error")
        return redirect(url_for("login"))

    portfolio_obj = get_portfolio(portfolio_id)
    user_id = current_user_id()
    existing_portfolios = get_portfolios_for_user(user_id)

    if not portfolio_obj or portfolio_obj.user_id != session["user_id"]:
        flash("Portfolio not found", "error")
        return redirect(url_for("portfolio_list"))

    if request.method == "POST":
        new_name = request.form.get("portfolio-name", "").strip()
        cash_str = request.form.get("cash-amount", "").strip()

        if not new_name:
            flash("Portfolio name cannot be empty", "error")
            return redirect(url_for("edit_portfolio", portfolio_id=portfolio_id))

        try:
            new_cash = float(cash_str)
        except ValueError:
            flash("Cash amount must be a number", "error")
            return redirect(url_for("edit_portfolio", portfolio_id=portfolio_id))

        if new_cash < 0:
            flash("Cash amount cannot be negative", "error")
            return redirect(url_for("edit_portfolio", portfolio_id=portfolio_id))

        update_portfolio_name(portfolio_id, new_name)
        update_portfolio_cash(portfolio_id, new_cash - portfolio_obj.cash)

        flash("Portfolio updated", "success")
        return redirect(url_for("portfolio_list"))

    return render_template(
        "edit_portfolio.html",
        title="Edit Portfolio",
        portfolio=portfolio_obj
    )

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
        user = get_user_by_username(username)
        # create_portfolio_db(user.id, f"{username}'s Portfolio", 10000.0)
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html", title="Sign Up")

# ROUTE: GET PORTFOLIO PAGE
@app.route("/portfolio/<int:portfolio_id>", methods=["GET"])
def portfolio(portfolio_id):
    if not login_required():
        flash("Please log in first", "error")
        return redirect(url_for("login"))

    # portfolio_id = get_current_portfolio_id()
    if not portfolio_id:
        flash("No portfolio found", "error")
        return redirect(url_for("index"))

    portfolio_obj = get_portfolio(portfolio_id)
    if not portfolio_obj or portfolio_obj.user_id != session["user_id"]:
        flash("Portfolio not found", "error")
        return redirect(url_for("portfolio_list"))

    holdings = get_holdings_for_portfolio(portfolio_id)
    transactions = get_transactions_for_portfolio(portfolio_id)
    
    # Fetch current prices and calculate P/L for holdings
    holdings_data = []
    total_value = 0
    total_cost = 0
    for holding in holdings:
        current_price = get_current_price(holding.symbol)
        if current_price:
            current_value = current_price * holding.shares
            cost_basis = holding.avg_price * holding.shares
            pl = current_value - cost_basis
            holdings_data.append({
                'symbol': holding.symbol,
                'shares': holding.shares,
                'avg_price': holding.avg_price,
                'current_price': current_price,
                'current_value': current_value,
                'pl': pl
            })
            total_value += current_value
            total_cost += cost_basis
        else:
            holdings_data.append({
                'symbol': holding.symbol,
                'shares': holding.shares,
                'avg_price': holding.avg_price,
                'current_price': None,
                'current_value': None,
                'pl': None
            })

    realized_pl = sum(
        (txn.price - txn.cost_basis) * txn.shares
        for txn in transactions
        if txn.type == "SELL" and txn.cost_basis is not None
    )
    unrealized_pl = total_value - total_cost
    total_pl = realized_pl + unrealized_pl

    return render_template(
        "portfolio.html",
        title="Portfolio",
        holdings=holdings_data,
        transactions=transactions,
        portfolio=portfolio_obj,
        total_value=total_value,
        total_pl=total_pl,
    )


# ROUTE: BUY STOCKS
@app.route("/portfolio/<int:portfolio_id>/buy", methods=["GET", "POST"])
def buy(portfolio_id):
    if not login_required():
        flash("Please log in first", "error")
        return redirect(url_for("login"))

    # portfolio_id = get_current_portfolio_id()
    portfolio_obj = get_portfolio(portfolio_id)
    if not portfolio_obj or portfolio_obj.user_id != session["user_id"]:
        flash("No portfolio found", "error")
        return redirect(url_for("portfolio_list"))
    # if not portfolio_id:
    #     flash("No portfolio found", "error")
    #     return redirect(url_for("index"))

    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip()
        shares = request.form.get("shares", "")
        price = request.form.get("price", "")

        try:
            shares = int(shares)
            price = float(price)
        except ValueError:
            flash("Shares must be a whole number and price must be a number.", "error")
            return redirect(url_for("buy", portfolio_id=portfolio_id))

        if not symbol or shares <= 0 or price <= 0:
            flash("Enter a valid symbol, positive shares, and positive price.", "error")
            return redirect(url_for("buy", portfolio_id=portfolio_id))

        total_cost = shares * price
        if total_cost > portfolio_obj.cash:
            flash("Insufficient cash to buy the requested shares.", "error")
            return redirect(url_for("buy", portfolio_id=portfolio_id))

        upsert_holding(portfolio_id, symbol, shares, price)
        record_transaction(portfolio_id, symbol, shares, price, "BUY", cost_basis=price)
        update_portfolio_cash(portfolio_id, -total_cost)
        flash(f"Bought {shares} shares of {symbol.upper()} at ${price:.2f}", "success")
        return redirect(url_for("portfolio", portfolio_id=portfolio_id))

    return render_template("buy.html", title="Buy Stocks", portfolio=portfolio_obj)


# ROUTE: SELL STOCKS
@app.route("/portfolio/<int:portfolio_id>/sell", methods=["GET", "POST"])
def sell(portfolio_id):
    if not login_required():
        flash("Please log in first", "error")
        return redirect(url_for("login"))

    # portfolio_id = get_current_portfolio_id()
    portfolio_obj = get_portfolio(portfolio_id)
    if not portfolio_obj or portfolio_obj.user_id != session["user_id"]:
        flash("No portfolio found", "error")
        return redirect(url_for("portfolio_list"))
    

    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip()
        shares = request.form.get("shares", "")
        price = request.form.get("price", "")

        try:
            shares = int(shares)
            price = float(price)
        except ValueError:
            flash("Shares must be a whole number and price must be a number.", "error")
            return redirect(url_for("sell",portfolio_id=portfolio_id))

        if not symbol or shares <= 0 or price <= 0:
            flash("Enter a valid symbol, positive shares, and positive price.", "error")
            return redirect(url_for("sell",portfolio_id=portfolio_id))

        holding = get_holding(portfolio_id, symbol)
        if not holding or shares > holding.shares:
            flash("Not enough shares to sell.", "error")
            return redirect(url_for("sell",portfolio_id=portfolio_id))

        cost_basis = holding.avg_price
        proceeds = shares * price
        sell_holding(portfolio_id, symbol, shares)
        update_portfolio_cash(portfolio_id, proceeds)
        record_transaction(portfolio_id, symbol, shares, price, "SELL", cost_basis=cost_basis)
        flash(f"Sold {shares} shares of {symbol.upper()} at ${price:.2f}", "success")
        return redirect(url_for("portfolio",portfolio_id=portfolio_id))

    return render_template("sell.html", title="Sell Stocks",portfolio=portfolio_obj)


# ROUTE: GET CREATE PORTFOLIO PAGE
@app.route("/create_portfolio", methods=["GET", "POST"])
def create_portfolio():
    if not login_required():
        flash("Please log in first", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("portfolio-name", "").strip()
        cash_str = request.form.get("cash-amount", "").strip()

        if not name:
            flash("Portfolio name is required", "error")
            return redirect(url_for("create_portfolio"))

        try:
            cash = float(cash_str) if cash_str else 10000.0
        except ValueError:
            flash("Cash amount must be a number", "error")
            return redirect(url_for("create_portfolio"))

        if cash < 0:
            flash("Cash amount cannot be negative", "error")
            return redirect(url_for("create_portfolio"))

        user_id = current_user_id()
        existing_portfolios = get_portfolios_for_user(user_id)
        if any(p.name.lower() == name.lower() for p in existing_portfolios):
            flash("Portfolio name already exists", "error")
            return render_template("create_portfolio.html", title="Create Portfolio")

        portfolio = create_portfolio_db(user_id, name, cash)
        session["current_portfolio_id"] = portfolio.id
        flash(f"Portfolio '{name}' created with ${cash:.2f} cash", "success")
        return redirect(url_for("portfolio_list"))

    return render_template("create_portfolio.html", title="Create_Portfolio")
    

# ROUTE: LOGOUT
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have been logged out", "success")
    return redirect(url_for("login"))

# ROUTE: GET CURRENT PRICE
@app.route("/get_price/<symbol>")
def get_price(symbol):
    from flask import jsonify
    price = get_current_price(symbol.upper())
    if price:
        return jsonify({"price": price})
    else:
        return jsonify({"error": "Unable to fetch price"}), 404

# start app
if __name__ == "__main__":
    app.run(debug=True)