import discord
from playwright.async_api import Page, async_playwright
from utils.discord import command
from utils.db import SessionLocal, Preset

async def setup_browser_and_page():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch()
    context = await browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    page = await context.new_page()
    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.goto("https://alpha123.github.io/uma-tools/umalator-global")
    await page.wait_for_timeout(1000)

    return pw, browser, page

async def get_track_names(page: Page):
    return await page.evaluate('''
        [...document.querySelectorAll('.trackSelect > select[tabIndex="2"] > option')].map(e => e.innerText.trim()).filter(e => e)
    ''')

async def select_track_name(page: Page, track_name: str):
    await page.locator('.trackSelect > select[tabIndex="2"]').select_option(track_name)

async def get_track_lengths(page: Page):
    return await page.evaluate('''
        [...document.querySelectorAll('.trackSelect > select[tabIndex="3"] > option')].map(e => e.innerText.trim()).filter(e => e)
    ''')

async def get_grounds(page: Page):
    return await page.evaluate('''
        [...document.querySelectorAll('select.groundSelect > option')].map(e => e.innerText.trim()).filter(e => e)
    ''')

async def get_weathers(page: Page):
    return await page.evaluate('''
        [...document.querySelectorAll('div.weatherSelect > img')].map(e => e.title.trim()).filter(e => e) 
    ''')

async def get_seasons(page: Page):
    return await page.evaluate('''
        [...document.querySelectorAll('div.seasonSelect > img')].map(e => e.title.trim()).filter(e => e) 
    ''')

class OptionSelectView(discord.ui.View):
    def __init__(self, options: list[str], author_id: int, prompt: str = "Select an option:"):
        super().__init__(timeout=60)
        self.value = None
        self.author_id = author_id
        self.prompt = prompt
        
        for i, option in enumerate(options[:25]):
            button = discord.ui.Button(
                label=option[:80],
                style=discord.ButtonStyle.secondary,
                custom_id=str(i)
            )
            button.callback = self.create_callback(option)
            self.add_item(button)

    def create_callback(self, option: str):
        async def callback(interaction: discord.Interaction):
            self.value = option
            await interaction.response.defer()
            self.stop()
        return callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

async def select_option(interaction: discord.Interaction, options: list[str], prompt: str = "Select an option:") -> str:
    if not options:
        await interaction.followup.send("No options available.", ephemeral=True)
        return None
    
    view = OptionSelectView(options, interaction.user.id, prompt)
    await interaction.followup.send(prompt, view=view, ephemeral=True)
    await view.wait()
    
    if not view.value:
        await interaction.followup.send("No option selected. Operation cancelled.", ephemeral=True)
        return None
    
    return view.value

@command(name='create-preset', description='Create a new preset in the database')
async def create_preset_command(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    
    pw = None
    browser = None
    
    try:
        pw, browser, page = await setup_browser_and_page()
        
        track_names = await get_track_names(page)
        if not track_names:
            await interaction.followup.send("Failed to retrieve track names from simulator.", ephemeral=True)
            return
        
        track_name = await select_option(interaction, track_names, "Select track name:")
        if not track_name:
            return
        
        await select_track_name(page, track_name)
        
        track_lengths = await get_track_lengths(page)
        if not track_lengths:
            await interaction.followup.send("Failed to retrieve track lengths from simulator.", ephemeral=True)
            return
        
        track_length = await select_option(interaction, track_lengths, "Select track length:")
        if not track_length:
            return
        
        grounds = await get_grounds(page)
        if not grounds:
            await interaction.followup.send("Failed to retrieve grounds from simulator.", ephemeral=True)
            return
        
        ground = await select_option(interaction, grounds, "Select ground condition:")
        if not ground:
            return
        
        weathers = await get_weathers(page)
        if not weathers:
            await interaction.followup.send("Failed to retrieve weather options from simulator.", ephemeral=True)
            return
        
        weather = await select_option(interaction, weathers, "Select weather:")
        if not weather:
            return
        
        seasons = await get_seasons(page)
        if not seasons:
            await interaction.followup.send("Failed to retrieve seasons from simulator.", ephemeral=True)
            return
        
        season = await select_option(interaction, seasons, "Select season:")
        if not season:
            return
        
        session = SessionLocal()
        try:
            preset = Preset(
                name=name,
                track_name=track_name,
                track_length=track_length,
                ground=ground,
                weather=weather,
                season=season,
                created_by=interaction.user.id,
            )
            session.add(preset)
            session.commit()
            
            await interaction.followup.send(
                f"Preset `{name}` created successfully!\n"
                f"Track: `{track_name}`\n"
                f"Length: `{track_length}`\n"
                f"Condition: `{ground}`\n"
                f"Weather: `{weather}`\n"
                f"Season: `{season}`",
                ephemeral=True
            )
        except Exception as e:
            session.rollback()
            await interaction.followup.send(f"Failed to save preset to database: {str(e)}", ephemeral=True)
        finally:
            session.close()
            
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
    finally:
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

@command(name='list-presets', description='List all custom presets')
async def list_presets_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    session = SessionLocal()
    try:
        presets = session.query(Preset).all()
        
        if not presets:
            await interaction.followup.send("No custom presets found in this server.", ephemeral=True)
            return
        
        preset_list = []
        for i, preset in enumerate(presets, 1):
            preset_list.append(
                f"{i}. Preset: `{preset.name}` Track: `{preset.track_name}`, Length: `{preset.track_length}`, "
                f"Condition: `{preset.ground}`, Weather: `{preset.weather}`, Season: `{preset.season}` Created by: <@{preset.created_by}>"
            )
        
        embed = discord.Embed(
            title="Custom Presets",
            description="\n".join(preset_list),
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"Failed to list presets: {str(e)}", ephemeral=True)
    finally:
        session.close()

@command(name='delete-preset', description='Delete an existing preset')
async def delete_preset_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    session = SessionLocal()
    try:
        presets = session.query(Preset).all()
        
        if not presets:
            await interaction.followup.send("No custom presets found in this server.", ephemeral=True)
            return
        
        preset_options = []
        for preset in presets:
            preset_options.append(
                f"{preset.track_name} - {preset.track_length} ({preset.ground}, {preset.weather}, {preset.season})"
            )
        
        selected_preset_str = await select_option(
            interaction,
            preset_options,
            "Select a preset to delete:"
        )
        
        if not selected_preset_str:
            return
        
        selected_index = preset_options.index(selected_preset_str)
        preset_to_delete = presets[selected_index]
        
        session.delete(preset_to_delete)
        session.commit()
        
        await interaction.followup.send(
            f"Preset deleted successfully!\n"
            f"Track: `{preset_to_delete.track_name}`\n"
            f"Length: {preset_to_delete.track_length}\n"
            f"Condition: `{preset_to_delete.ground}`\n"
            f"Weather: `{preset_to_delete.weather}`\n"
            f"Season: `{preset_to_delete.season}`",
            ephemeral=True
        )
        
    except Exception as e:
        session.rollback()
        await interaction.followup.send(f"Failed to delete preset: {str(e)}", ephemeral=True)
    finally:
        session.close()

