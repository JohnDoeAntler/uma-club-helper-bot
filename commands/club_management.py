import discord
from discord.ext.commands import has_permissions
from utils.db import SessionLocal, Club
from discord import app_commands
from utils.discord import command

@command(name='create-club', description='Create a new club')
@app_commands.describe(club_name='Name of the club to create')
async def create_club_command(interaction: discord.Interaction, club_name: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to create clubs.", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    
    session = SessionLocal()
    try:
        # Check if club already exists in this guild
        existing_club = session.query(Club).filter_by(name=club_name, guild_id=guild_id).first()
        if existing_club:
            await interaction.response.send_message(f"Club '{club_name}' already exists in this server.", ephemeral=True)
            return
        
        # Create new club
        new_club = Club(name=club_name, guild_id=guild_id)
        session.add(new_club)
        session.commit()
        
        await interaction.response.send_message(f"Club '{club_name}' has been created successfully!")
        
    except Exception as e:
        session.rollback()
        await interaction.response.send_message(f"Failed to create club: {str(e)}", ephemeral=True)
    finally:
        session.close()

@command(name='list-clubs', description='List all clubs in this server')
async def list_clubs_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to list clubs.", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    
    session = SessionLocal()
    try:
        clubs = session.query(Club).filter_by(guild_id=guild_id).all()
        
        if not clubs:
            await interaction.response.send_message("No clubs found in this server.")
            return
        
        club_list = "\n".join([f"- {club.name}" for club in clubs])
        embed = discord.Embed(
            title="Clubs in this Server",
            description=club_list,
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"Failed to list clubs: {str(e)}", ephemeral=True)
    finally:
        session.close()

@command(name='delete-club', description='Delete a club')
@app_commands.describe(club_name='Name of the club to delete')
async def delete_club_command(interaction: discord.Interaction, club_name: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to delete clubs.", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    
    session = SessionLocal()
    try:
        club = session.query(Club).filter_by(name=club_name, guild_id=guild_id).first()
        
        if not club:
            await interaction.response.send_message(f"Club '{club_name}' not found in this server.", ephemeral=True)
            return
        
        session.delete(club)
        session.commit()
        
        await interaction.response.send_message(f"Club '{club_name}' has been deleted successfully!")
        
    except Exception as e:
        session.rollback()
        await interaction.response.send_message(f"Failed to delete club: {str(e)}", ephemeral=True)
    finally:
        session.close()
