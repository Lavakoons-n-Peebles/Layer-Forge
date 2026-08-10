import numpy as np
import trimesh
import os, shutil, zipfile

from PIL import Image

from modules.image2layers import generate_layer_masks
from modules.config import AppConfig, prepare_path


import os
import shutil
import zipfile
import re
from .config import AppConfig, prepare_path

def save_project(settings: AppConfig, mesh):
    """Save the exported 3D model (STL or 3MF), update 3MF template if needed, and generate guides."""
    filename = generate_model_filename(settings)
    
    if settings.output_format == "stl":
        mesh.export(filename, file_type="stl")
    elif settings.output_format == "3mf":
        # Select template based on layer height
        ps = settings.print_settings
        template_name = f"print_{ps.layer_height}.3mf"
        template_path = os.path.join("defaults", template_name)
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template 3MF not found for layer height {ps.layer_height} at '{template_path}'")
            
        shutil.copy(template_path, filename)
        
        # Update mesh geometry and inject custom gcode
        _update_3mf_template(filename, settings, mesh)
    else:
        raise ValueError(f"Unknown format: {settings.output_format}")
        
    save_color_layers_guide(settings)        
        
    print(f"Saved: {filename}")


def save_color_layers_guide(settings: AppConfig) -> str:
    """Generate a compact text guide mapping color blocks to Z-height ranges in mm."""
    
    ps                  = settings.print_settings
    layer_height        = ps.layer_height
    base_layers         = ps.base_layers
    color_layers_count  = int(ps.color_layers)
    
    lines = [
        "=== 3D Model Print Guide ===",
        f"Layer Height: {layer_height} mm",
        "-" * 40
    ]
    
    # Base Z-range calculation using absolute layer bounds
    base_start_z = 0.0
    base_end_z = base_layers * layer_height
    lines.append(
        f"Z: {base_start_z:.2f} - {base_end_z:.2f} mm "
        f"(Layers 1-{base_layers}) -> Base / Foundation"
    )
    
    current_layer = base_layers
    
    # Color Z-ranges calculation using absolute layer indices to prevent float drift
    for color_idx in range(settings.colors_count):
        if color_layers_count <= 0:
            continue
            
        color_name = (
            ps.filament_colors[color_idx] 
            if color_idx < len(ps.filament_colors) 
            else f"Color #{color_idx + 1}"
        )
        
        start_layer = current_layer + 1
        end_layer = current_layer + color_layers_count
        
        start_z = (start_layer - 1) * layer_height
        end_z = end_layer * layer_height
        
        layer_range_str = f"Layer {start_layer}" if start_layer == end_layer else f"Layers {start_layer}-{end_layer}"
        
        lines.append(f"Z: {start_z:.2f} - {end_z:.2f} mm ({layer_range_str}) -> {color_name}")
        current_layer = end_layer

    base_name, _ = os.path.splitext(os.path.basename(settings.input))
    guide_filename = prepare_path(f"{base_name}_layers_guide.txt")
        
    with open(guide_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"Layer & color guide saved to: {guide_filename}")
    return guide_filename


def generate_model_filename(settings: AppConfig) -> str:
    """Generate a descriptive STL filename with dimensions, total thickness, layer height, and total colors."""
    
    ps = settings.print_settings
    
    color_thickness = settings.colors_count * ps.color_layers * ps.layer_height
    total_thickness = ps.base_layers * ps.layer_height + color_thickness
    base_name, _ = os.path.splitext(os.path.basename(settings.input))
    
    # f"{round(target_width)}x{round(target_height)}x{total_thickness:.2f}_"
    filename = prepare_path(f"{base_name}_{ps.layer_height:.2f}_{settings.colors_count}colors.{settings.output_format}")
    return filename
    

