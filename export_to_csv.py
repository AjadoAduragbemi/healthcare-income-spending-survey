"""
Export every survey response from MongoDB to a CSV file.

Loops through the stored responses, turns each one into a User object and writes
one CSV row per User. Run after collecting responses (MongoDB must be running):

    python export_to_csv.py                      # writes survey_data.csv
    python export_to_csv.py --output my.csv
"""

import argparse
import csv
import os
import sys

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from user import User

DEFAULT_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DEFAULT_DB = os.environ.get("MONGO_DB", "healthcare_survey")


def load_users(collection):
    """Loop through the stored responses and return them as User objects, oldest first."""
    users = []
    for document in collection.find().sort("submitted_at", 1):
        users.append(User.from_document(document))
    return users


def write_csv(users, path):
    """Write one row per User to a CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=User.CSV_FIELDS)
        writer.writeheader()
        for user in users:
            writer.writerow(user.to_csv_row())


def main():
    parser = argparse.ArgumentParser(description="Export survey responses from MongoDB to CSV.")
    parser.add_argument("--uri", default=DEFAULT_URI, help="MongoDB connection string")
    parser.add_argument("--db", default=DEFAULT_DB, help="Database name")
    parser.add_argument("--output", default="survey_data.csv", help="CSV file to write")
    args = parser.parse_args()

    try:
        collection = MongoClient(args.uri, serverSelectionTimeoutMS=5000)[args.db]["participants"]
        users = load_users(collection)
    except PyMongoError as err:
        sys.exit(f"Could not read from MongoDB at {args.uri}. Is it running (docker compose up)?\n{err}")

    if not users:
        sys.exit("No survey responses found yet. Submit the form or run seed_sample_data.py first.")

    try:
        write_csv(users, args.output)
    except OSError as err:
        sys.exit(f"Could not write {args.output}: {err}")

    synthetic = sum(user.source == "synthetic" for user in users)
    print(f"Exported {len(users)} responses to {args.output} "
          f"({len(users) - synthetic} from the survey form, {synthetic} synthetic)")


if __name__ == "__main__":
    main()
