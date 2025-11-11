import discord
from discord.ext.commands import has_permissions
from utils.db import SessionLocal, ChannelConfig
from utils.discord import command

def toggle_channel_for_veteran_uma(channel_id: str, created_by: str):
    session = SessionLocal()
    try:
        existing = session.query(ChannelConfig).filter_by(
            channel_id=channel_id, 
            purpose="veteran_uma"
        ).first()
        
        if existing:
            session.delete(existing)
            session.commit()
            return "removed"
        else:
            new_config = ChannelConfig(
                channel_id=channel_id,
                purpose="veteran_uma",
                club_id=None,
                created_by=created_by
            )
            session.add(new_config)
            session.commit()
            return "added"
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

@command(name='setup-channel-veteran-uma', description='Setup channel for processing veteran uma screenshots')
async def setup_channel_veteran_uma_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to setup channel for veteran uma screenshots.", ephemeral=True)
        return

    try:
        channel_id = str(interaction.channel.id)
        created_by = str(interaction.user.id)
        
        result = toggle_channel_for_veteran_uma(channel_id, created_by)
        
        if result == "removed":
            await interaction.response.send_message(
                f"Removed {interaction.channel.mention} from processing veteran uma screenshots.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Setup {interaction.channel.mention} for processing veteran uma screenshots.",
                ephemeral=True
            )
            
    except Exception as e:
        await interaction.response.send_message(f"Command failed: {str(e)}", ephemeral=True)