def build_mesh_geometry1(settings: AppConfig):    
    """Build 3D mesh geometry using layer_height, base_layers, and color_layers."""
    
    masks = generate_layer_masks(settings)
    print(f"Successfully generated {len(masks)} layer masks in '{settings.output_dir}'.")
    
    # Load all generated image layer masks into a list of boolean NumPy arrays
    raw_layers = []
    for mask_path in masks:
        with Image.open(mask_path).convert("1") as m:
            m = m.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            raw_layers.append(np.array(m, dtype=bool))
            
    if not raw_layers:
        raise ValueError("Error: No layers found to build geometry.")

    # Determine pixel dimensions from the first layer mask and calculate proportional scale factors
    ref_shape = raw_layers[0].shape  # (height, width)
    img_height, img_width = ref_shape
    
    target_height = settings.print_settings.width * (img_height / img_width)
    scale_x = settings.print_settings.width / img_width
    scale_y = target_height / img_height
    
    num_layers = len(raw_layers)
    color_layers_counts = [int(settings.print_settings.color_layers)] * num_layers
        
    solid_base = np.ones(ref_shape, dtype=bool)
    base_stack = [solid_base] * settings.print_settings.base_layers
    
    color_stack = []
    current_union = np.zeros(ref_shape, dtype=bool)
    
    for i in range(num_layers - 1, -1, -1):
        layer = raw_layers[i]
        if layer.shape != ref_shape:
            raise ValueError(f"Layer shape mismatch: {layer.shape} vs expected {ref_shape}")
            
        current_union = np.logical_or(current_union, layer)
        
        repeat_count = color_layers_counts[i] if i < len(color_layers_counts) else 1
        for _ in range(repeat_count):
            color_stack.insert(0, current_union.copy())
        
    all_voxel_planes = base_stack + color_stack
    
    volume = np.stack(all_voxel_planes, axis=0)
    
    if not volume.any():
        raise ValueError("Error: Generated volume is completely empty, no geometry to build.")

    volume_xyz = np.transpose(volume, (2, 1, 0))

    voxels = trimesh.voxel.VoxelGrid(volume_xyz)
    mesh = voxels.marching_cubes
    
    transform_matrix = np.array([
        [scale_x, 0, 0, 0],
        [0, scale_y, 0, 0],
        [0, 0, settings.print_settings.layer_height, 0],
        [0, 0, 0, 1]
    ])
    mesh.apply_transform(transform_matrix)
    
    current_z_min = mesh.bounds[0][2]
    mesh.apply_translation([0, 0, -current_z_min])
    
    return mesh


def build_mesh_geometry2(settings: AppConfig):
    """Build a clean 2.5D surface mesh with correct color height steps."""
    
    # Still generate masks if other parts of the pipeline expect them to exist
    masks = generate_layer_masks(settings)
    print(f"Successfully generated {len(masks)} layer masks in '{settings.output_dir}'.")
    
    base_image_path = os.path.join(settings.output_dir, "processed_base.png")
    img = Image.open(base_image_path).convert("P")
    img_array = np.array(img)
    
    # Mirror horizontally to match the previous coordinate space
    img_array = np.fliplr(img_array)
    
    ref_shape = img_array.shape  # (height, width)
    img_height, img_width = ref_shape
    
    target_height = settings.print_settings.width * (img_height / img_width)
    scale_x = settings.print_settings.width / img_width
    scale_y = target_height / img_height
    layer_height = settings.print_settings.layer_height
    base_layers = settings.print_settings.base_layers
    color_layers = int(getattr(settings.print_settings, "color_layers", 1))

    # Build height map directly from color indices (higher index = higher Z position)
    # Base foundation + proportional height per color index
    height_map = base_layers + (img_array.astype(np.float32) + 1) * color_layers
    
    # Scale height values to physical units (mm)
    z_grid = height_map * layer_height

    # Generate vertices and faces for a lightweight 2.5D surface grid
    H, W = ref_shape
    x_indices = np.arange(W, dtype=np.float32) * scale_x
    y_indices = np.arange(H, dtype=np.float32) * scale_y
    xx, yy = np.meshgrid(x_indices, y_indices)
    
    top_vertices = np.stack([xx.ravel(), yy.ravel(), z_grid.ravel()], axis=-1)
    
    v_indices = np.arange(H * W).reshape((H, W))
    faces = []
    
    for y_idx in range(H - 1):
        for x_idx in range(W - 1):
            v0 = v_indices[y_idx, x_idx]
            v1 = v_indices[y_idx, x_idx + 1]
            v2 = v_indices[y_idx + 1, x_idx]
            v3 = v_indices[y_idx + 1, x_idx + 1]
            
            # Triangle 1
            faces.append([v0, v2, v1])
            # Triangle 2
            faces.append([v1, v2, v3])
            
    mesh = trimesh.Trimesh(vertices=top_vertices, faces=np.array(faces), process=False)
    
    # Shift to zero base
    current_z_min = mesh.bounds[0][2]
    mesh.apply_translation([0, 0, -current_z_min])
    
    return mesh

