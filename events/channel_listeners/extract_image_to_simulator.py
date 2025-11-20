import discord
import uuid
import json
from playwright.async_api import Browser, Page, PlaywrightContextManager, async_playwright
from rapidfuzz import process, fuzz
from utils.db import Preset, SessionLocal
from utils.parse import parse_only_numbers
from opencv.veteran_umamusume_parsing import extract_image
from utils.blocking import run_blocking
import os
import io
import asyncio

def fuzzy_match(a: str, b: list[str]):
    best_match, _, _ = process.extractOne(a, b, scorer=fuzz.WRatio)
    return best_match

async def input_name(page: Page, info: dict[str, any]):
    umamusumes_dict = await page.evaluate('''
        [...document.querySelectorAll('#umaPane > div.selected .umaSuggestions .umaSuggestion')].map(e => [e.getAttribute("data-uma-id"), e.innerText]).reduce((a, [id, name]) => ({ ...a, [name]: id }), {})
    ''')
    umamusumes = list(umamusumes_dict.keys())
    true_name = fuzzy_match(info["name"], umamusumes)
    umamusume_id = umamusumes_dict[true_name]

    await page.locator('#umaPane > div.selected input.umaSelectInput').focus()
    await page.locator(f'#umaPane > div.selected li.umaSuggestion[data-uma-id="{umamusume_id}"]').click()

async def input_skills(page: Page, info: dict[str, any]):
    skills_dict = await page.evaluate('''
        [...document.querySelectorAll('#umaPane > div.selected .skillList .skill')].map(e => [e.getAttribute("data-skillid"), e.innerText]).reduce((a, [id, name]) => ({ ...a, [name]: id }), {})
    ''')
    unique_skill_name = await page.evaluate('''
        document.querySelector('div.skill.skill-unique').innerText
    ''')

    skills = list(skills_dict.keys())
    true_skils = set()
    for skill in info["skills"]:
        match = fuzzy_match(skill, skills)
        if match == unique_skill_name:
            continue

        true_skils.add(match)

    skills_ids = [skills_dict[skill] for skill in true_skils]

    for skill_id in skills_ids:
        await page.locator('#umaPane > div.selected div.skill.addSkillButton').click()
        await page.locator(f'#umaPane > div.selected div.skill[data-skillid="{skill_id}"]').click()

async def input_stats(page: Page, info: dict[str, any]):
    stat_headers = await page.evaluate('''
        [...document.querySelectorAll('#umaPane > div.selected .horseParams .horseParamHeader')].map(e => e.innerText.trim())
    ''')

    for stat, value in info["stats"].items():
        index = len(stat_headers) + stat_headers.index(stat)
        await page.locator(f'#umaPane > div.selected .horseParams .horseParam:nth-child({index + 1}) input').fill(str(value))

def number_to_distance(number: int):
    if number <= 1400:
        return "Sprint"
    elif number <= 1800:
        return "Mile"
    elif number <= 2400:
        return "Medium"
    else:
        return "Long"

async def get_presets(page: Page):
    return await page.evaluate('''
        [...document.querySelectorAll('#P0-0 option')].map(e => e.innerText).filter(e => e.trim())
    ''')

async def select_track_name(page: Page, track_name: str):
    await page.locator('.trackSelect > select[tabIndex="2"]').select_option(track_name)

async def select_track_length(page: Page, track_length: str):
    await page.locator('.trackSelect > select[tabIndex="3"]').select_option(track_length)

async def select_ground(page: Page, ground: str):
    await page.locator('select.groundSelect').select_option(ground)

async def select_weather(page: Page, weather: str):
    await page.locator(f'div.weatherSelect > img[title="{weather}"]').click()

async def select_season(page: Page, season: str):
    await page.locator(f'div.seasonSelect > img[title="{season}"]').click()

