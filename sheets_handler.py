"""
sheets_handler.py -- Google Sheets integration for AI Workflow Auditor.

Works in TWO modes:
  LOCAL:  reads credentials.json file (for running on your own PC)
  CLOUD:  reads credentials from Streamlit secrets (for Streamlit Cloud deployment)

LOCAL SETUP (one-time):
  1. Place credentials.json in this folder (see SETUP.md)
  2. Share your Google Sheet with the service account email

CLOUD SETUP:
  1. In Streamlit Cloud dashboard → your app → Settings → Secrets
  2. Paste the [gcp_service_account] section from secrets.toml.example
"""

import os
import json
from datetime import datetime
from typing import Tuple

CREDS_FILE  = os.path.join(os.path.dirname(__file__), "credentials.json")
SHEET_NAME  = os.getenv("GOOGLE_SHEET_NAME", "AI Workflow Auditor Leads")

HEADERS = [
    "Timestamp", "Name", "Email", "Role", "Industry",
    "Total Hours/Week", "Time Saved/Week", "Efficiency Gain %",
    "Automation Score", "Source"
]


def is_configured() -> bool:
    """True if credentials.json exists OR Streamlit cloud secrets are present."""
    if os.path.exists(CREDS_FILE) and os.path.getsize(CREDS_FILE) > 10:
        return True
    try:
        import streamlit as st
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


def _get_credentials():
    """Return Google credentials from file or Streamlit secrets."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        raise ImportError("Run: pip install gspread google-auth")

    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    # Mode 1: local credentials.json file
    if os.path.exists(CREDS_FILE) and os.path.getsize(CREDS_FILE) > 10:
        return Credentials.from_service_account_file(CREDS_FILE, scopes=scopes)

    # Mode 2: Streamlit Cloud secrets
    try:
        import streamlit as st
        info = dict(st.secrets["gcp_service_account"])
        return Credentials.from_service_account_info(info, scopes=scopes)
    except Exception as e:
        raise FileNotFoundError(f"No credentials found locally or in Streamlit secrets: {e}")


def _get_sheet():
    """Initialise gspread client and return the first worksheet."""
    import gspread

    creds  = _get_credentials()
    client = gspread.authorize(creds)

    # Read sheet name from Streamlit secrets if available
    sheet_name = SHEET_NAME
    try:
        import streamlit as st
        sheet_name = st.secrets.get("GOOGLE_SHEET_NAME", SHEET_NAME)
    except Exception:
        pass

    try:
        sheet = client.open(sheet_name).sheet1
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(sheet_name)
        sheet = spreadsheet.sheet1

    existing = sheet.get_all_values()
    if not existing or not existing[0] or existing[0][0] != "Timestamp":
        sheet.insert_row(HEADERS, index=1)

    return sheet


def save_lead(
    name: str = "", email: str = "", role: str = "",
    industry: str = "", total_hours: float = 0.0,
    time_saved: float = 0.0, efficiency: float = 0.0,
    auto_score: int = 0,
) -> Tuple[bool, str]:
    if not email and not name:
        return False, "No contact details provided"

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        name.strip()    or "Anonymous",
        email.strip()   or "Not provided",
        role.strip()    or "Not specified",
        industry.strip() or "Not specified",
        f"{total_hours:.1f}h",
        f"{time_saved:.1f}h",
        f"{efficiency:.1f}%",
        f"{auto_score}/100",
        "AI Workflow Auditor",
    ]

    try:
        sheet = _get_sheet()
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True, "Saved to Google Sheet"
    except ImportError as e:
        return False, f"Missing package: {e}"
    except FileNotFoundError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Google Sheets error: {type(e).__name__}: {e}"


def get_all_leads() -> list:
    try:
        sheet = _get_sheet()
        return sheet.get_all_records()
    except Exception:
        return []
