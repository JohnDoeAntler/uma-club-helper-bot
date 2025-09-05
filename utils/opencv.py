import numpy as np
import cv2
from cv2.typing import MatLike
from paddleocr import PaddleOCR

# ocr

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

# opencv

def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16) 
    b = int(hex_color[4:6], 16)
    return np.array([b, g, r])

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