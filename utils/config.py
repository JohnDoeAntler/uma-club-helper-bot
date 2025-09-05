import os
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
