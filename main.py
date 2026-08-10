import argparse

from modules.config import load_settings, prepare_path
from modules.image2layers import quantize_enhance_image
from modules.generator3D import create_3D_model

DEFAULT_CONFIG = prepare_path("config.json")


def parse_arguments():
    """Parse command line arguments with the highest priority."""
    parser = argparse.ArgumentParser(description="LayerForge 3D Multi-Color Generator")
    parser.add_argument("--mode",          "-m", type=str,    help="Mode (full, image_only, model_only)")
    parser.add_argument("--input",         "-i", type=str,    help="Path to input image")
    parser.add_argument("--output",        "-o", type=str,    help="Name of output file")
    parser.add_argument("--output_format", "-f", type=str,    help="File format (stl/3mf)")
    parser.add_argument("--output_dir",    "-d", type=str,    help="Directory for layers output")
    parser.add_argument("--width",         "-w", type=float,  help="Model width")
    parser.add_argument("--base_layers",   "-b", type=float,  help="Base layers")
    parser.add_argument("--config",        "-c", type=str,    help="Configuration file")
    return parser.parse_args()


def main():
    args = parse_arguments()
    config  = prepare_path(args.config) if args.config else DEFAULT_CONFIG

    settings = load_settings(config)
    
    if args.mode is not None:
        settings.mode = args.mode
    if args.input is not None:
        settings.input = args.input
    if args.output_dir is not None:
        settings.output_dir = args.output_dir
    if args.output_format is not None:
        settings.output_format = args.output_format
    if args.width is not None:
        settings.print_settings.width = args.width
    if args.base_layers is not None:
        settings.print_settings.base_layers = args.base_layers

    print("--- Starting pipeline ---")
    print(f"Input image : {settings.input}")

    settings.input      = prepare_path(settings.input)
    settings.output_dir = prepare_path(settings.output_dir)

    # image_only
    if settings.mode == "full" or settings.mode == "image_only":
        quantize_enhance_image(settings)

    # model_only
    if settings.mode == "full" or settings.mode == "model_only":
        create_3D_model(settings)
    
    print("--- Pipeline finished successfully ---")

if __name__ == "__main__":
    main()