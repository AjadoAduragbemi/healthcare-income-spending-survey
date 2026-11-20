# Healthcare Income & Spending Survey (Flask + MongoDB)

A survey tool for collecting participants' income and spending data, ahead of a new healthcare product launch:

- A **Flask** web page collects each participant's age, gender, total income and expenses. Every expense category has a checkbox with an amount box.
- Responses are stored in **MongoDB**.
- A Python **`User`** class processes the data, and an export script loops through every response and writes a **CSV**.
- A **Jupyter notebook** loads the CSV, charts income by age and spending by gender, and exports the charts for a client PowerPoint.
- The app and database run locally in **Docker**.

## Files

| Path | Description |
| --- | --- |
| `app.py` | Flask app: the survey form (`/`), a thank-you page and a `/health` check |
| `templates/`, `static/` | HTML pages and styling for the form |
| `user.py` | The **`User`** class: validates form input, converts to and from MongoDB documents, and produces CSV rows |
| `export_to_csv.py` | Loops through every MongoDB response, builds a `User` for each and writes `survey_data.csv` |
| `seed_sample_data.py` | Adds clearly labelled **synthetic** responses so the analysis has data to chart |
| `analysis.ipynb` | Loads the CSV, produces the charts and findings, and exports the charts to `charts/` (saved with outputs) |
| `charts/` | Exported PNG charts for PowerPoint (16:9, 200 dpi) |
| `survey_data.csv` | Example export (121 responses, 120 synthetic) |
| `Dockerfile`, `docker-compose.yml` | Run the app (gunicorn) and MongoDB in containers |
| `requirements-app.txt` | Packages for the app container |
| `requirements.txt` | Packages for running the scripts and notebook on your machine |

## Requirements

- **Docker Desktop**, for the app and MongoDB.
- **Python 3.11+**, for the export script, seed script and notebook.

## How to run

### 1. Start the app and database

```bash
docker compose up --build -d
```

Open **<http://localhost:8080>** and fill in the survey.

- MongoDB runs alongside the app, and its data is kept in a Docker volume, so responses survive restarts.
- <http://localhost:8080/health> shows whether the app can reach the database and how many responses are stored.
- To stop: `docker compose down`. Add `-v` to also delete the stored responses.

### 2. Set up Python for the scripts and notebook

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. (Optional) Add synthetic sample data

```bash
python seed_sample_data.py              # adds 120 responses; --count changes the number
```

Synthetic responses are stored with `source = "synthetic"`, so they can always be told apart from real submissions. They're randomly generated for demonstration and are **not real participant data**.

### 4. Export the responses to CSV

```bash
python export_to_csv.py                 # writes survey_data.csv
```

The script loops through every MongoDB response, creates a `User` object for each, and writes one row per user.

- **Columns:** age, gender, total income, one column per expense category (0 if not ticked), total expenses, submission time and source.
- **Connection:** it connects to MongoDB at `localhost:27017`, which `docker-compose.yml` exposes to your machine only.

### 5. Analyse in Jupyter

```bash
python -m ipykernel install --user --name survey-analysis --display-name "Python (Survey analysis)"
jupyter lab
```

Open `analysis.ipynb`, select the **Python (Survey analysis)** kernel, and choose **Run → Run All Cells**. Set `INCLUDE_SYNTHETIC = False` at the top to analyse real submissions only.

## The survey form

- **About you:** age (18–100), gender (Female, Male, Non-binary, Prefer not to say), and total monthly income.
- **Monthly expenses:** a checkbox for each of utilities, entertainment, school fees, shopping and healthcare. Ticking a category enables its amount box.
- **Validation:** the `User` class checks every submission on the server. Age must be in range, numbers can't be negative, and every ticked category needs an amount. Errors are listed at the top of the form, and what was entered is kept.
- **Storage:** valid responses are saved to the `healthcare_survey.participants` collection in MongoDB, and the participant sees a thank-you page.

Example stored document:

```json
{
  "age": 34, "gender": "Female", "total_income": 4200,
  "expenses": {"utilities": 310.5, "healthcare": 150},
  "total_expenses": 460.5,
  "submitted_at": "2026-11-17T16:31:59Z",
  "source": "survey"
}
```

## Analysis and charts

The notebook answers the two client questions and exports a chart for each:

| Chart | Question it answers |
| --- | --- |
| `income_by_age_group.png` | **Which ages have the highest income?** Average monthly income by age group, with the top group highlighted. |
| `spending_share_by_gender.png` | **How is spending distributed across genders?** Each category's total spending split by gender. |
| `average_spend_by_gender.png` | The same question **per person**: average spend per participant by gender and category, since the genders differ in group size. |

With the included sample data, **45–54-year-olds have the highest average income**, and women account for over half of spending in every category, largely because they're the largest group. Every chart has a footnote stating how many responses are synthetic. Re-run the export and notebook once real responses are collected.

## Deployment

The app reads its database connection from the `MONGO_URI` environment variable, so it can point at any MongoDB, such as MongoDB Atlas, without code changes.
