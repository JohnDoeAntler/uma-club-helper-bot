import discord
from utils.db import SessionLocal, Club

NUMBER_EMOJIS = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']

def get_guild_clubs(guild_id: str):
    session = SessionLocal()
    try:
        return session.query(Club).filter_by(guild_id=guild_id).all()
    finally:
        session.close()

def create_club_selection_embed(clubs, title, description):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    
    club_list = "\n".join([f"{NUMBER_EMOJIS[i]} {club.name}" for i, club in enumerate(clubs[:10])])
    embed.add_field(name="Available Clubs", value=club_list, inline=False)
    return embed

async def add_reactions_to_message(message, count):
    for i in range(min(count, 10)):
        await message.add_reaction(NUMBER_EMOJIS[i])

def create_reaction_check(interaction, clubs, message):
    def check(reaction, user):
        return (
            user == interaction.user and 
            str(reaction.emoji) in NUMBER_EMOJIS[:len(clubs)] and
            reaction.message.id == message.id
        )
    return check

async def select_club_with_reactions(interaction, clubs, title, description):
    embed = create_club_selection_embed(clubs, title, description)
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    await add_reactions_to_message(message, len(clubs))
    
    try:
        reaction, user = await interaction.client.wait_for(
            'reaction_add', 
            timeout=60.0, 
            check=create_reaction_check(interaction, clubs, message)
        )
        
        selected_index = NUMBER_EMOJIS.index(str(reaction.emoji))
        selected_club = clubs[selected_index]
        
        await message.clear_reactions()
        return selected_club, message
        
    except TimeoutError:
        timeout_embed = discord.Embed(
            title="Selection Timeout",
            description="No club selected within 60 seconds. Please run the command again.",
            color=discord.Color.red()
        )
        await message.edit(embed=timeout_embed)
        await message.clear_reactions()
        return None, message

async def handle_club_selection(interaction, single_club_handler, multi_club_handler):
    try:
        clubs = get_guild_clubs(str(interaction.guild_id))
        
        if not clubs:
            await interaction.response.send_message("No clubs found. Please create a club first.", ephemeral=True)
            return
        
        if len(clubs) == 1:
            await single_club_handler(interaction, clubs[0])
        else:
            await multi_club_handler(interaction, clubs)
            
    except Exception as e:
        error_msg = f"Command failed: {str(e)}"
        if interaction.response.is_done():
            await interaction.followup.send(error_msg, ephemeral=True)
        else:
            await interaction.response.send_message(error_msg, ephemeral=True)
