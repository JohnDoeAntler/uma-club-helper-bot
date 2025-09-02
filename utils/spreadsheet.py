from google.oauth2 import service_account
from googleapiclient.discovery import build

def init_google_credentials():
    global creds
    creds = service_account.Credentials.from_service_account_file(
        "service-account.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )

def init_google_sheets_client():
    global service
    service = build("sheets", "v4", credentials=creds)

def get_service():
    return service
