import bpy
import json
import sys
import os
import math

def clear_scene():
    """Remove all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Clear all mesh data
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    
    for curve in bpy.data.curves:
        bpy.data.curves.remove(curve)

def create_ring(inner_radius=2.0, outer_radius=2.5, height=0.5):
    """Create a 3D ring using cylinder primitive"""
    
    # Create outer cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        radius=outer_radius,
        depth=height,
        location=(0, 0, 0)
    )
    outer_cylinder = bpy.context.active_object
    outer_cylinder.name = "Ring_Outer"
    
    # Create inner cylinder (to subtract)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=inner_radius,
        depth=height * 1.1,  # Slightly taller to ensure clean cut
        location=(0, 0, 0)
    )
    inner_cylinder = bpy.context.active_object
    inner_cylinder.name = "Ring_Inner"
    
    # Apply boolean modifier to create the ring
    modifier = outer_cylinder.modifiers.new(name="Boolean", type='BOOLEAN')
    modifier.operation = 'DIFFERENCE'
    modifier.object = inner_cylinder
    
    # Apply the modifier
    bpy.context.view_layer.objects.active = outer_cylinder
    bpy.ops.object.modifier_apply(modifier="Boolean")
    
    # Delete the inner cylinder
    bpy.data.objects.remove(inner_cylinder, do_unlink=True)
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    return outer_cylinder

def create_curved_text(text="CUSTOM TEXT", radius=2.25, font_size=0.3, extrude_depth=0.1, font_path=None, letter_spacing=0.1):
    """Create 3D text that curves around the ring with adjustable letter spacing"""
    
    # Create a parent empty for all text letters
    text_parent = bpy.data.objects.new("TextParent", None)
    bpy.context.collection.objects.link(text_parent)
    
    # Calculate the total arc length needed for the text
    # This is approximate - you may need to adjust based on font
    base_letter_width = font_size * 0.6  # Approximate letter width
    total_width = len(text) * base_letter_width + (len(text) - 1) * letter_spacing
    
    # Calculate angle per unit length
    angle_per_unit = 360.0 / (2 * math.pi * radius)
    
    # Calculate total angle needed for text
    total_angle = total_width * angle_per_unit
    
    # Starting angle (center the text)
    start_angle = -total_angle / 2
    
    # Create individual letters
    current_angle = start_angle
    all_letters = []
    
    for i, char in enumerate(text):
        if char == ' ':
            # Skip space but add to angle
            current_angle += (base_letter_width + letter_spacing) * angle_per_unit
            continue
            
        # Create text object for single character
        char_curve = bpy.data.curves.new(name=f"Char_{i}", type='FONT')
        char_obj = bpy.data.objects.new(name=f"Char_{i}", object_data=char_curve)
        bpy.context.collection.objects.link(char_obj)
        
        # Set text properties
        char_curve.body = char
        char_curve.size = font_size
        char_curve.extrude = extrude_depth
        char_curve.bevel_depth = 0.02
        char_curve.bevel_resolution = 2
        char_curve.align_x = 'CENTER'
        char_curve.align_y = 'CENTER'
        
        # Load custom font if provided
        if font_path:
            try:
                font = bpy.data.fonts.load(font_path)
                char_curve.font = font
            except:
                print(f"Could not load font from {font_path}, using default")
        
        # Position the character
        angle_rad = math.radians(current_angle)
        x = radius * math.cos(angle_rad)
        y = radius * math.sin(angle_rad)
        
        char_obj.location = (x, y, 0.25)
        
        # Rotate to face outward from center
        char_obj.rotation_euler = (0, 0, angle_rad - math.pi/2)
        
        # Parent to the text parent
        char_obj.parent = text_parent
        
        all_letters.append(char_obj)
        
        # Calculate approximate width of this character
        # This is simplified - for better results, you'd measure the actual character width
        if char.upper() in ['I', 'J', 'L']:
            char_width = base_letter_width * 0.5
        elif char.upper() in ['M', 'W']:
            char_width = base_letter_width * 1.5
        else:
            char_width = base_letter_width
            
        # Move to next character position
        current_angle += (char_width + letter_spacing) * angle_per_unit
    
    return text_parent, all_letters

def create_curved_text_single_object(text="CUSTOM TEXT", radius=2.25, font_size=0.3, extrude_depth=0.1, font_path=None, letter_spacing=0.1):
    """Alternative method: Create 3D text as a single object with letter spacing"""
    
    # Create text object
    text_curve = bpy.data.curves.new(name="RingText", type='FONT')
    text_obj = bpy.data.objects.new(name="RingText", object_data=text_curve)
    bpy.context.collection.objects.link(text_obj)
    
    # Set text properties
    text_curve.body = text
    text_curve.size = font_size
    text_curve.extrude = extrude_depth
    text_curve.bevel_depth = 0.02
    text_curve.bevel_resolution = 2
    
    # Set letter spacing
    text_curve.space_character = 1.0 + letter_spacing / font_size
    text_curve.space_word = 1.0 + letter_spacing / font_size
    
    # Load custom font if provided
    if font_path:
        try:
            font = bpy.data.fonts.load(font_path)
            text_curve.font = font
        except:
            print(f"Could not load font from {font_path}, using default")
    
    # Create a bezier circle for the text to follow
    bpy.ops.curve.primitive_bezier_circle_add(radius=radius, location=(0, 0, 0))
    curve_circle = bpy.context.active_object
    curve_circle.name = "TextPath"
    
    # Make text follow the curve
    text_obj.select_set(True)
    bpy.context.view_layer.objects.active = text_obj
    
    # Add curve modifier to text
    curve_modifier = text_obj.modifiers.new(name="Curve", type='CURVE')
    curve_modifier.object = curve_circle
    
    # Center text on the curve
    text_curve.align_x = 'CENTER'
    text_curve.align_y = 'CENTER'
    
    # Position text at ring height
    text_obj.location.z = 0.25
    
    return text_obj, curve_circle

def add_materials(ring, text_objects):
    """Add materials to ring and text"""
    
    # Create ring material
    ring_mat = bpy.data.materials.new(name="RingMaterial")
    ring_mat.use_nodes = True
    ring_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.8, 0.7, 0.3, 1.0)  # Gold color
    ring_mat.node_tree.nodes["Principled BSDF"].inputs[4].default_value = 1.0  # Metallic
    ring_mat.node_tree.nodes["Principled BSDF"].inputs[7].default_value = 0.2  # Roughness
    
    # Create text material
    text_mat = bpy.data.materials.new(name="TextMaterial")
    text_mat.use_nodes = True
    text_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.1, 0.1, 0.1, 1.0)  # Dark color
    text_mat.node_tree.nodes["Principled BSDF"].inputs[7].default_value = 0.5  # Roughness
    
    # Assign materials
    ring.data.materials.append(ring_mat)
    
    # Handle both single text object and multiple letter objects
    if isinstance(text_objects, list):
        for text_obj in text_objects:
            if hasattr(text_obj, 'data') and hasattr(text_obj.data, 'materials'):
                text_obj.data.materials.append(text_mat)
    else:
        if hasattr(text_objects, 'data') and hasattr(text_objects.data, 'materials'):
            text_objects.data.materials.append(text_mat)

def export_result(filepath="ring_with_text.stl"):
    """Export the final result"""
    # For Blender 3.0+
    try:
        bpy.ops.wm.stl_export(filepath=filepath,
                              export_selected_objects=False,
                              ascii_format=False,
                              apply_modifiers=True)
    except AttributeError:
        # For Blender 2.8x - 2.9x
        try:
            bpy.ops.export_mesh.stl(filepath=filepath,
                                    use_selection=False,
                                    use_mesh_modifiers=True,
                                    ascii=False)
        except AttributeError:
            # For older versions or as a fallback
            bpy.ops.export_scene.stl(filepath=filepath,
                                     use_selection=False,
                                     use_mesh_modifiers=True,
                                     ascii=False)

    print(f"Exported to {filepath}")

def create_ring_with_text(
    text="CUSTOM RING",
    inner_radius=2.0,
    outer_radius=2.5,
    ring_height=0.5,
    font_size=0.3,
    text_extrude=0.1,
    font_path=None,
    letter_spacing=0.1,
    output_path="ring_with_text.stl",
    use_individual_letters=False
):
    """
    Main function to create a ring with custom text
    
    Parameters:
    -----------
    text : str
        The text to display on the ring
    inner_radius : float
        Inner radius of the ring
    outer_radius : float
        Outer radius of the ring
    ring_height : float
        Height/thickness of the ring
    font_size : float
        Size of the text
    text_extrude : float
        Extrusion depth of the text
    font_path : str
        Path to custom font file (optional)
    letter_spacing : float
        Distance between letters
    output_path : str
        Path for the exported file
    use_individual_letters : bool
        If True, create each letter as a separate object (more control but slower)
    """
    
    # Clear the scene
    clear_scene()
    
    # Create the ring
    ring = create_ring(inner_radius, outer_radius, ring_height)
    
    # Create curved text
    if use_individual_letters:
        text_parent, text_objects = create_curved_text(
            text=text,
            radius=(inner_radius + outer_radius) / 2,
            font_size=font_size,
            extrude_depth=text_extrude,
            font_path=font_path,
            letter_spacing=letter_spacing
        )
        # Add materials
        add_materials(ring, text_objects)
    else:
        text_obj, text_path = create_curved_text_single_object(
            text=text,
            radius=(inner_radius + outer_radius) / 2,
            font_size=font_size,
            extrude_depth=text_extrude,
            font_path=font_path,
            letter_spacing=letter_spacing
        )
        # Add materials
        add_materials(ring, text_obj)
    
    # Export the result
    export_result(output_path)
    
    return ring

def create_customizable_ring_from_config(config_file):
    """Load configuration from JSON and create ring"""
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Extract parameters
    text_config = config.get('text', {})
    ring_config = config.get('ring', {})
    export_config = config.get('export', {})
    
    # Create the ring with text using configuration
    create_ring_with_text(
        text=text_config.get('content', 'CUSTOM RING'),
        inner_radius=ring_config.get('inner_radius', 2.0),
        outer_radius=ring_config.get('outer_radius', 2.5),
        ring_height=ring_config.get('height', 0.5),
        font_size=text_config.get('size', 0.3),
        text_extrude=text_config.get('extrude', 0.1),
        font_path=text_config.get('font_path'),
        letter_spacing=text_config.get('letter_spacing', 0.1),
        output_path=export_config.get('output_path', 'ring.stl'),
        use_individual_letters=text_config.get('use_individual_letters', False)
    )

# Usage with config file
if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_path = sys.argv[-1]
        if os.path.exists(config_path) and config_path.endswith('.json'):
            create_customizable_ring_from_config(config_path)
