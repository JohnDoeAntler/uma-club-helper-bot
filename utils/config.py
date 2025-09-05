import os
import base64
from dotenv import load_dotenv

load_dotenv()

def get_env():
    return os.getenv('ENV')

def get_bot_token():
    return os.getenv('DISCORD_CLIENT_TOKEN')

def get_client_id():
    return os.getenv('DISCORD_CLIENT_ID')

def get_database_url():
    return os.getenv('DATABASE_URL')

def init_env():
    BASE64_SERVICE_ACOUNT = os.getenv('FILE_SERVICE_ACCOUNT_JSON_BASE64')
    if BASE64_SERVICE_ACOUNT is not None:
        # create a new file
        with open('service-account.json', 'w+') as f:
            f.write(base64.b64decode(BASE64_SERVICE_ACOUNT).decode('utf-8'))