def build_mesh_geometry(settings: AppConfig):
    """Build a watertight 2.5D surface mesh with smooth tone transitions 
    for a multi-tone palette (black, gray, brown, white).
    """
    
    base_image_path = os.path.join(settings.output_dir, "processed_base.png")
    if not os.path.exists(base_image_path):
        raise FileNotFoundError(f"Processed base image not found at '{base_image_path}'.")

    img = Image.open(base_image_path).convert("P")
    img_array = np.array(img)
    
    # Mirror horizontally to match coordinate space
    img_array = np.fliplr(img_array)
    
    ref_shape = img_array.shape  # (height, width)
    H, W = ref_shape
    
    target_height = settings.print_settings.width * (H / W)
    scale_x = settings.print_settings.width / W
    scale_y = target_height / H
    layer_height = settings.print_settings.layer_height
    base_layers = settings.print_settings.base_layers
    color_layers = int(getattr(settings.print_settings, "color_layers", 4))

    # 1. Map color tones smoothly instead of flat blocks
    # Convert palette indices into a normalized float gradient (0.0 to 1.0)
    img_float = img_array.astype(np.float32)
    max_val = img_float.max()
    if max_val > 0:
        normalized_tones = img_float / max_val
    else:
        normalized_tones = np.zeros_like(img_float)

    # Total height span dedicated to the tone variations based on color_layers
    unique_indices = np.unique(img_array)
    total_tone_steps = max(len(unique_indices) * color_layers, color_layers * 4)

    # Height map: solid base + smooth continuous tone gradient on top
    height_map = base_layers + (normalized_tones * total_tone_steps)
    z_grid = height_map * layer_height

    # 2. Fast grid mesh creation using vectorized numpy operations
    x_indices = np.arange(W, dtype=np.float32) * scale_x
    y_indices = np.arange(H, dtype=np.float32) * scale_y
    xx, yy = np.meshgrid(x_indices, y_indices)
    
    top_vertices = np.stack([xx.ravel(), yy.ravel(), z_grid.ravel()], axis=-1)
    bottom_z = 0.0
    bottom_vertices = np.stack([xx.ravel(), yy.ravel(), np.full(H * W, bottom_z, dtype=np.float32)], axis=-1)
    
    vertices = np.vstack([top_vertices, bottom_vertices])
    
    # Generate face indices using vectorized grid layout
    v_top = np.arange(H * W).reshape((H, W))
    v_bot = v_top + (H * W)
    
    # Top and bottom faces
    t0 = v_top[:-1, :-1].ravel()
    t1 = v_top[:-1, 1:].ravel()
    t2 = v_top[1:, :-1].ravel()
    t3 = v_top[1:, 1:].ravel()
    
    top_faces = np.column_stack([t0, t2, t1])
    top_faces_2 = np.column_stack([t1, t2, t3])
    
    b0 = v_bot[:-1, :-1].ravel()
    b1 = v_bot[:-1, 1:].ravel()
    b2 = v_bot[1:, :-1].ravel()
    b3 = v_bot[1:, 1:].ravel()
    
    bot_faces = np.column_stack([b0, b1, b2])
    bot_faces_2 = np.column_stack([b1, b3, b2])
    
    # Side walls (Edges closing the mesh)
    w_top_0_t0 = v_top[0, :-1]
    w_top_0_t1 = v_top[0, 1:]
    w_bot_0_b0 = v_bot[0, :-1]
    w_bot_0_b1 = v_bot[0, 1:]
    wall_faces_1 = np.column_stack([w_top_0_t0, w_bot_0_b0, w_top_0_t1])
    wall_faces_2 = np.column_stack([w_top_0_t1, w_bot_0_b0, w_bot_0_b1])

    w_top_h_t0 = v_top[H-1, :-1]
    w_top_h_t1 = v_top[H-1, 1:]
    w_bot_h_b0 = v_bot[H-1, :-1]
    w_bot_h_b1 = v_bot[H-1, 1:]
    wall_faces_3 = np.column_stack([w_top_h_t0, w_top_h_t1, w_bot_h_b0])
    wall_faces_4 = np.column_stack([w_top_h_t1, w_bot_h_b1, w_bot_h_b0])

    w_top_c0_t0 = v_top[:-1, 0]
    w_top_c0_t1 = v_top[1:, 0]
    w_bot_c0_b0 = v_bot[:-1, 0]
    w_bot_c0_b1 = v_bot[1:, 0]
    wall_faces_5 = np.column_stack([w_top_c0_t0, w_top_c0_t1, w_bot_c0_b0])
    wall_faces_6 = np.column_stack([w_top_c0_t1, w_bot_c0_b1, w_bot_c0_b0])

    w_top_cw_t0 = v_top[:-1, W-1]
    w_top_cw_t1 = v_top[1:, W-1]
    w_bot_cw_b0 = v_bot[:-1, W-1]
    w_bot_cw_b1 = v_bot[1:, W-1]
    wall_faces_7 = np.column_stack([w_top_cw_t0, w_bot_cw_b0, w_top_cw_t1])
    wall_faces_8 = np.column_stack([w_top_cw_t1, w_bot_cw_b0, w_bot_cw_b1])

    faces = np.vstack([
        top_faces, top_faces_2,
        bot_faces, bot_faces_2,
        wall_faces_1, wall_faces_2,
        wall_faces_3, wall_faces_4,
        wall_faces_5, wall_faces_6,
        wall_faces_7, wall_faces_8
    ])

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.fix_normals()
    
    current_z_min = mesh.bounds[0][2]
    mesh.apply_translation([0, 0, -current_z_min])
    
    return mesh


