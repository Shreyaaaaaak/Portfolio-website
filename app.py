from flask import Flask, flash, redirect, render_template, request, url_for

from data import (
    CATEGORY_CHOICES,
    create_habit,
    delete_habit,
    ensure_database,
    get_dashboard_data,
    mark_habit_complete,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = "habit-tracker-dev"


ensure_database()


@app.get("/")
def home():
    dashboard = get_dashboard_data()
    return render_template(
        "index.html",
        dashboard=dashboard,
        category_choices=CATEGORY_CHOICES,
    )


@app.post("/habits")
def create_habit_view():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    target_days = request.form.get("target_days", "").strip()

    try:
        create_habit(name=name, category=category, target_days=target_days)
    except ValueError as error:
        flash(str(error), "error")
    else:
        flash(f'"{name}" is ready to track.', "success")

    return redirect(url_for("home"))


@app.post("/habits/<int:habit_id>/check-in")
def check_in_habit(habit_id: int):
    created = mark_habit_complete(habit_id)

    if created:
        flash("Check-in saved for today.", "success")
    else:
        flash("That habit is already checked in today.", "info")

    return redirect(url_for("home"))


@app.post("/habits/<int:habit_id>/delete")
def delete_habit_view(habit_id: int):
    delete_habit(habit_id)
    flash("Habit removed.", "info")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
