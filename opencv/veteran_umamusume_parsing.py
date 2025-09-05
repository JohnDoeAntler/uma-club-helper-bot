import cv2
from cv2.typing import MatLike
from paddleocr import PaddleOCR
import numpy as np
import re

ocr = None

# copied
def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16) 
    b = int(hex_color[4:6], 16)
    return np.array([b, g, r])

def init_paddleocr():
    global ocr
    ocr = PaddleOCR(
        lang='en',
        ocr_version='PP-OCRv5',
        use_doc_orientation_classify=False, 
        use_doc_unwarping=False, 
        use_textline_orientation=False,
        return_word_box=False,
    )

def is_paddleocr_initialized():
    return ocr is not None

def create_binary_mask(image: MatLike, target_colors: list[str], tolerance: int = 0) -> MatLike:
    combined_mask = np.zeros(image.shape[:2], dtype=bool)
    
    for color in target_colors:
        target_bgr = hex_to_bgr(color)
        diff = np.abs(image.astype(np.int16) - target_bgr.astype(np.int16))
        color_mask = np.all(diff <= tolerance, axis=2)
        combined_mask = combined_mask | color_mask
    
    binary_image = np.zeros_like(image)
    binary_image[combined_mask] = [255, 255, 255]
    binary_image[~combined_mask] = [0, 0, 0]
    
    return binary_image

CLUB_HEADER_COLOR = "#7fcc0b"

