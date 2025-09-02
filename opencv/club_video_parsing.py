from collections import Counter
import cv2
import numpy as np
from cv2.typing import MatLike
from paddleocr import PaddleOCR

# TODO: to further optimize the video parsing, we could capture the scrollbar to obtain the max height of the club lsit

# constants
TRUE_RATIO = 3.89
MIN_RATIO = TRUE_RATIO - 0.2
MAX_RATIO = TRUE_RATIO + 0.2
# ===
CLUB_HEADER_COLOR = "#7fcc0b"
# ===
ROW_HEADER_COLOR = "#e4ddd2"
ROW_BACKGROUND_COLOR = "#ffffff"
ROW_SELF_BACKGROUND_COLOR = "#fff4c6"
ROW_KEY_BACKGROUND = "#ece7e4"
# == 
ICON_I_GRADIENT_TOP_COLOR = "#ffffff"
ICON_I_GRADIENT_BOTTOM_COLOR = "#fafafa"
# ===
LEADER_FLAG_COLOR = "#ef3c39"
OFFICER_FLAG_COLOR = "#267fe9"
MEMBER_FLAG_COLOR = "#5dca10"

# helper functions
ocr = None

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

# main functions

def load_screenshot(filepath: str):
    image = cv2.imread(filepath)
    if image is None:
        return None
    
    return image

def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16) 
    b = int(hex_color[4:6], 16)
    return np.array([b, g, r])

def replace_color(image: MatLike, from_color: str, to_color: str, tolerance: int = 0) -> MatLike:
    from_bgr = hex_to_bgr(from_color)
    to_bgr = hex_to_bgr(to_color)
    
    diff = np.abs(image.astype(np.int16) - from_bgr.astype(np.int16))
    mask = np.all(diff <= tolerance, axis=2)
    
    result = image.copy()
    result[mask] = to_bgr
    
    return result

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

def expand_white_areas(image: MatLike, radius: int) -> MatLike:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    kernel_size = 2 * radius + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    
    expanded = cv2.dilate(gray, kernel, iterations=1)
    
    result = cv2.cvtColor(expanded, cv2.COLOR_GRAY2BGR)
    
    return result

def shrink_white_areas(image: MatLike, radius: int) -> MatLike:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    kernel_size = 2 * radius + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    
    shrunk = cv2.erode(gray, kernel, iterations=1)
    
    result = cv2.cvtColor(shrunk, cv2.COLOR_GRAY2BGR)
    
    return result

