import cv2
import numpy as np
from PIL import Image

def is_within_geofence(lat, lng):
    # Studio Home Base (Fotogenic Studio, Mickey Leland St, Addis Ababa)
    STUDIO_LAT, STUDIO_LNG = 9.011556, 38.781258
    
    # Haversine formula for distance in kilometers
    R = 6371.0
    lat1 = np.radians(STUDIO_LAT)
    lng1 = np.radians(STUDIO_LNG)
    lat2 = np.radians(lat)
    lng2 = np.radians(lng)
    
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    distance = R * c
    
    # 25km Geofence limit
    return distance <= 25.0, distance

def compare_photos(baseline_path, return_path):
    """
    Compares baseline and return photos using OpenCV, calculates damage score,
    highlights differences, and classifies the specific type of damage.
    Returns: (highlighted_image_pil, damage_score_float, damage_type_str, description_str)
    """
    try:
        # Load images
        img1 = cv2.imread(baseline_path)
        img2 = cv2.imread(return_path)
        
        if img1 is None or img2 is None:
            return None, 0.0, "Normal", "Could not load images for comparison."
            
        # Resize to standard dimensions for accurate comparison
        img1 = cv2.resize(img1, (600, 600))
        img2 = cv2.resize(img2, (600, 600))
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Compute absolute difference
        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, 35, 255, cv2.THRESH_BINARY)
        
        # Calculate percentage of changed pixels (damage score)
        non_zero_count = np.count_nonzero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        damage_score = round((non_zero_count / total_pixels) * 100, 2)
        
        # Contour analysis to classify damage type
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        damage_type = "Normal / Clean"
        description = "No significant changes detected compared to baseline."
        
        if damage_score > 1.0:
            max_contour_area = max([cv2.contourArea(c) for c in contours]) if contours else 0
            num_contours = len(contours)
            
            # Heuristic classification based on contour shapes and spread
            if max_contour_area > 800:
                damage_type = "🔴 Body Dent / Heavy Impact"
                description = "Large structural deformity or major surface impact detected on chassis."
            elif num_contours > 15 and damage_score < 5.0:
                damage_type = "🟡 Surface Dust / Smudge"
                description = "Multiple small scattered particles or smudges detected (can likely be wiped clean)."
            elif any(cv2.arcLength(c, True) > 100 and cv2.contourArea(c) < 200 for c in contours):
                damage_type = "🟠 Lens Scratch / Linear Abrasion"
                description = "Thin linear mark or scratch detected on glass or optical element."
            else:
                damage_type = "🟠 Moderate Wear / Surface Mark"
                description = "Localized scuff mark or surface wear detected."
        
        # Highlight differences on the return image
        highlighted = img2.copy()
        for c in contours:
            if cv2.contourArea(c) > 20:
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(highlighted, (x, y), (x + w, y + h), (0, 0, 255), 2)
                
        highlighted_rgb = cv2.cvtColor(highlighted, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(highlighted_rgb)
        
        return pil_img, damage_score, damage_type, description
        
    except Exception as e:
        print("Image comparison error:", e)
        return None, 0.0, "Analysis Error", str(e)
