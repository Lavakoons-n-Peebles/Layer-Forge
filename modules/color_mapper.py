import csv
import math
from PIL import Image

# def get_dominant_filament_colors(image_path, total_colors):
#     """Analyze the image and extract palette colors as HEX codes."""
#     img = Image.open(image_path).convert("P")
#     palette = img.getpalette() # Получаем палитру изображения (список RGBRGB...)
    
#     colors = []
#     # Извлекаем первые total_colors цветов из палитры изображения
#     for i in range(total_colors):
#         r = palette[i * 3]
#         g = palette[i * 3 + 1]
#         b = palette[i * 3 + 2]
#         hex_color = f"#{r:02X}{g:02X}{b:02X}"
#         colors.append(hex_color)
        
#     return colors

def load_filament_palette(csv_path):
    filaments = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hx = row["hex"].lstrip("#")
            rgb = tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))
            filaments.append({"name": row["name"], "rgb": rgb, "hex": f"#{hx}"})
    return filaments

def closest_color(rgb, filaments):
    r, g, b = rgb
    min_dist = float("inf")
    best_match = filaments[0]
    
    for f in filaments:
        fr, fg, fb = f["rgb"]
        dist = math.sqrt((r - fr) ** 2 + (g - fg) ** 2 + (b - fb) ** 2)
        if dist < min_dist:
            min_dist = dist
            best_match = f
            
    return best_match

def map_image_to_filaments(image_path, csv_path, total_colors):
    filaments = load_filament_palette(csv_path)
    
    img = Image.open(image_path).convert("P")
    palette = img.getpalette()
    
    new_palette = []
    mapped_filament_names = []
    
    for i in range(total_colors):
        orig_rgb = (palette[i*3], palette[i*3+1], palette[i*3+2])
        match = closest_color(orig_rgb, filaments)
        
        new_palette.extend(match["rgb"])
        mapped_filament_names.append(match["name"])
        
    new_palette.extend([0] * (768 - len(new_palette)))
    
    img.putpalette(new_palette)
    img.save(image_path)
    
    return mapped_filament_names