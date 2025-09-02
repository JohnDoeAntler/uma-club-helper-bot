import discord
from utils.discord import get_tree

@get_tree().command(name='ping', description='Check if the bot is responsive')
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message('Pong!')
