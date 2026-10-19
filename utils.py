import math
import cv2
import numpy as np
from PIL import Image

def calculate_distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_within_geofence(lat, lon, center_lat=9.0107, center_lon=38.7612, radius_km=25.0):
    distance = calculate_distance_km(center_lat, center_lon, lat, lon)
    return distance <= radius_km, distance

def compare_photos(baseline_img_path, return_img_path):
    try:
        img1 = cv2.imread(baseline_img_path)
        img2 = cv2.imread(return_img_path)
        if img1 is None or img2 is None:
            return None, 0.0
        
        # Align image sizes for pixel comparison
        img1 = cv2.resize(img1, (500, 500))
        img2 = cv2.resize(img2, (500, 500))
        
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Compute absolute difference between baseline and return image
        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, 35, 255, cv2.THRESH_BINARY)
        
        # Highlight changed/damaged pixels in bright red on the return image
        highlighted = img2.copy()
        highlighted[thresh > 0] = [0, 0, 255]
        
        non_zero_count = np.count_nonzero(thresh)
        total_pixels = thresh.size
        damage_score = round((non_zero_count / total_pixels) * 100, 2)
        
        highlighted_rgb = cv2.cvtColor(highlighted, cv2.COLOR_BGR2RGB)
        return Image.fromarray(highlighted_rgb), damage_score
    except Exception as e:
        return None, 0.0