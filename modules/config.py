from dataclasses import dataclass, field
from typing import List
import json
import os

DEFAULT_CONFIG = "../defaults/config.json"
USER_WORKSPACE = "workspace"

@dataclass
class PrintSettings:
    width:          float   = 50
    layer_height:   float   = 0.08
    base_layers:    int     = 4
    color_layers:   int     = 3
    print_order:    str     = "auto_by_area"
    filament_type:  str     = "PLA"
    filament_colors: List[str] = field(default_factory=lambda: ["#000000", "#FFFFFF", "#FF0000", "#00FF00"])

@dataclass
class AppConfig:
    mode:           str  = "full"
    input:          str  = "source.jpg"
    output_dir:     str  = "output_layers"
    output_format:  str  = "stl"
    colors_count:   int  = 4
    dither:         bool = False
    brightness:     int  = 0
    contrast:       int  = 0
    print_settings: PrintSettings = field(default_factory=PrintSettings)


def load_settings(config_path) -> AppConfig:
    """Load settings and return a typed AppConfig object."""
    config = AppConfig()

    if not os.path.exists(config_path):
        config_path = DEFAULT_CONFIG
        
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                
                # Populate main config fields
                for key, value in data.items():
                    if key == "print_settings" and isinstance(value, dict):
                        for sub_key, sub_val in value.items():
                            if hasattr(config.print_settings, sub_key):
                                setattr(config.print_settings, sub_key, sub_val)
                    elif hasattr(config, key):
                        setattr(config, key, value)
                        
            except json.JSONDecodeError as e:
                print(f"Error parsing configuration file: {e}. Using defaults.")
    else:
        print(f"Configuration file '{config_path}' not found. Using defaults.")
        
    return config

def prepare_path(path):
    res = path if os.path.isabs(path) else os.path.join(USER_WORKSPACE, path)
    return res 