async def input_preset(page: Page, preset: str, custom_presets: list[Preset]):
    if not preset.startswith("*"):
        await page.locator(f'#P0-0').select_option(preset)
        return
    
    # remove the asterisk
    preset_name = preset[1:]
    custom_preset = [preset for preset in custom_presets if preset.name == preset_name][0]

    await select_track_name(page, custom_preset.track_name)
    await select_track_length(page, custom_preset.track_length)
    await select_ground(page, custom_preset.ground)
    await select_weather(page, custom_preset.weather)
    await select_season(page, custom_preset.season)

async def input_style(page, info: dict[str, any], aptitude_dict: dict[str, any], style: str):
    style_options = await page.evaluate('''
        [...document.querySelectorAll('#umaPane > div.selected .horseStrategySelect option')].map(e => e.innerText).filter(e => e.trim())
    ''')

    # set the style
    long_term_style = [s for s in style_options if s.startswith(style)][0]
    await page.locator(f'#umaPane > div.selected .horseStrategySelect').select_option(long_term_style)

    # set the grade of the style
    await page.locator(f'#umaPane > div.selected div.horseAptitudeSelect[tabindex="{aptitude_dict["Style"]}"]').click()
    await page.locator(f'#umaPane > div.selected div.horseAptitudeSelect[tabindex="{aptitude_dict["Style"]}"] li[data-horse-aptitude="{info["aptitudes"][style]}"]').click()

async def input_surface_and_distance(page, info: dict[str, any], aptitude_dict: dict[str, any]):
    racetrack_name = await page.evaluate("document.querySelector('.racetrackName').innerText")
    surface = "Dirt" if "Dirt" in racetrack_name else "Turf"
    distance = number_to_distance(parse_only_numbers(racetrack_name))

    # surface
    await page.locator(f'#umaPane > div.selected div.horseAptitudeSelect[tabindex="{aptitude_dict["Surface"]}"]').click()
    await page.locator(f'#umaPane > div.selected div.horseAptitudeSelect[tabindex="{aptitude_dict["Surface"]}"] li[data-horse-aptitude="{info["aptitudes"][surface]}"]').click()

    # distance
    await page.locator(f'#umaPane > div.selected div.horseAptitudeSelect[tabindex="{aptitude_dict["Distance"]}"]').click()
    await page.locator(f'#umaPane > div.selected div.horseAptitudeSelect[tabindex="{aptitude_dict["Distance"]}"] li[data-horse-aptitude="{info["aptitudes"][distance]}"]').click()

async def compute_aptitude_dict(page: Page):
    return await page.evaluate('''
        [...document.querySelectorAll('#umaPane > div.selected .horseAptitudes > div')]
            .map((e) => [e, e.querySelector('.horseAptitudeSelect')])
            .filter(([e, s]) => !!s)
            .map(([e, s]) => [e.innerText.split(' ')[0], s.getAttribute('tabindex')])
            .reduce((a, [key, value]) => ({ ...a, [key]: value }), {})
    ''')

