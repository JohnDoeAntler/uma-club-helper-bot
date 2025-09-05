from utils.opencv import init_paddleocr
from utils.config import get_bot_token
from utils.discord import get_client, init_client, init_command_tree
from utils.loader import auto_load_commands, auto_load_events
from utils.spreadsheet import init_google_credentials, init_google_sheets_client

def main():
    try:
        # initialize external services
        init_paddleocr()
        init_google_credentials()
        init_google_sheets_client()

        # initialize bot
        init_client()
        init_command_tree()
        auto_load_events()
        auto_load_commands()

        # start the bot
        client = get_client()
        token = get_bot_token()
        client.run(token)

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please make sure to set up your .env file with the required environment variables.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
