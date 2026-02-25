"""One-time Google Calendar OAuth2 token setup.

Run this script locally to complete the OAuth flow and generate token.json.
The token file is then used by the deployed server for calendar access.

Usage:
    python -m scripts.setup_calendar

Prerequisites:
    1. Create a Google Cloud project and enable Calendar API
    2. Create OAuth2 Desktop App credentials
    3. Download credentials.json to the project root
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
]
TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token.json")
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")


def main():
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"Error: {CREDENTIALS_PATH} not found.")
        print("Download OAuth2 Desktop App credentials from Google Cloud Console.")
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        print(f"Existing token found at {TOKEN_PATH}")
        # Check if token is missing the gmail.readonly scope
        if creds and creds.scopes:
            has_gmail = any("gmail.readonly" in s for s in creds.scopes)
            has_readonly_cal = any("calendar.readonly" in s for s in creds.scopes) and not any("auth/calendar" == s.split("/")[-1] for s in creds.scopes)
            if not has_gmail or has_readonly_cal:
                print("Token missing required scope(s) — deleting to re-auth with all scopes.")
                os.remove(TOKEN_PATH)
                creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            creds.refresh(Request())
        else:
            print("Starting OAuth2 flow — a browser window will open.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print(f"Token saved to {TOKEN_PATH}")
    else:
        print("Token is still valid.")

    # Verify access
    service = build("calendar", "v3", credentials=creds)
    calendars = service.calendarList().list().execute()
    print(f"\nAccess verified. Found {len(calendars.get('items', []))} calendars:")
    for cal in calendars.get("items", []):
        print(f"  - {cal['summary']} ({cal['id']})")

    print(f"\nSetup complete. Copy {TOKEN_PATH} to your deployment environment.")
    print("Note: Tokens in testing mode expire every 7 days. Re-run this script to refresh.")


if __name__ == "__main__":
    main()
