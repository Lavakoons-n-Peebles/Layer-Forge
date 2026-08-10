import os
from PIL import Image, ImageEnhance
from modules.config import AppConfig


def quantize_enhance_image(settings: AppConfig) -> str:
    """
    Process the source image applying brightness, contrast, 
    and color quantization, then save it as the base layer image.
    """

    input_path = settings.input

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Error: Input image '{input_path}' not found.")

    print(f"Loading base image from: {input_path}")
    img = Image.open(input_path).convert("RGB")

    # Apply brightness adjustment if needed
    brightness_val = 1.0 + (settings.brightness / 100.0)
    if brightness_val != 1.0:
        print(f"Applying brightness adjustment: {settings.brightness}%")
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness_val)

    # Apply contrast adjustment if needed
    contrast_val = 1.0 + (settings.contrast / 100.0)
    if contrast_val != 1.0:
        print(f"Applying contrast adjustment: {settings.contrast}%")
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_val)

    # Quantize colors based on color count and dithering setting
    colors_count = settings.colors_count
    use_dither = settings.dither
    dither_mode = Image.Dither.FLOYDSTEINBERG if use_dither else Image.Dither.NONE
    
    print(f"Quantizing image to {colors_count} colors (Dithering: {use_dither})")
    quantized_img = img.quantize(colors=colors_count, method=Image.Quantize.MEDIANCUT, dither=dither_mode)
    
    # Save the processed base image for the next stages
    output_dir = settings.output_dir
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "processed_base.png")
    quantized_img.save(output_path)
    
    print(f"Stage 1 Complete: Processed base image saved to '{output_path}'.")
    return output_path


def generate_layer_masks(settings: AppConfig) -> list[str]:
    """Generate individual binary masks for each color layer based on the processed base image."""
    output_dir = settings.output_dir
    base_image_path = os.path.join(output_dir, "processed_base.png")
    
    if not os.path.exists(base_image_path):
        raise FileNotFoundError(
            f"Error: Processed base image not found at '{base_image_path}'. "
            "Please run Stage 1 or use full pipeline mode via main.py."
        )

    print(f"Loading processed base image from: {base_image_path}")
    img = Image.open(base_image_path).convert("P")
    
    colors_count = settings.colors_count
    masks = []
    
    for color_index in range(colors_count):
        mask = img.point(lambda p: 255 if p == color_index else 0, mode="1")
        mask_path = os.path.join(output_dir, f"layer_{color_index}.png")
        mask.save(mask_path)
        masks.append(mask_path)
        
    return masks

