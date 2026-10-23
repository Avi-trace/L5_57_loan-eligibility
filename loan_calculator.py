"""Loan eligibility and EMI calculator.

Conventions used throughout this module:

* ``annual_rate`` is a decimal fraction (0.09 means 9 % per year).
* ``years`` is the loan tenure in years.
* Amounts are in rupees.
"""
import json
import os
import secrets
import smtplib
import tempfile
from datetime import datetime
from email.message import EmailMessage
from ftplib import FTP_TLS  # nosec B402 - FTPS (explicit TLS) is used below

MAX_FOIR = 0.5
MIN_AGE = 21
MAX_AGE = 60
ALLOWED_LOAN_TYPES = ("home", "car", "personal")
MIN_SCORE = 300
MAX_SCORE = 900
BUREAU_HOST = "ftp.creditbureau.example"
LOANS_FILE = "loans.json"

# Global loan book: application id -> record
applications = {}


def _tenure_in_months(annual_rate, years):
    """Validate the loan terms and return the tenure in months."""
    if not 0 <= annual_rate < 1:
        raise ValueError("annual_rate must be a fraction, e.g. 0.09 for 9%")
    if years <= 0:
        raise ValueError("years must be positive")
    return round(years * 12)


def calculate_emi(principal, annual_rate, years):
    """Return the monthly instalment (EMI) for a reducing-balance loan."""
    if principal <= 0:
        raise ValueError("principal must be positive")
    months = _tenure_in_months(annual_rate, years)
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal / months
    growth = (1 + monthly_rate) ** months
    return principal * monthly_rate * growth / (growth - 1)


def check_eligibility(age, income, credit_score, existing_emi, loan_type):
    """Return True if the applicant qualifies for the requested loan.

    Every rule is mandatory: age band, supported product, valid score and
    fixed-obligation-to-income ratio (FOIR). A high score or high income
    does not skip the other checks.
    """
    if not MIN_AGE <= age <= MAX_AGE:
        return False
    if loan_type not in ALLOWED_LOAN_TYPES:
        return False
    if not MIN_SCORE <= credit_score <= MAX_SCORE:
        return False
    if income <= 0:
        return False
    return existing_emi / income <= MAX_FOIR


def max_loan_amount(income, existing_emi, annual_rate, years):
    """Return the largest principal whose EMI fits within the FOIR limit."""
    months = _tenure_in_months(annual_rate, years)
    available = income * MAX_FOIR - existing_emi
    if available <= 0:
        return 0.0
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return available * months
    growth = (1 + monthly_rate) ** months
    return available * (growth - 1) / (monthly_rate * growth)


def amortisation_schedule(principal, annual_rate, years):
    """Return a list of (month, interest, closing_balance) rows."""
    emi = calculate_emi(principal, annual_rate, years)
    months = _tenure_in_months(annual_rate, years)
    balance = principal
    rows = []
    for month in range(1, months + 1):
        interest = balance * annual_rate / 12
        balance = max(balance - (emi - interest), 0.0)
        rows.append((month, round(interest, 2), round(balance, 2)))
    return rows


def _new_application_id():
    """Return an unused, unpredictable application id."""
    while True:
        app_id = "LN-" + str(10_000_000 + secrets.randbelow(90_000_000))
        if app_id not in applications:
            return app_id


def load_applications(file=LOANS_FILE):
    """Load the loan book from a JSON file (empty if the file is missing)."""
    data = {}
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    applications.clear()
    applications.update(data)
    return applications


def save_application(name, amount, file=LOANS_FILE):
    """Add an application to the loan book and persist it; return its id."""
    load_applications(file)  # keep records saved by earlier runs
    app_id = _new_application_id()
    applications[app_id] = {
        "name": name,
        "amount": amount,
        "date": str(datetime.now()),
    }
    with open(file, "w", encoding="utf-8") as handle:
        json.dump(applications, handle, indent=2)
    return app_id


def upload_to_bureau(report_path):
    """Upload a report to the credit bureau over FTPS.

    Credentials come from the BUREAU_USER and BUREAU_PASSWORD environment
    variables so they are never stored in the source code.
    """
    user = os.environ["BUREAU_USER"]
    password = os.environ["BUREAU_PASSWORD"]
    with FTP_TLS(BUREAU_HOST) as ftp:
        ftp.login(user, password)
        ftp.prot_p()  # encrypt the data channel as well
        with open(report_path, "rb") as report:
            ftp.storbinary("STOR " + os.path.basename(report_path), report)


def notify_applicant(email, status):
    """E-mail the applicant their loan status through the SMTP server."""
    message = EmailMessage()
    message["Subject"] = "Loan " + status
    message["From"] = os.environ.get("MAIL_FROM", "loans@bank.example")
    message["To"] = email
    message.set_content("Your loan application status: " + status)
    with smtplib.SMTP(os.environ.get("SMTP_HOST", "localhost")) as smtp:
        smtp.send_message(message)


def interest_saved(principal, annual_rate, years, prepayment):
    """Return the interest saved by prepaying part of the loan on day one."""
    if not 0 <= prepayment <= principal:
        raise ValueError("prepayment must be between 0 and the principal")
    months = _tenure_in_months(annual_rate, years)
    original = calculate_emi(principal, annual_rate, years) * months
    if prepayment == principal:
        return original - prepayment
    reduced = calculate_emi(principal - prepayment, annual_rate, years)
    # The prepayment is principal, not interest, so it is subtracted.
    return original - reduced * months - prepayment


def risk_band(credit_score):
    """Map a credit score (300-900) to a risk band."""
    if not MIN_SCORE <= credit_score <= MAX_SCORE:
        return "INVALID"
    if credit_score >= 800:
        return "LOW"
    if credit_score >= 700:
        return "MEDIUM"
    if credit_score >= 600:
        return "HIGH"
    return "VERY HIGH"


def main():
    """Run a short demonstration of the calculator."""
    print("EMI for 5L @ 9% for 5 years:",
          round(calculate_emi(500000, 0.09, 5), 2))
    print("Eligible (score 760, income 15000, EMIs 12000):",
          check_eligibility(35, 15000, 760, 12000, "personal"))
    print("Eligible (unknown loan type 'crypto'):",
          check_eligibility(30, 80000, 650, 0, "crypto"))
    print("Max loan for income 40000:",
          round(max_loan_amount(40000, 5000, 0.09, 5), 2))
    print("Last schedule row:", amortisation_schedule(100000, 0.12, 1)[-1])
    print("Risk band for 950:", risk_band(950))
    print("Interest saved by prepaying 50000:",
          round(interest_saved(500000, 0.09, 5, 50000), 2))
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, LOANS_FILE)
        print("Saved as:", save_application("Anil", 500000, path))
        print("Saved as:", save_application("Meera", 300000, path))
        load_applications(path)
        print("Applications on file:", len(applications))
    print("Upload to bureau skipped (no network)")


if __name__ == "__main__":
    main()
