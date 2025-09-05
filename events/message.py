import discord
from utils.db import SessionLocal, ChannelConfig, Club
from .channel_listeners.extract_video_to_club_info import extract_video_to_club_info
from .channel_listeners.extract_image_to_simulator import extract_image_to_simulator
from utils.discord import get_client
import asyncio

async def handle_purpose(client, message: discord.Message, purpose: str, club):
    if purpose == "club_records":
        await extract_video_to_club_info(client, message, club)
    if purpose == "veteran_uma":
        await extract_image_to_simulator(client, message)

@get_client().event
async def on_message(message: discord.Message):
    client = get_client()

    if message.author == client.user:
        return
    if message.author.bot:
        return
    if not message.guild:
        return

    channel_id = str(message.channel.id)
    session = SessionLocal()

    try:
        configs = session.query(ChannelConfig).join(Club).filter(
            ChannelConfig.channel_id == channel_id
        ).all()
        
        # Extract data before closing session
        config_data = []
        for config in configs:
            config_data.append({
                'purpose': config.purpose,
                'club': config.club
            })
        
    except Exception as e:
        print(f"Database error in message handler: {e}")
        return
    finally:
        session.close()    

    # Process configs after session is closed
    if config_data:
        await asyncio.gather(*[
            handle_purpose(client, message, data['purpose'], data['club']) 
            for data in config_data
        ])
