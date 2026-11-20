"""
Add synthetic survey responses to MongoDB so the analysis has enough data to chart.

Every generated response is stored with source="synthetic", so it can always be told
apart from (or filtered out of) real responses submitted through the web form.
The values are randomly generated for demonstration and are NOT real participant data.

    python seed_sample_data.py              # adds 120 synthetic responses
    python seed_sample_data.py --count 50
"""

import argparse
import math
import os
import random
import sys
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from user import EXPENSE_CATEGORIES, User

DEFAULT_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DEFAULT_DB = os.environ.get("MONGO_DB", "healthcare_survey")
SEED = 42

GENDER_WEIGHTS = {"Female": 0.48, "Male": 0.46, "Non-binary": 0.04, "Prefer not to say": 0.02}
# For each category: chance a participant spends on it, and the share of income spent (min, max)
SPENDING_PROFILE = {
    "utilities":     (0.95, (0.06, 0.12)),
    "entertainment": (0.70, (0.03, 0.10)),
    "school_fees":   (0.35, (0.08, 0.20)),
    "shopping":      (0.85, (0.05, 0.15)),
    "healthcare":    (0.75, (0.03, 0.10)),
}


def synthetic_user(rng, now):
    """Generate one plausible, randomly generated participant."""
    age = int(min(75, max(18, rng.gauss(40, 13))))
    gender = rng.choices(list(GENDER_WEIGHTS), weights=GENDER_WEIGHTS.values())[0]

    # Monthly income rises with age to a peak in the late 40s, with random variation
    typical_income = 2200 + 4800 * math.exp(-((age - 48) / 18) ** 2)
    income = round(typical_income * rng.lognormvariate(0, 0.25), -1)

    expenses = {}
    for category, (chance, (low, high)) in SPENDING_PROFILE.items():
        if category == "school_fees" and not 25 <= age <= 60:
            chance /= 3                                   # School fees are less common outside these ages
        if rng.random() < chance:
            expenses[category] = round(income * rng.uniform(low, high), 2)

    submitted_at = now - timedelta(days=rng.uniform(0, 30))
    return User(age=age, gender=gender, total_income=income, expenses=expenses,
                submitted_at=submitted_at, source="synthetic")


def main():
    parser = argparse.ArgumentParser(description="Add synthetic survey responses to MongoDB.")
    parser.add_argument("--count", type=int, default=120, help="Number of responses to add")
    parser.add_argument("--uri", default=DEFAULT_URI, help="MongoDB connection string")
    parser.add_argument("--db", default=DEFAULT_DB, help="Database name")
    args = parser.parse_args()
    if args.count <= 0:
        sys.exit("--count must be a positive number")

    rng = random.Random(SEED)
    now = datetime.now(timezone.utc)
    documents = [synthetic_user(rng, now).to_document() for _ in range(args.count)]

    try:
        collection = MongoClient(args.uri, serverSelectionTimeoutMS=5000)[args.db]["participants"]
        collection.insert_many(documents)
    except PyMongoError as err:
        sys.exit(f"Could not write to MongoDB at {args.uri}. Is it running (docker compose up)?\n{err}")
    print(f"Added {args.count} synthetic responses (source='synthetic') to {args.db}.participants")


if __name__ == "__main__":
    main()
