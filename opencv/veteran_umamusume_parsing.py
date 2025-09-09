import cv2
from cv2.typing import MatLike
from paddleocr import PaddleOCR
import numpy as np
import re
from utils.opencv import create_binary_mask, remove_noise, find_white_regions, crop_image, ocr

CLUB_HEADER_COLOR = "#7fcc0b"
TEMPLATE_DOUBLE_CIRCLE = cv2.imread("opencv/assets/double-circle.png")
TEMPLATE_DOUBLE_CIRCLE2 = cv2.imread("opencv/assets/double-circle2.png")
TEMPLATE_DOUBLE_CIRCLE3 = cv2.imread("opencv/assets/double-circle3.png")
TEMPLATE_CIRCLE = cv2.imread("opencv/assets/circle.png")
TEMPLATE_CIRCLE2 = cv2.imread("opencv/assets/circle2.png")
TEMPLATE_CIRCLE3 = cv2.imread("opencv/assets/circle3.png")

CIRCLE_TEMPLATES = [TEMPLATE_CIRCLE, TEMPLATE_CIRCLE2, TEMPLATE_CIRCLE3]
DOUBLE_CIRCLE_TEMPLATES = [TEMPLATE_DOUBLE_CIRCLE, TEMPLATE_DOUBLE_CIRCLE2, TEMPLATE_DOUBLE_CIRCLE3]

def find_club_header(image: MatLike):
    step1 = create_binary_mask(image, [CLUB_HEADER_COLOR], 60)
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
        return True, re.sub(r'Lvl\s*\d*', '', skill_name).strip()

    return False, skill_name

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
    is_unique_skill, skill_name = remove_level_from_skill_name(skill_name)

    circle, double_circle = find_circle(crop)

    if double_circle is not None:
        return is_unique_skill, skill_name + " ◎"

    if circle is not None:
        return is_unique_skill, skill_name + " ○"
    
    return is_unique_skill, skill_name

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

    unique_skills = []
    skills = []

    for box in boxes:
        if box[2] / box[3] < 5:
            continue

        is_unique_skill, skill_name = parse_skill(image, box)
        if is_unique_skill:
            unique_skills.append(skill_name)
        else:
            skills.append(skill_name)
    
    return unique_skills, skills

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

    value = 0

    for text in texts:
        if text.isdigit():
            value = max(value, int(text))

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
    unique_skills, skills = parse_skill_section(img)

    return {
        "name": parse_name(img),
        "stats": parse_stat_section(img),
        "aptitudes": parse_aptitude_section(img),
        "unique_skills": unique_skills,
        "skills": skills,
    }
