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

        if not new_name:
            flash("Portfolio name cannot be empty", "error")
            return redirect(url_for("edit_portfolio", portfolio_id=portfolio_id))
        
        if any(p.name.lower() == new_name.lower() for p in existing_portfolios):
            flash("Portfolio name already exists", "error")
            return render_template("edit_portfolio.html", title="Create Portfolio")

        update_portfolio_name(portfolio_id, new_name)

        flash("Portfolio name updated", "success")
        return redirect(url_for("portfolio_list"))

    return render_template(
        "edit_portfolio.html",
        title="Edit Portfolio",
        portfolio=portfolio_obj
    )