def find_contours_containing_boxes(
    image: MatLike,
    target_boxes: list[tuple[int, int, int, int]],
    min_ratio: float = MIN_RATIO,
    max_ratio: float = MAX_RATIO,
) -> list[tuple[int, int, int, int]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    contours, _ = cv2.findContours(gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    matching_contour_boxes = []
    
    for contour in contours:
        contour_x, contour_y, contour_w, contour_h = cv2.boundingRect(contour)
        
        if contour_h == 0:
            continue
        
        aspect_ratio = contour_w / contour_h
        
        if not (min_ratio <= aspect_ratio <= max_ratio):
            continue

        for target_x, target_y, target_w, target_h in target_boxes:
            target_x2 = target_x + target_w
            target_y2 = target_y + target_h
            contour_x2 = contour_x + contour_w
            contour_y2 = contour_y + contour_h
            
            if (contour_x <= target_x and contour_y <= target_y and 
                contour_x2 >= target_x2 and contour_y2 >= target_y2 and
                target_h / contour_h < 0.275):
                matching_contour_boxes.append((contour_x, contour_y, contour_w, contour_h))
                break
    
    return matching_contour_boxes

def detect_player_rows(image: MatLike):
    # replace self indicator background color from yellow to white, which is any other member background color
    p_image = replace_color(image, ROW_SELF_BACKGROUND_COLOR, ROW_BACKGROUND_COLOR, 10)

    headers = remove_noise(create_binary_mask(p_image, [ROW_HEADER_COLOR], 5), 2)
    headers = shrink_white_areas(headers, 1)
    headers = find_white_regions(headers, 0.5, 10, 10)

    p_image = create_binary_mask(p_image, [
        ROW_HEADER_COLOR,
        ROW_BACKGROUND_COLOR,
        ROW_KEY_BACKGROUND,
    ], 5)
    p_image = remove_noise(p_image, 5)
    p_image = expand_white_areas(p_image, 2)
    boxes = find_contours_containing_boxes(p_image, headers)

    return boxes

def resize_image(image: MatLike, height: int) -> MatLike:
    # if the image is screenshoted from mobile, return the original image
    if image.shape[0] / 2 > image.shape[1]:
        return image

    return cv2.resize(image, (int(image.shape[1] * height / image.shape[0]), height))

def fill_area(image: MatLike, area: tuple[int, int, int, int], color: str) -> MatLike:
    x, y, w, h = area
    image[y:y+h, x:x+w] = hex_to_bgr(color)
    return image

def cleanup_image_before_ocr(image: MatLike) -> MatLike:
    # fill the top right corner to be the header color
    # the width will be 0.22% of the image
    # the height will be 0.25% of the image
    w = int(image.shape[1] * 0.23)
    h = int(image.shape[0] * 0.25)
    image = fill_area(image, (image.shape[1] - w, 0, w, h), ROW_HEADER_COLOR)

    # remove the i icon right next to the name
    header_row = crop_image(image, (
        int(image.shape[1] * 0.215),
        int(h * 0.1),
        int(image.shape[1] * 0.8),
        int(h * 0.8),
    ))
    mask = create_binary_mask(header_row, [ICON_I_GRADIENT_TOP_COLOR, ICON_I_GRADIENT_BOTTOM_COLOR], 10)
    mask = expand_white_areas(mask, int(h / 7.5))
    areas = find_white_regions(mask, 0.5, h * 0.5, h * 0.5) # 0.8 for margin of error

    for x, _, w, _ in areas:
        image = fill_area(image, (
            int(image.shape[1] * 0.215 + x),
            0,
            int(image.shape[1] * 0.1 + h),
            h,
        ), ROW_HEADER_COLOR)
    
    return image

def ocr_image(image: MatLike) -> list[str]:
    results = ocr.predict(cleanup_image_before_ocr(image))
    return results[0]["rec_texts"]

def crop_image(image: MatLike, box: tuple[int, int, int, int]):
    x, y, w, h = box
    return image[y:y+h, x:x+w]

def get_optimization_info(image: MatLike):
    step1 = create_binary_mask(image, [CLUB_HEADER_COLOR], 50)
    step2 = remove_noise(step1, 4000)

    boxes = find_white_regions(
        step2,
        0.5,
        10,
        10,
    )

    if len(boxes) == 0:
        return None

    if len(boxes) > 1:
        return None
    
    return boxes[0]

def optimize(image: MatLike):
    resized_image = resize_image(image, 960)
    info = get_optimization_info(resized_image)

    if info is None:
        print('something is wrong')
        return

    return crop_image(resized_image, (
        max(info[0] - 10, 0),
        0,
        min(info[2] + 20, resized_image.shape[1]),
        resized_image.shape[0],
    ))

def to_fps(capture: cv2.VideoCapture, fps: int):
    current_fps = capture.get(cv2.CAP_PROP_FPS)
    frame_skip = int(current_fps / fps)
    frame_count = 0
    while True:
        ret, frame = capture.read()
        if not ret:
            break
        if frame_count % frame_skip == 0:
            yield frame
        frame_count += 1

def parse_only_numbers(text: str) -> int:
    ret = 0
    for ch in text:
        if ch.isdigit():
            ret = ret * 10 + int(ch)
    return ret

def parse_last_login(text: str) -> int:
    num = parse_only_numbers(text)
    if 's' in text:
        return num
    elif 'm' in text:
        return num * 60
    elif 'h' in text:
        return num * 60 * 60
    elif 'd' in text:
        return num * 60 * 60 * 24
    return num

def predict_name(strings: list[str]) -> str:
    return Counter(strings).most_common(1)[0][0]

def reconstruct_paths(edges):
    adj = {}
    indegree = {}
    nodes = set()

    for u, v in edges:
        adj[u] = v
        indegree[v] = indegree.get(v, 0) + 1
        indegree[u] = indegree.get(u, 0)
        nodes.add(u)
        nodes.add(v)

    starts = [n for n in nodes if indegree[n] == 0]

    paths = []
    visited = set()

    for start in starts:
        path = []
        cur = start
        while cur in adj and cur not in visited:
            path.append(cur)
            visited.add(cur)
            cur = adj[cur]
        if cur not in visited:
            path.append(cur)
            visited.add(cur)
        paths.append(path)

    return paths

def get_captured_player_info_images(iter):
    ret = []

    for frame_idx, frame in enumerate(iter):
        optimized_frame = optimize(frame)
        boxes = detect_player_rows(optimized_frame)
        for box in boxes:
            image = crop_image(optimized_frame, box)
            _, y, _, _ = box
            ret.append((image, frame_idx, y))

    return ret

def extract_from_ocr_results(texts: list[str]) -> tuple[bool, tuple[str, str, int, int]]:
    normalized_texts = [' '.join(e.lower().strip().split(' ')) for e in texts]
    try:
        role = normalized_texts[0]
        # maybe username should not be normalized, in case some frame contains reading error we could still vote by majority
        name = ' '.join(texts[1:normalized_texts.index("total fans")]).strip()
        total_fans = parse_only_numbers(normalized_texts[normalized_texts.index("total fans") + 1])
        last_login = parse_last_login(normalized_texts[normalized_texts.index("last login") + 1])

        if name == '':
          return False, None

        return True, (role, name, total_fans, last_login)
    except:
        return False, None

def vote_by_majority(records: dict[str, list[dict[str, int]]]):
    ret = {}
    for name, record_by_frame in records.items():
        # use counter to get the most common values
        role_counter = Counter(e["role"] for e in record_by_frame)
        total_fans_counter = Counter(e["total_fans"] for e in record_by_frame)
        last_login_counter = Counter(e["last_login"] for e in record_by_frame)
        ret[name] = (role_counter.most_common(1)[0][0], total_fans_counter.most_common(1)[0][0], last_login_counter.most_common(1)[0][0])
    return ret

def get_order_relationship(records: dict[str, list[dict[str, int]]]):
    ret = set()

    for k1, first in records.items():
        for k2, second in records.items():
            if k1 == k2:
                break

            if (k1, k2) in ret or (k2, k1) in ret:
                break

            for first_frame in first:
                for second_frame in second:
                    if first_frame["frame_idx"] == second_frame["frame_idx"]:
                        if first_frame["frame_box_y"] < second_frame["frame_box_y"]:
                            ret.add((k1, k2))
                        else:
                            ret.add((k2, k1))
                        break
                else:
                    continue
                break
    return ret

def merge_group_with_same_groundtruth_inplace(records: dict[str, list[dict[str, int]]], groundtruths: dict[str, tuple[str, int, int]]):
    for name, groundtruth in groundtruths.items():
        if name not in records:
            continue

        for name2, groundtruth2 in groundtruths.items():
            if name2 not in records:
                continue
            if name == name2:
                continue

            if groundtruth == groundtruth2:
                # get the lens
                if len(records[name]) > len(records[name2]):
                    records[name].extend(records[name2])
                    del records[name2]
                else:
                    records[name2].extend(records[name])
                    del records[name]

def extract_player_info(images):
    ret: dict[str, list[dict[str, int]]] = {}

    for image, frame_idx, y in images:
        texts = ocr_image(image)
        success, data = extract_from_ocr_results(texts)
        if not success:
            continue

        role, name, total_fans, last_login = data

        if name not in ret:
            ret[name] = []

        ret[name].append({
            "role": role,
            "total_fans": total_fans,
            "last_login": last_login,
            "frame_idx": frame_idx,
            "frame_box_y": y,
        })
    return ret

def extract_video(path: str):
    cap = cv2.VideoCapture(path)

    images = get_captured_player_info_images(to_fps(cap, 12))
    player_data_group_by_name = extract_player_info(images)
    groundtruth_by_group = vote_by_majority(player_data_group_by_name)
    merge_group_with_same_groundtruth_inplace(player_data_group_by_name, groundtruth_by_group)
    order_relationship = get_order_relationship(player_data_group_by_name)
    reconstructed_paths = reconstruct_paths(order_relationship)
    cap.release()

    if len(reconstructed_paths) == 0:
      raise Exception("No reconstructed paths found.")

    return [
      [
        {
          "name": name,
          "role": groundtruth_by_group[name][0],
          "total_fans": groundtruth_by_group[name][1],
          "last_login": groundtruth_by_group[name][2],
        } for name in names
      ] for names in reconstructed_paths
    ]
