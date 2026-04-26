# Momentum Habit Tracker

A compact Flask habit tracker with:

- weekly targets
- one-click daily check-ins
- current and longest streaks
- a simple dashboard with progress cards
- SQLite storage with no external database setup

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Project structure

- `app.py` contains the Flask routes.
- `data.py` handles SQLite storage and streak calculations.
- `templates/index.html` contains the page template.
- `static/style.css` contains the visual design.
- `data/habits.db` is created automatically on first run.

## Main actions

- Add a habit with a category and weekly target.
- Check a habit in once per day.
- Delete a habit when you no longer want to track it.

## Notes

- The app prevents duplicate check-ins for the same habit on the same day.
- SQLite is built into Python, so only Flask is required as a dependency.
