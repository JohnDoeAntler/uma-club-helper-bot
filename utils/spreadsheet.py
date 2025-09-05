from google.oauth2 import service_account
from googleapiclient.discovery import build

_service = None

def init_google_sheets_client():
    global _service
    creds = service_account.Credentials.from_service_account_file(
        "service-account.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    _service = build("sheets", "v4", credentials=creds)

def get_service():
    return _service
