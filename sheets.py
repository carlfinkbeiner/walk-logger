import os
import json
import base64
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Scopes and Sheet configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")

# Load credentials either from a base64-encoded env var or from a file path
_creds_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
if _creds_env:
    _creds_info = json.loads(base64.b64decode(_creds_env))
    creds = service_account.Credentials.from_service_account_info(
        _creds_info,
        scopes=SCOPES
    )
else:
    _service_account_file = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH")
    creds = service_account.Credentials.from_service_account_file(
        _service_account_file,
        scopes=SCOPES
    )

# Build the Sheets service
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

def append_action(action: str, timestamp: datetime, duration: str = ""):
    """
    Append a new action row to the sheet.
    """
    date_str = timestamp.strftime("%m/%d/%Y")
    time_str = timestamp.strftime("%H:%M")
    row = [date_str, time_str, action, duration]
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:D",
        valueInputOption="USER_ENTERED",
        body={"values": [row]}
    ).execute()


def find_last_start_unmatched() -> dict | None:
    """
    Find the most recent 'Walk Start' entry without a duration.
    Returns a dict with 'date' and 'time', or None if not found.
    """
    res = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:D"
    ).execute().get('values', [])

    # Filter for Walk Start rows where Duration is blank
    rows = [r for r in res if r[2] == "Walk Start" and (len(r) < 4 or r[3] == "")]
    if not rows:
        return None
    last = rows[-1]
    return {"date": last[0], "time": last[1]}


def update_duration(row_index: int, duration: str):
    """
    Update the Duration column for a specific 1-based row index.
    """
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!D{row_index}",
        valueInputOption="USER_ENTERED",
        body={"values": [[duration]]}
    ).execute()
