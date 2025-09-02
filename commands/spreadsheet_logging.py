import discord
from discord import app_commands
from discord.ext.commands import has_permissions
from utils.db import SessionLocal, Club
from utils.club_selection import handle_club_selection, select_club_with_reactions
from utils.discord import get_tree
import copy

def enable_club_logging(club_id: int, spreadsheet_id: str):
    session = SessionLocal()
    try:
        club = session.query(Club).filter_by(id=club_id).first()
        if not club:
            return None, "Club not found"
        
        if club.spreadsheet_id:
            return club, "already_enabled"
        
        club.spreadsheet_id = spreadsheet_id
        ret = copy.deepcopy(club)
        session.commit()
        return ret, "enabled"
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def disable_club_logging(club_id: int):
    session = SessionLocal()
    try:
        club = session.query(Club).filter_by(id=club_id).first()
        if not club:
            return None, "Club not found"
        
        if not club.spreadsheet_id:
            return club, "already_disabled"
        
        club.spreadsheet_id = None
        session.commit()
        return club, "disabled"
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

async def handle_single_club_enable(interaction, club, spreadsheet_id):
    updated_club, status = enable_club_logging(club.id, spreadsheet_id)
    if not updated_club:
        await interaction.response.send_message("Club not found.", ephemeral=True)
        return
    
    if status == "already_enabled":
        await interaction.response.send_message(
            f"Spreadsheet logging is already enabled for club '{updated_club.name}' with ID: `{updated_club.spreadsheet_id}`"
        )
    elif status == "enabled":
        await interaction.response.send_message(
            f"Spreadsheet logging enabled for club '{updated_club.name}' with spreadsheet ID: `{spreadsheet_id}`"
        )

async def handle_multiple_clubs_enable(interaction, clubs, spreadsheet_id):
    selected_club, message = await select_club_with_reactions(
        interaction, 
        clubs, 
        "Select Club for Spreadsheet Logging",
        f"Spreadsheet ID: `{spreadsheet_id}`"
    )
    
    if selected_club:
        updated_club, status = enable_club_logging(selected_club.id, spreadsheet_id)
        if not updated_club:
            error_embed = discord.Embed(
                title="Error",
                description="Club not found.",
                color=discord.Color.red()
            )
            await message.edit(embed=error_embed)
            return
        
        if status == "already_enabled":
            already_embed = discord.Embed(
                title="Already Enabled",
                description=f"Spreadsheet logging is already enabled for club '{updated_club.name}' with ID: `{updated_club.spreadsheet_id}`",
                color=discord.Color.yellow()
            )
            await message.edit(embed=already_embed)
        elif status == "enabled":
            success_embed = discord.Embed(
                title="Spreadsheet Logging Enabled",
                description=f"Successfully enabled for club '{updated_club.name}' with ID: `{spreadsheet_id}`",
                color=discord.Color.green()
            )
            await message.edit(embed=success_embed)

async def handle_single_club_disable(interaction, club):
    updated_club, status = disable_club_logging(club.id)
    if not updated_club:
        await interaction.response.send_message("Club not found.", ephemeral=True)
        return
    
    if status == "already_disabled":
        await interaction.response.send_message(
            f"Spreadsheet logging is already disabled for club '{updated_club.name}'"
        )
    elif status == "disabled":
        await interaction.response.send_message(
            f"Spreadsheet logging disabled for club '{updated_club.name}'"
        )

async def handle_multiple_clubs_disable(interaction, clubs):
    selected_club, message = await select_club_with_reactions(
        interaction, 
        clubs, 
        "Select Club to Disable Spreadsheet Logging",
        ""
    )
    
    if selected_club:
        updated_club, status = disable_club_logging(selected_club.id)
        if not updated_club:
            error_embed = discord.Embed(
                title="Error",
                description="Club not found.",
                color=discord.Color.red()
            )
            await message.edit(embed=error_embed)
            return
        
        if status == "already_disabled":
            already_embed = discord.Embed(
                title="Already Disabled",
                description=f"Spreadsheet logging is already disabled for club '{updated_club.name}'",
                color=discord.Color.yellow()
            )
            await message.edit(embed=already_embed)
        elif status == "disabled":
            success_embed = discord.Embed(
                title="Spreadsheet Logging Disabled",
                description=f"Successfully disabled for club '{updated_club.name}'",
                color=discord.Color.green()
            )
            await message.edit(embed=success_embed)

@has_permissions(administrator=True)
@get_tree().command(name='enable-spreadsheet-logging', description='Enable spreadsheet logging for a club')
@app_commands.describe(spreadsheet_id='The Google Sheets spreadsheet ID')
async def enable_spreadsheet_logging_command(interaction: discord.Interaction, spreadsheet_id: str):
    async def single_handler(interaction, club):
        await handle_single_club_enable(interaction, club, spreadsheet_id)
    
    async def multi_handler(interaction, clubs):
        await handle_multiple_clubs_enable(interaction, clubs, spreadsheet_id)
    
    await handle_club_selection(interaction, single_handler, multi_handler)

@has_permissions(administrator=True)
@get_tree().command(name='disable-spreadsheet-logging', description='Disable spreadsheet logging for a club')
async def disable_spreadsheet_logging_command(interaction: discord.Interaction):
    async def single_handler(interaction, club):
        await handle_single_club_disable(interaction, club)
    
    async def multi_handler(interaction, clubs):
        await handle_multiple_clubs_disable(interaction, clubs)
    
    await handle_club_selection(interaction, single_handler, multi_handler)
