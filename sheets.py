import os
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

def append_action(action: str, timestamp: datetime, duration: str = ""):
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
    """Find the most recent ‘Walk Start’ with empty Duration."""
    res = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:D"
    ).execute().get('values', [])
    # Skip header if present
    rows = [r for r in res if r[2] == "Walk Start" and (len(r) < 4 or r[3] == "")]
    if not rows:
        return None
    last = rows[-1]
    return {"date": last[0], "time": last[1]}

def update_duration(row_index: int, duration: str):
    """Update Duration column at given 1-based row_index."""
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!D{row_index}",
        valueInputOption="USER_ENTERED",
        body={"values": [[duration]]}
    ).execute()
