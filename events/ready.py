import discord
from utils.loader import sync_commands
from utils.db import init_db, engine, SessionLocal
from utils.discord import event, get_client

@event
async def on_ready():
    client = get_client()
    print(f'{client.user} has connected to Discord!')
    print(f'Bot ID: {client.user.id}')
    
    # Initialize database
    try:
        init_db()
        if engine and SessionLocal:
            print("Database: Connected successfully")
        else:
            print("Database: Connection failed")
    except Exception as e:
        print(f"Database: Connection failed - {e}")

    # Generate invite link
    permissions = discord.Permissions(
        send_messages=True,
        use_application_commands=True,
        read_message_history=True,
        manage_messages=True, # clear reactions
        embed_links=True
    )

    invite_link = discord.utils.oauth_url(
        client.user.id,
        permissions=permissions,
        scopes=('bot', 'applications.commands')
    )

    print(f'Invite link: {invite_link}')
    await sync_commands()