def create_3D_model(settings: AppConfig):
    """Package layers into a 3MF/STL file using the selected GEOMETRY_BACKEND based strictly on passed settings."""

    print(f"Building geometry (Width: {settings.print_settings.width}mm, Base Layers: {settings.print_settings.base_layers})...")

    mesh = build_mesh_geometry(settings)
    mesh.metadata['filament_type']      = settings.print_settings.filament_type
    mesh.metadata['filament_colors']    = settings.print_settings.filament_colors

    print(f"Exporting mesh with {settings.print_settings.filament_type} profile")
    
    save_project(settings, mesh)
        
    print("Stage 2 Complete: Successfully created model.")


def _update_3mf_template(output_path: str, settings: AppConfig, mesh):
    """Unpack template 3MF, replace mesh geometry in object file, update custom gcode, and repack."""
    temp_dir = output_path + "_temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Extract template 3MF archive
    with zipfile.ZipFile(output_path, 'r') as zf:
        zf.extractall(temp_dir)
        
    # Export current mesh to a temporary 3mf to extract its raw mesh structure
    temp_mesh_3mf = output_path + "_mesh.3mf"
    mesh.export(temp_mesh_3mf, file_type="3mf")
    
    temp_mesh_dir = output_path + "_mesh_temp"
    os.makedirs(temp_mesh_dir, exist_ok=True)
    with zipfile.ZipFile(temp_mesh_3mf, 'r') as zf:
        zf.extractall(temp_mesh_dir)
        
    # Read the exported mesh model content
    exported_model_path = os.path.join(temp_mesh_dir, "3D", "3dmodel.model")
    mesh_block = ""
    if os.path.exists(exported_model_path):
        with open(exported_model_path, "r", encoding="utf-8") as f:
            exported_content = f.read()
            mesh_match = re.search(r'(<mesh>.*?</mesh>)', exported_content, re.DOTALL)
            if mesh_match:
                mesh_block = mesh_match.group(1)
                
    # Clean up temporary mesh files
    shutil.rmtree(temp_mesh_dir, ignore_errors=True)
    if os.path.exists(temp_mesh_3mf):
        os.remove(temp_mesh_3mf)
        
    # Find and update the object model file inside the template structure
    objects_dir = os.path.join(temp_dir, "3D", "Objects")
    if os.path.exists(objects_dir) and mesh_block:
        object_files = [f for f in os.listdir(objects_dir) if f.endswith(".model")]
        if object_files:
            target_object_path = os.path.join(objects_dir, object_files[0])
            with open(target_object_path, "r", encoding="utf-8") as f:
                template_obj_content = f.read()
                
            updated_obj_content = re.sub(r'<mesh>.*?</mesh>', mesh_block, template_obj_content, flags=re.DOTALL)
            
            with open(target_object_path, "w", encoding="utf-8") as f:
                f.write(updated_obj_content)
                
    # Inject/Update Metadata/custom_gcode_per_layer.xml
    _inject_custom_gcode_xml(temp_dir, settings)
    
    # Update Metadata/model_settings.config
    config_path = os.path.join(temp_dir, "Metadata", "model_settings.config")
    if os.path.exists(config_path):
        model_name = os.path.splitext(os.path.basename(output_path))[0]
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("OBJECT_NAME", model_name)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)    
    
    # Repack everything back into the 3MF zip file with forward slashes
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, temp_dir).replace("\\", "/")
                zf.write(full_path, relative_path)
                
    shutil.rmtree(temp_dir, ignore_errors=True)
    