class StyleSelectView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.value = None
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="Front", style=discord.ButtonStyle.primary)
    async def front(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "Front"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Pace", style=discord.ButtonStyle.primary)
    async def pace(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "Pace"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Late", style=discord.ButtonStyle.primary)
    async def late(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "Late"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="End", style=discord.ButtonStyle.primary)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "End"
        await interaction.response.defer()
        self.stop()

class PresetSelectView(discord.ui.View):
    def __init__(self, presets: list[str], author_id: int):
        super().__init__(timeout=60)
        self.value = None
        self.author_id = author_id
        
        for i, preset in enumerate(presets[:25]):
            button = discord.ui.Button(
                label=preset[:80],
                style=discord.ButtonStyle.secondary,
                custom_id=str(i)
            )
            button.callback = self.create_callback(preset)
            self.add_item(button)

    def create_callback(self, preset: str):
        async def callback(interaction: discord.Interaction):
            self.value = preset
            await interaction.response.defer()
            self.stop()
        return callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

async def select_style(thread, author_id: int, hint: str = ""):
    view = StyleSelectView(author_id)
    if hint:
        prompt_msg = await thread.send(f"Select the style for {hint}:", view=view)
    else:
        prompt_msg = await thread.send("Select the style:", view=view)
    await view.wait()
    await prompt_msg.edit(view=None)
    
    if not view.value:
        await thread.send("No style selected, defaulting to Front.")
        return "Front"
    
    return view.value

async def select_preset(thread, presets: list[str], custom_presets: list[Preset], author_id: int):
    view = PresetSelectView(presets + [f"*{preset.name}" for preset in custom_presets], author_id)
    prompt_msg = await thread.send("Select the preset:", view=view)
    await view.wait()
    await prompt_msg.edit(view=None)
    
    if not view.value:
        await thread.send("No preset selected, defaulting to first preset.")
        return presets[0]
    
    return view.value

async def simulate(page: Page, samples=100):
    await page.locator('input#nsamples').fill(str(samples))
    await page.locator('button#run').click()
    await page.wait_for_timeout(1000)

async def copy_link(page: Page):
    await page.locator('a:has-text("Copy link")').click()
    return await page.evaluate('''
        navigator.clipboard.readText()
    ''')

async def setup_browser_and_page():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch()
    context = await browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    page = await context.new_page()
    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.goto("https://alpha123.github.io/uma-tools/umalator-global")
    await page.wait_for_timeout(1000)

    return pw, browser, page

async def attachment_check(message: discord.Message):
    if len(message.attachments) == 0:
        return []

    attachments = [attachment for attachment in message.attachments if attachment.content_type.startswith("image/")]

    if not len(attachments):
        return []

    return attachments

async def extract_attachment_info(bot, attachment: discord.Attachment) -> dict[str, any]:
    file_path = f'./downloads/{uuid.uuid4()}.{attachment.content_type.split("/")[1]}'

    try:
        await attachment.save(file_path)
        info = await run_blocking(bot, extract_image, file_path)
        return info
    finally:
        os.remove(file_path)

def hash_dict(info: dict[str, any]) -> int:
    return hash(tuple(sorted(info.items())))

async def extract_attachments(bot, attachments: list[discord.Attachment]) -> list[dict[str, any]]:
    ret = {}

    # extract info
    for attachment in attachments:
        try:
            info = await extract_attachment_info(bot, attachment)
            hash_info = hash(info["name"]) + hash_dict(info["stats"]) + hash_dict(info["aptitudes"])

            if hash_info not in ret:
                ret[hash_info] = info
            else:
                ret[hash_info]["skills"].extend(info["skills"])
        except Exception:
            pass

    # remove duplicate skills
    for info in ret.values():
        info["skills"] = list(set(info["skills"]))

    return list(ret.values())

def get_uma_stats(uma: dict[str, any]):
    return f"{uma['stats']['Speed']}/{uma['stats']['Stamina']}/{uma['stats']['Power']}/{uma['stats']['Guts']}/{uma['stats']['Wit']}"

def get_custom_presets():
    session = SessionLocal()
    try:
        presets = session.query(Preset).all()
        return [preset for preset in presets]
    finally:
        session.close()

async def run_simulator_single(uma: dict[str, any], thread: discord.Thread, message: discord.Message):
    await thread.edit(name=f"{uma['name']} ({get_uma_stats(uma)})")
    await thread.send(f"```json\n{json.dumps(uma, indent=2)}\n```")

    # parallel tasks
    future_list = []

    # initialize playwright
    async def browser_init_and_page_init():
        pw, browser, page = await setup_browser_and_page()

        # input info
        presets = await get_presets(page)

        await input_name(page, uma)
        await input_stats(page, uma)
        await input_skills(page, uma)

        return pw, browser, page, presets

    future_list.append(select_style(thread, message.author.id))
    future_list.append(browser_init_and_page_init())
    style, (pw, browser, page, presets) = await asyncio.gather(*future_list)
    custom_presets = get_custom_presets()

    preset = await select_preset(thread, presets, custom_presets, message.author.id)

    await input_preset(page, preset, custom_presets)

    aptitude_idx_dict = await compute_aptitude_dict(page)
    await input_style(page, uma, aptitude_idx_dict, style)
    await input_surface_and_distance(page, uma, aptitude_idx_dict)
    await simulate(page)
    
    screenshot = await page.screenshot()
    url = await copy_link(page)
    
    await thread.send(f"Simulator url: [here]({url})", file=discord.File(io.BytesIO(screenshot), filename="_.png"))
    await browser.close()
    await pw.stop()

async def select_uma_slot(page: Page, slot: str):
    await page.locator(f'#umaPane > div.selected div.umaTab:has-text("{slot}")').click()

async def run_simulator_double(uma1: dict[str, any], uma2: dict[str, any], thread: discord.Thread, message: discord.Message):
    await thread.edit(name=f"{uma1['name']} compared to {uma2['name']}"[:96])
    await thread.send(f"```json\n{json.dumps(uma1, indent=2)}\n```\n```json\n{json.dumps(uma2, indent=2)}\n```")

    # parallel tasks
    future_list = []

    # initialize playwright
    async def browser_init_and_page_init():
        pw, browser, page = await setup_browser_and_page()

        # get presets
        presets = await get_presets(page)

        async def fill_data(slot, uma):
            await select_uma_slot(page, slot)
            await input_name(page, uma)
            await input_stats(page, uma)
            await input_skills(page, uma)

        await fill_data('Umamusume 1', uma1)
        await fill_data('Umamusume 2', uma2)
        return pw, browser, page, presets

    future_list.append(select_style(thread, message.author.id, f"`{uma1['name']} ({get_uma_stats(uma1)})`"))
    future_list.append(select_style(thread, message.author.id, f"`{uma2['name']} ({get_uma_stats(uma2)})`"))
    future_list.append(browser_init_and_page_init())
    style1, style2, (pw, browser, page, presets) = await asyncio.gather(*future_list)
    custom_presets = get_custom_presets()

    preset = await select_preset(thread, presets, custom_presets, message.author.id)
    await input_preset(page, preset, custom_presets)

    async def set_style_and_surface_and_distance(slot, uma, style):
        await select_uma_slot(page, slot)
        aptitude_idx_dict = await compute_aptitude_dict(page)
        await input_style(page, uma, aptitude_idx_dict, style)
        await input_surface_and_distance(page, uma, aptitude_idx_dict)

    await set_style_and_surface_and_distance('Umamusume 1', uma1, style1)
    await set_style_and_surface_and_distance('Umamusume 2', uma2, style2)
    await simulate(page)
    
    screenshot = await page.screenshot()
    url = await copy_link(page)
    
    await thread.send(f"Simulator url: [here]({url})", file=discord.File(io.BytesIO(screenshot), filename="_.png"))
    await browser.close()
    await pw.stop()

async def extract_image_to_simulator(bot: discord.Client, message: discord.Message):
    # attachment check
    attachments = await attachment_check(message)
    if not len(attachments):
        await message.channel.send("No images found, expected at least one image of a veteran uma screenshot.")
        return

    thread = await message.create_thread(name='analyzing...')
    umas = await extract_attachments(bot, attachments)

    if len(umas) == 0:
        await thread.edit(name='failed analysis')
        await thread.send("No umas found, expected at least one uma screenshot.")
        return
    elif len(umas) == 1:
        await run_simulator_single(umas[0], thread, message)
        return
    elif len(umas) == 2:
        await run_simulator_double(umas[0], umas[1], thread, message)
        return
    else:
        await thread.edit(name='failed analysis')
        await thread.send("Too many umas found, currently not supported to run simulator for more than two umas.")
        return
