import discord
from discord.ext.commands import has_permissions
from utils.db import SessionLocal, ChannelConfig
from utils.club_selection import handle_club_selection, select_club_with_reactions
from utils.discord import command

def setup_channel_for_club(channel_id: str, club_id: int, created_by: str):
    session = SessionLocal()
    try:
        existing = session.query(ChannelConfig).filter_by(
            channel_id=channel_id, 
            purpose="club_records"
        ).first()
        
        if existing:
            session.delete(existing)
            session.commit()
            return "removed"
        else:
            new_config = ChannelConfig(
                channel_id=channel_id,
                purpose="club_records",
                club_id=club_id,
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

async def handle_single_club(interaction, club):
    channel_id = str(interaction.channel.id)
    created_by = str(interaction.user.id)
    
    result = setup_channel_for_club(channel_id, club.id, created_by)
    
    if result == "removed":
        await interaction.response.send_message(
            f"Removed {interaction.channel.mention} from storing records for club '{club.name}'.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"Selected {interaction.channel.mention} for storing records for club '{club.name}'.",
            ephemeral=True
        )

async def handle_multiple_clubs(interaction, clubs):
    channel_id = str(interaction.channel.id)
    created_by = str(interaction.user.id)
    
    selected_club, message = await select_club_with_reactions(
        interaction, 
        clubs, 
        "Select Club for Channel Records",
        f"Channel: {interaction.channel.mention}"
    )
    
    if selected_club:
        result = setup_channel_for_club(channel_id, selected_club.id, created_by)
        
        if result == "removed":
            success_embed = discord.Embed(
                title="Channel Configuration Removed",
                description=f"Removed {interaction.channel.mention} from storing records for club '{selected_club.name}'.",
                color=discord.Color.orange()
            )
        else:
            success_embed = discord.Embed(
                title="Channel Configuration Added",
                description=f"Selected {interaction.channel.mention} for storing records for club '{selected_club.name}'.",
                color=discord.Color.green()
            )
        
        await message.edit(embed=success_embed)

@command(name='setup-channel-club-records', description='Setup channel for storing club records')
async def setup_channel_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to setup channel for club records.", ephemeral=True)
        return

    await handle_club_selection(interaction, handle_single_club, handle_multiple_clubs)