def _inject_custom_gcode_xml(temp_dir: str, settings: AppConfig):
    """Generate and write custom_gcode_per_layer.xml inside Metadata folder, including base layer changes."""
    ps = settings.print_settings
    layer_height = ps.layer_height
    base_layers = ps.base_layers
    color_layers_count = int(ps.color_layers)
    
    current_z = 0.0
    layers_xml = []
    
    total_layers = base_layers + (settings.colors_count * color_layers_count)
    prev_extruder = None
    
    # Get base extruder and color (default to extruder 1 and first filament color if available)
    base_extruder = getattr(ps, "base_extruder", 1)
    base_color = (
        ps.filament_colors[0] if (hasattr(ps, "filament_colors") and ps.filament_colors) 
        else "#000000"
    )
    if not base_color.startswith("#"):
        base_color = f"#{base_color}"

    for layer_idx in range(1, total_layers + 1):
        current_z += layer_height
        
        # Determine extruder and color for the current layer
        if layer_idx <= base_layers:
            extruder_id = base_extruder
            color_hex = base_color
        else:
            color_idx = (layer_idx - base_layers - 1) // color_layers_count
            if color_idx >= settings.colors_count:
                color_idx = settings.colors_count - 1
            # Color extruders usually start after base, or use 1-indexed mapping
            extruder_id = color_idx + 1
            color_hex = (
                ps.filament_colors[color_idx] 
                if color_idx < len(ps.filament_colors) 
                else "#FFFFFF"
            )
            
        if not color_hex.startswith("#"):
            color_hex = f"#{color_hex}"
            
        # Add a tool_change entry when the extruder/color changes
        if prev_extruder is not None and extruder_id != prev_extruder:
            top_z_str = f"{current_z:.16f}"
            layers_xml.append(
                f'<layer top_z="{top_z_str}" type="2" extruder="{extruder_id}" '
                f'color="{color_hex}" extra="" gcode="tool_change"/>'
            )
            
        prev_extruder = extruder_id
        
    xml_content = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<custom_gcodes_per_layer>',
        '<plate>',
        '<plate_info id="1"/>'
    ]
    xml_content.extend(layers_xml)
    xml_content.extend([
        '<mode value="MultiAsSingle"/>',
        '</plate>',
        '</custom_gcodes_per_layer>'
    ])
    
    metadata_dir = os.path.join(temp_dir, "Metadata")
    os.makedirs(metadata_dir, exist_ok=True)
    xml_path = os.path.join(metadata_dir, "custom_gcode_per_layer.xml")
    
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write("\n".join(xml_content))