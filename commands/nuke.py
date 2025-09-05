import discord
from discord.ext.commands import has_permissions
from utils.config import get_env
from utils.db import engine, Base
from utils.discord import get_tree

@has_permissions(administrator=True)
@get_tree().command(name='nuke-db', description='[DEV] Drop and recreate all database tables')
async def handle_nuke_command(interaction: discord.Interaction):
    if get_env() != 'DEV':
        await interaction.response.send_message("This command is only available in development environment.", ephemeral=True)
        return

    try:
        await interaction.response.defer(ephemeral=True)
        
        if not engine:
            await interaction.followup.send("Database not connected. Cannot perform nuke operation.", ephemeral=True)
            return
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("Database: All tables dropped")
        
        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        print("Database: All tables recreated")
        
        await interaction.followup.send("Database nuked successfully! All tables have been dropped and recreated.", ephemeral=True)
        
    except Exception as e:
        error_message = f"Failed to nuke database: {str(e)}"
        print(f"Database nuke error: {e}")
        await interaction.followup.send(error_message, ephemeral=True)