def find_white_regions(image: MatLike, threshold: float = 0.5, min_width: int = 50, min_height: int = 20) -> list[tuple[int, int, int, int]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    bounding_boxes = []
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        # cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        if w < min_width or h < min_height:
            continue
        
        roi = gray[y:y+h, x:x+w]
        white_pixels = np.sum(roi == 255)
        total_pixels = roi.size
        white_ratio = white_pixels / total_pixels
        
        if white_ratio >= threshold:
            bounding_boxes.append((x, y, w, h))
    
    return bounding_boxes

def remove_noise(image: MatLike, min_area: int = 50) -> MatLike:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    result = image.copy()
    result_gray = gray.copy()
    
    removed_count = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            cv2.fillPoly(result_gray, [contour], 0)
            removed_count += 1
    
    result = cv2.cvtColor(result_gray, cv2.COLOR_GRAY2BGR)
    
    return result

def crop_image(image: MatLike, box: tuple[int, int, int, int]):
    x, y, w, h = box
    return image[y:y+h, x:x+w]

def parse_only_numbers(text: str) -> int:
    ret = 0
    for ch in text:
        if ch.isdigit():
            ret = ret * 10 + int(ch)
    return ret
# end of copied

TEMPLATE_DOUBLE_CIRCLE = cv2.imread("opencv/assets/double-circle.png")
TEMPLATE_DOUBLE_CIRCLE2 = cv2.imread("opencv/assets/double-circle2.png")
TEMPLATE_DOUBLE_CIRCLE3 = cv2.imread("opencv/assets/double-circle3.png")
TEMPLATE_CIRCLE = cv2.imread("opencv/assets/circle.png")
TEMPLATE_CIRCLE2 = cv2.imread("opencv/assets/circle2.png")
TEMPLATE_CIRCLE3 = cv2.imread("opencv/assets/circle3.png")

CIRCLE_TEMPLATES = [TEMPLATE_CIRCLE, TEMPLATE_CIRCLE2, TEMPLATE_CIRCLE3]
DOUBLE_CIRCLE_TEMPLATES = [TEMPLATE_DOUBLE_CIRCLE, TEMPLATE_DOUBLE_CIRCLE2, TEMPLATE_DOUBLE_CIRCLE3]

def find_club_header(image: MatLike):
    step1 = create_binary_mask(image, [CLUB_HEADER_COLOR], 50)
    step2 = remove_noise(step1, 4000)

    boxes = find_white_regions(
        step2,
        0.5,
        10,
        10,
    )

    max_width = 0
    max_width_box = None
    for box in boxes:
        if box[2] > max_width:
            max_width = box[2]
            max_width_box = box
    return max_width_box

def show_image(img: MatLike):
    cv2.imshow("Image", img)
    cv2.waitKey(0)

def posterization(im: MatLike, n: int = 2):
    indices = np.arange(0,256)   # List of all colors 
    divider = np.linspace(0,255,n+1)[1] # we get a divider
    quantiz = np.intp(np.linspace(0,255,n)) # we get quantization colors
    color_levels = np.clip(np.intp(indices/divider),0,n-1) # color levels 0,1,2..
    palette = quantiz[color_levels] # Creating the palette
    im2 = palette[im]  # Applying palette on image
    im2 = cv2.convertScaleAbs(im2) # Converting image back to uint8
    return im2

white_skill_color = "#bfbfff"
gold_skill_color = "#ffbf3f"
skill_section_coordinates = (5, 440, 542, 409)

def find_circle(image: MatLike):
    whatever = cv2.Canny(image, 50, 150)
    whatever = cv2.cvtColor(whatever, cv2.COLOR_GRAY2BGR)
    threshold = 0.5

    max_threshold = 0
    max_circle = None

    for template in CIRCLE_TEMPLATES:
        res = cv2.matchTemplate(whatever, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        for pt in zip(*loc[::-1]):
            if res[pt[1], pt[0]] > max_threshold:
                max_threshold = res[pt[1], pt[0]]
                max_circle = pt

    max_threshold = 0
    max_double_circle = None

    for template in DOUBLE_CIRCLE_TEMPLATES:
        res = cv2.matchTemplate(whatever, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        for pt in zip(*loc[::-1]):
            if res[pt[1], pt[0]] > max_threshold:
                max_threshold = res[pt[1], pt[0]]
                max_double_circle = pt

    return max_circle, max_double_circle

# rgb format
S_COLOR = (255,198,28) # ok
A_COLOR = (255,141,56) # ok
B_COLOR = (255,113,170) # ok
C_COLOR = (141,226,113) # ok
D_COLOR = (113,198,255) # ok
E_COLOR = (226,113,255) # ok
F_COLOR = (170,141,255) # ok
G_COLOR = (198,198,198) # ok

def to_bgr(arr):
    return (arr[2], arr[1], arr[0])

def guess_grade(image: np.ndarray):
    colors = {
        'S': S_COLOR,
        'A': A_COLOR,
        'B': B_COLOR,
        'C': C_COLOR,
        'D': D_COLOR,
        'E': E_COLOR,
        'F': F_COLOR,
        'G': G_COLOR,
    }

    for grade, color in colors.items():
        bgr = to_bgr(color)
        if np.any(np.all(image == bgr, axis=-1)):
            return grade
    
    return 'G'

def remove_level_from_skill_name(skill_name: str):
    if 'Lvl' in skill_name:
        return re.sub(r'Lvl\s*\d*', '', skill_name).strip()

    return skill_name

def parse_skill(image: MatLike, box: tuple[int, int, int, int]):
    skill_icon_width = int(box[2] * 0.15)

    crop = crop_image(image, (
        box[0] + skill_icon_width,
        box[1] + skill_section_coordinates[1],
        box[2] - skill_icon_width,
        box[3],
    ))

    texts = ocr.predict(crop)[0]["rec_texts"]
    skill_name = ' '.join(texts).strip()
    skill_name = remove_level_from_skill_name(skill_name)

    circle, double_circle = find_circle(crop)

    if double_circle is not None:
        return skill_name + " ◎"

    if circle is not None:
        return skill_name + " ○"
    
    return skill_name

    
def parse_skill_section(image: MatLike):
    p = posterization(image, 10)

    skill_section = crop_image(p, skill_section_coordinates)
    floodfilled = cv2.floodFill(skill_section, None, (0, 0), (0, 0, 0))[1]

    # turn non-black to fucking pure white
    mask = np.any(floodfilled != [0, 0, 0], axis=-1)  # True where pixel != black
    floodfilled[mask] = [255, 255, 255]

    floodfilled = cv2.cvtColor(floodfilled, cv2.COLOR_BGR2GRAY)
    contours, _ = cv2.findContours(floodfilled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(contour) for contour in contours]

    skills = []

    for box in boxes:
        if box[2] / box[3] < 5:
            continue

        skills.append(parse_skill(image, box))
    
    return skills

APTITUDES = [
    "Turf",
    "Dirt",
    "Sprint",
    "Mile",
    "Medium",
    "Long",
    "Front",
    "Pace",
    "Late",
    "End",
]

def parse_aptitude(image: MatLike, box: tuple[int, int, int, int]):
    crop = crop_image(image, (
        box[0] + 123,
        box[1] + 286,
        box[2],
        box[3]
    ))

    grade = crop_image(crop, (
        68,
        0,
        crop.shape[1] - 68,
        crop.shape[0],
    ))
    grade = posterization(grade, 10)
    grade = guess_grade(grade)

    texts = ocr.predict(crop)[0]["rec_texts"]

    aptitude = None

    for text in texts:
        for a in APTITUDES:
            if a in text:
                aptitude = a
                break
    
    return aptitude, grade

def parse_aptitude_section(image: MatLike):
    crop = crop_image(image, (123, 286, image.shape[1] - 148, 102))

    p = posterization(crop, 10)
    floodfilled = cv2.floodFill(p, None, (0, 0), (0, 0, 0))[1]
    floodfilled = cv2.cvtColor(floodfilled, cv2.COLOR_BGR2GRAY)
    contours, _ = cv2.findContours(floodfilled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(contour) for contour in contours]

    ret = {
        "Turf": "G",
        "Dirt": "G",
        "Sprint": "G",
        "Mile": "G",
        "Medium": "G",
        "Long": "G",
        "Front": "G",
        "Pace": "G",
        "Late": "G",
        "End": "G",
    }

    for box in boxes:
        if box[2] / box[3] < 3.5:
            continue

        aptitude, grade = parse_aptitude(image, box)
        if aptitude is not None:
            ret[aptitude] = grade

    return ret

def parse_name(img: MatLike):
    name_section = crop_image(
        img,
        (256, 50, 287, 104),
    )

    texts = ocr.predict(name_section)[0]["rec_texts"]
    return ' '.join(texts)

STAT_ATTRIBUTES = ["Speed", "Stamina", "Power", "Guts", "Wit"]

def parse_stat(image: MatLike, box: tuple[int, int, int, int]):
    stat = crop_image(image, box)

    texts = ocr.predict(stat)[0]["rec_texts"]

    attribute = None

    # any in text in texts matches one of the STAT_ATTRIBUTES
    for text in texts:
        if any(attr in text for attr in STAT_ATTRIBUTES):
            attribute = text
            break

    value = None

    for text in texts:
        if text.isdigit():
            value = text
            break

    return attribute, value

def parse_stat_section(image: MatLike):
    crop = crop_image(image, (13, 216, 528, 63))

    # split image into five pieces 528 / /5

    ret = {
        "Speed": 0,
        "Stamina": 0,
        "Power": 0,
        "Guts": 0,
        "Wit": 0,
    }

    for i in range(5):
        start = (528 * i) // 5
        end = (528 * (i + 1)) // 5

        attribute, value = parse_stat(crop, (start, 0, end - start, crop.shape[0]))

        if attribute is not None and value is not None:
            ret[attribute] = value

    return ret

def extract_image(path: str):
    img = cv2.imread(path)
    # results = ocr.predict(img)

    club_header = find_club_header(img)
    if club_header is None:
        return

    img = crop_image(img, [
        club_header[0],
        club_header[1],
        club_header[2],
        int(1.73131504 * (club_header[2])),
    ])
    # please resize the height to 960 with keeping the aspect ratio
    img = cv2.resize(img, (int(img.shape[1] * 960 / img.shape[0]), 960))

    return {
        "name": parse_name(img),
        "stats": parse_stat_section(img),
        "aptitudes": parse_aptitude_section(img),
        "skills": parse_skill_section(img),
    }

from playwright.sync_api import sync_playwright
from rapidfuzz import process, fuzz

def fuzzy_match(a: str, b: list[str]):
    best_match, _, _ = process.extractOne(a, b, scorer=fuzz.WRatio)
    return best_match

def input_name(page, info: dict[str, any]):
    umamusumes_dict = page.evaluate('''
        [...document.querySelectorAll('#umaPane > div:nth-child(1) .umaSuggestions .umaSuggestion')].map(e => [e.getAttribute("data-uma-id"), e.innerText]).reduce((a, [id, name]) => ({ ...a, [name]: id }), {})
    ''')
    umamusumes = list(umamusumes_dict.keys())
    true_name = fuzzy_match(info["name"], umamusumes)
    umamusume_id = umamusumes_dict[true_name]

    page.locator('#umaPane > div:nth-child(1) input.umaSelectInput').focus()
    page.locator(f'#umaPane > div:nth-child(1) li.umaSuggestion[data-uma-id="{umamusume_id}"]').click()

def input_skills(page, info: dict[str, any]):
    skills_dict = page.evaluate('''
        [...document.querySelectorAll('#umaPane > div:nth-child(1) .skillList .skill')].map(e => [e.getAttribute("data-skillid"), e.innerText]).reduce((a, [id, name]) => ({ ...a, [name]: id }), {})
    ''')
    unique_skill_name = page.evaluate('''
        document.querySelector('div.skill.skill-unique').innerText
    ''')

    skills = list(skills_dict.keys())
    true_skils = []
    for skill in info["skills"]:
        match = fuzzy_match(skill, skills)
        if match == unique_skill_name:
            continue
        true_skils.append(match)

    skills_ids = [skills_dict[skill] for skill in true_skils]

    for skill_id in skills_ids:
        page.locator('#umaPane > div:nth-child(1) div.skill.addSkillButton').click()
        page.locator(f'#umaPane > div:nth-child(1) div.skill[data-skillid="{skill_id}"]').click()

def input_stats(page, info: dict[str, any]):
    stat_headers = page.evaluate('''
        [...document.querySelectorAll('#umaPane > div:nth-child(1) .horseParams .horseParamHeader')].map(e => e.innerText.trim())
    ''')

    for stat, value in info["stats"].items():
        index = len(stat_headers) + stat_headers.index(stat)
        page.locator(f'#umaPane > div:nth-child(1) .horseParams .horseParam:nth-child({index + 1}) input').fill(value)

def number_to_distance(number: int):
    if number <= 1400:
        return "Sprint"
    elif number <= 1800:
        return "Mile"
    elif number <= 2400:
        return "Medium"
    else:
        return "Long"

def get_presets(page):
    return page.evaluate('''
        [...document.querySelectorAll('#P0-0 option')].map(e => e.innerText).filter(e => e.trim())
    ''')

def input_preset(page, preset: str):
    page.locator(f'#P0-0').select_option(preset)

def input_style(page, info: dict[str, any], aptitude_dict: dict[str, any], style: str):
    style_options = page.evaluate('''
        [...document.querySelectorAll('#umaPane > div:nth-child(1) .horseStrategySelect option')].map(e => e.innerText).filter(e => e.trim())
    ''')

    # set the style
    long_term_style = [s for s in style_options if s.startswith(style)][0]
    page.locator(f'#umaPane > div:nth-child(1) .horseStrategySelect').select_option(long_term_style)

    # set the grade of the style
    page.locator(f'#umaPane > div:nth-child(1) div.horseAptitudeSelect[tabindex="{aptitude_dict["Style"]}"]').click()
    page.locator(f'#umaPane > div:nth-child(1) div.horseAptitudeSelect[tabindex="{aptitude_dict["Style"]}"] li[data-horse-aptitude="{info["aptitudes"][style]}"]').click()

def input_surface_and_distance(page, info: dict[str, any], aptitude_dict: dict[str, any]):
    racetrack_name = page.evaluate("document.querySelector('.racetrackName').innerText")
    surface = "Dirt" if "Dirt" in racetrack_name else "Turf"
    distance = number_to_distance(parse_only_numbers(racetrack_name))

    # surface
    page.locator(f'#umaPane > div:nth-child(1) div.horseAptitudeSelect[tabindex="{aptitude_dict["Surface"]}"]').click()
    page.locator(f'#umaPane > div:nth-child(1) div.horseAptitudeSelect[tabindex="{aptitude_dict["Surface"]}"] li[data-horse-aptitude="{info["aptitudes"][surface]}"]').click()

    # distance
    page.locator(f'#umaPane > div:nth-child(1) div.horseAptitudeSelect[tabindex="{aptitude_dict["Distance"]}"]').click()
    page.locator(f'#umaPane > div:nth-child(1) div.horseAptitudeSelect[tabindex="{aptitude_dict["Distance"]}"] li[data-horse-aptitude="{info["aptitudes"][distance]}"]').click()

def compute_aptitude_dict(page):
    return page.evaluate('''
        [...document.querySelectorAll('#umaPane > div:nth-child(1) .horseAptitudes > div')]
            .map((e) => [e, e.querySelector('.horseAptitudeSelect')])
            .filter(([e, s]) => !!s)
            .map(([e, s]) => [e.innerText.split(' ')[0], s.getAttribute('tabindex')])
            .reduce((a, [key, value]) => ({ ...a, [key]: value }), {})
    ''')

def main():
    init_paddleocr()
    info = extract_image("opencv/data/image4.png")

    with sync_playwright() as p:
        # goto the url
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto("https://alpha123.github.io/uma-tools/umalator-global")
        page.wait_for_timeout(1000)

        input_name(page, info)
        input_stats(page, info)
        input_skills(page, info)

        aptitude_dict = compute_aptitude_dict(page)

        # get the list of preset (2025-08 CM 2025-09 CM)
        presets = get_presets(page)

        # ask player for the style and preset
        style = input("Enter the style: ")
        input_style(page, info, aptitude_dict, style)

        # ask player for the preset
        for i, preset in enumerate(presets):
            print(f'{i}: {preset}')

        preset_idx = input("Enter the preset: ")
        selected_preset = presets[int(preset_idx)]
        input_preset(page, selected_preset)
        input_surface_and_distance(page, info, aptitude_dict)
        page.screenshot(path="opencv/data/screenshot.png")
        input('Press Enter to continue...')

        browser.close()

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()