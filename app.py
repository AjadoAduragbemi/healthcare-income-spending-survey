"""
Healthcare income-spending survey: Flask web app.

Shows a survey form, validates it with the User class and stores each response in MongoDB.
The MongoDB connection comes from the MONGO_URI environment variable.

Run with Docker:   docker compose up --build      (then open http://localhost:8080)
"""

import os

from flask import Flask, redirect, render_template, request, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from user import EXPENSE_CATEGORIES, GENDERS, MAX_AGE, MIN_AGE, User, ValidationError

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "healthcare_survey")

app = Flask(__name__)
participants = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[MONGO_DB]["participants"]


@app.route("/", methods=["GET", "POST"])
def survey():
    """Show the survey form; on submit, validate and save the response."""
    errors, status = [], 200
    if request.method == "POST":
        try:
            user = User.from_form(request.form)
            participants.insert_one(user.to_document())
            return redirect(url_for("thank_you"))          # Post/Redirect/Get: no resubmit on refresh
        except ValidationError as err:
            errors, status = err.messages, 400
        except PyMongoError:
            app.logger.exception("Could not save survey response")
            errors, status = ["Your response could not be saved right now. Please try again shortly."], 503

    return render_template("survey.html", form=request.form, errors=errors,
                           categories=EXPENSE_CATEGORIES, genders=GENDERS,
                           min_age=MIN_AGE, max_age=MAX_AGE), status


@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")


@app.route("/health")
def health():
    """Report whether the app can reach MongoDB."""
    try:
        participants.database.client.admin.command("ping")
        return {"status": "ok", "responses": participants.count_documents({})}
    except PyMongoError:
        return {"status": "database unavailable"}, 503


if __name__ == "__main__":
    app.run(debug=True, port=8080)
