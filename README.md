# Uma Club Helper Bot

A Discord bot for managing Uma Musume club information through video processing and automated spreadsheet logging.

## Demonstration

## Features

- **Video Processing**: Upload club member list videos to automatically extract player data using opencv and PaddleOCR
- **Spreadsheet Integration**: Automatically log member data to Google Sheets with timestamps

## Setup

1. Copy `example.env` to `.env` and configure:
   - Discord bot credentials
   - PostgreSQL database URL
   - Google Sheets API credentials

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Commands

All commands require administrator permissions.

### Club Management

- `/create-club <name>` - Create a new club
- `/list-clubs` - List all clubs in this server
- `/delete-club <name>` - Delete a club

### Channel Configuration

- `/setup-channel-club-records` - Toggle current channel as video upload destination for a club

### Spreadsheet Integration

- `/enable-spreadsheet-logging <spreadsheet_id>` - Enable automatic Google Sheets logging for a club
- `/disable-spreadsheet-logging` - Disable spreadsheet logging for a club

## Usage

Upload a video recording of your Uma Musume club member list to a configured channel. The bot will automatically process the video, extract member information (names, fan counts, roles, last login), and update the associated Google Sheet with timestamped data.
