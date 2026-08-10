# Layer Forge

> **Project on hold / archived.** 
> A lightweight Python CLI pipeline designed to convert standard raster images into multi-color 3D-printable models (`.3mf` and meshes) optimized for FDM multi-material and layered workflows. Developed for personal use.

---

## Features

- **Automated End-to-End Generation:** Automatically processes images and structures output parameters directly through configuration without requiring complex upfront manual tweaking.
- **Multi-Format Output:** Generates both structured 3D models (`.3mf`) ready for layer-based printing workflows and geometric components.
- **Color Quantization:** Reduces complex image color palettes down to a clean set of target colors ideal for sharp 3D prints.
- **FDM Print Customization:** Fine-tune physical widths, layer heights, base thicknesses, and color layers directly via configuration.

---

## Current Limitations & Status

- **Filament Transparency & Brand Analysis (Not Implemented):** The pipeline does not currently analyze or automatically map real-world manufacturer filament transmission distances (TD) or color transparency into the print sequence. True automated physical blending requires interactive calibration and visual tuning, which remains outside the scope of this prototype.
- **Interactive UI:** Interactive color-mapping controls and visual slicing sliders are omitted in favor of configuration-driven automation.

---

## Inspiration & Sourcing Images

While Layer Forge processes a wide variety of raster images, graphic-heavy, stylized, or high-contrast imagery yields the most striking multi-material results. 

If you need test candidates, you can explore visual collections or automate downloading batches of reference images using [Pinterest-Collector](https://github.com/Lavakoons-n-Peebles/Pinterest-Collector).

---

## Project Structure

The project maintains a modular workspace structure:

```text
Layer Forge/
│
├── defaults/          # Default templates (config.json, filaments.csv, templates)
├── docs/              # Documentation generator metadata and scripts
├── modules/           # Core processing modules (color mapping, config, 3D generator)
├── workspace/         # Active workspace (input images, generated layers, .3mf output)
├── main.py            # Main entry point script
└── README.md          # Project documentation
```

---

## Configuration Reference (`config.json`)

```json
{
  "mode": "full",
  "input": "source.jpg",
  "output_dir": "output_layers",
  "output_format": "stl",
  "colors_count": 4,
  "dither": false,
  "brightness": 0,
  "contrast": 0,
  "print_settings": {
    "width": 50,
    "layer_height": 0.08,
    "base_layers": 4,
    "color_layers": 3,
    "print_order": "auto_by_area",
    "filament_type": "PLA",
    "filament_colors": ["#000000", "#FFFFFF", "#FF0000", "#00FF00"]
  }
}
```

### Configuration Parameters
<!-- TABLE_CONFIG_START -->
<table>
  <colgroup>
    <col style="width: 15%;">
    <col style="width: 10%;">
    <col style="width: 15%;">
    <col style="width: 60%;">
  </colgroup>
  <thead>
    <tr>
      <th>Parameter</th>
      <th>Type</th>
      <th>Default</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>input_image</code></td>
      <td>String</td>
      <td><code>"source.jpg"</code></td>
      <td>Path to the input image file (JPEG, PNG).</td>
    </tr>
    <tr>
      <td><code>output_dir</code></td>
      <td>String</td>
      <td><code>"output_layers"</code></td>
      <td>Target directory where generated masks and previews will be saved.</td>
    </tr>
    <tr>
      <td><code>colors_count</code></td>
      <td>Integer</td>
      <td><code>4</code></td>
      <td>Target number of colors for palette quantization (number of layers).</td>
    </tr>
    <tr>
      <td><code>dither</code></td>
      <td>Boolean</td>
      <td><code>false</code></td>
      <td>Enables (<code>true</code>) or disables (<code>false</code>) Floyd-Steinberg dithering. Set to <code>false</code> for clean, solid graphic boundaries.</td>
    </tr>
    <tr>
      <td><code>brightness</code></td>
      <td>Integer</td>
      <td><code>0</code></td>
      <td>Brightness adjustment percentage (-100 to 100) applied before processing.</td>
    </tr>
    <tr>
      <td><code>contrast</code></td>
      <td>Integer</td>
      <td><code>0</code></td>
      <td>Contrast adjustment percentage (-100 to 100) applied before processing.</td>
    </tr>
    <tr>
      <td colspan="4"><strong>Print Settings (`print_settings`)</strong></td>
    </tr>
    <tr>
      <td style="padding-left: 20px;"><code>layer_height</code></td>
      <td>Float</td>
      <td><code>0.2</code></td>
      <td>Base physical height of a single print layer in millimeters.</td>
    </tr>
    <tr>
      <td style="padding-left: 20px;"><code>base_layers_multiplier</code></td>
      <td>Integer</td>
      <td><code>8</code></td>
      <td>Multiplier for the solid bottom base layers (e.g., 8 x 0.2 mm = 1.6 mm total base thickness).</td>
    </tr>
    <tr>
      <td style="padding-left: 20px;"><code>use_custom_heights</code></td>
      <td>Boolean</td>
      <td><code>false</code></td>
      <td>Enables (<code>true</code>) custom extrusion heights per color layer instead of a uniform thickness.</td>
    </tr>
    <tr>
      <td style="padding-left: 20px;"><code>color_layer_heights</code></td>
      <td>Array</td>
      <td><code>[0.6, 0.4, 0.4, 0.4]</code></td>
      <td>Individual extrusion heights in millimeters for each corresponding color layer when custom heights are active.</td>
    </tr>
    <tr>
      <td style="padding-left: 20px;"><code>ams_mode</code></td>
      <td>Boolean</td>
      <td><code>true</code></td>
      <td>Enables (<code>true</code>) multi-material mode (AMS/MMU) or disables (<code>false</code>) for single-extruder manual color swaps.</td>
    </tr>
    <tr>
      <td style="padding-left: 20px;"><code>print_order</code></td>
      <td>String</td>
      <td><code>"auto_by_area"</code></td>
      <td>Layer printing sequence strategy (<code>"auto_by_area"</code> for largest background masks first, or <code>"sequential"</code> for strict file ordering).</td>
    </tr>
  </tbody>
</table>
<!-- TABLE_CONFIG_END -->

---

## Getting Started

1. **Requirements**
Make sure you have Python installed along with the Pillow library:
```bash
pip install Pillow numpy trimesh
```

2. **Running**
Run the processing pipeline via:
```bash
python main.py
```