import bpy
import math
import json
import os
from mathutils import Vector

def clear_scene():
    """Remove all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Clear mesh data
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)

def create_ring(inner_radius=0.9, outer_radius=1.0, height=0.2):
    """Create a ring using boolean operations"""
    # Create outer cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        radius=outer_radius,
        depth=height,
        location=(0, 0, 0)
    )
    outer_cyl = bpy.context.active_object
    outer_cyl.name = "OuterCylinder"
    
    # Create inner cylinder (hole)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=inner_radius,
        depth=height * 1.1,  # Slightly taller to ensure clean boolean
        location=(0, 0, 0)
    )
    inner_cyl = bpy.context.active_object
    inner_cyl.name = "InnerCylinder"
    
    # Add boolean modifier to outer cylinder
    boolean_mod = outer_cyl.modifiers.new("Boolean", 'BOOLEAN')
    boolean_mod.operation = 'DIFFERENCE'
    boolean_mod.object = inner_cyl
    
    # Apply the modifier
    bpy.context.view_layer.objects.active = outer_cyl
    bpy.ops.object.modifier_apply(modifier="Boolean")
    
    # Delete the inner cylinder
    bpy.data.objects.remove(inner_cyl)
    
    # Rename to Ring
    outer_cyl.name = "Ring"
    
    return outer_cyl

def create_text(text_string, font_size=0.1, extrude_depth=0.02):
    """Create 3D text object"""
    # Create text object
    bpy.ops.object.text_add(location=(0, 0, 0))
    text_obj = bpy.context.active_object
    
    # Set the text
    text_obj.data.body = text_string
    
    # Set text properties
    text_obj.data.size = font_size
    text_obj.data.extrude = extrude_depth
    text_obj.data.bevel_depth = 0.002
    text_obj.data.bevel_resolution = 2
    
    # Center the text
    text_obj.data.align_x = 'CENTER'
    text_obj.data.align_y = 'CENTER'
    
    # Convert text to mesh for easier manipulation
    bpy.ops.object.convert(target='MESH')
    
    return text_obj

def bend_text_to_ring(text_obj, ring_radius=1.0):
    """Bend the text to follow the ring curve"""
    # Make sure text object is active
    bpy.context.view_layer.objects.active = text_obj
    text_obj.select_set(True)
    
    # First, center the text at origin
    text_obj.location = (0, 0, 0)
    text_obj.rotation_euler = (0, 0, 0)
    
    # Apply all transforms to make sure we start clean
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    # Get text dimensions
    bbox = [text_obj.matrix_world @ Vector(corner) for corner in text_obj.bound_box]
    width = max([v.x for v in bbox]) - min([v.x for v in bbox])
    
    # Calculate the angle the text should span (in radians)
    # Use negative angle to bend in the correct direction (left to right)
    text_angle = -width / ring_radius  # Negative to fix direction
    
    # Add Simple Deform modifier to bend text
    deform_mod = text_obj.modifiers.new("BendText", 'SIMPLE_DEFORM')
    deform_mod.deform_method = 'BEND'
    deform_mod.angle = text_angle
    deform_mod.deform_axis = 'X'  # Bend around X axis to curve with the ring
    
    # Apply the modifier
    bpy.ops.object.modifier_apply(modifier="BendText")

def position_text_on_ring(text_obj, ring_obj, ring_radius):
    """Position the text properly on the ring"""
    # Orient text to lie flat on the ring surface
    # No rotation needed initially - text naturally lies flat in XY plane
    text_obj.rotation_euler = (0, 0, 0)
    
    # Move text to the outer surface of the ring
    # Position it on the front of the ring (along Y axis)
    text_obj.location = (0, ring_radius - 0.03, 0)  # Slightly embed into ring surface
    
    # Apply the transformation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

def boolean_text_from_ring(ring_obj, text_obj, operation='DIFFERENCE'):
    """Boolean operation to subtract or add text to ring"""
    # Add boolean modifier to ring
    boolean_mod = ring_obj.modifiers.new("TextBoolean", 'BOOLEAN')
    boolean_mod.operation = operation
    boolean_mod.object = text_obj
    
    # Apply the modifier
    bpy.context.view_layer.objects.active = ring_obj
    bpy.ops.object.modifier_apply(modifier="TextBoolean")
    
    # Hide the text object (don't delete it yet in case we need to adjust)
    text_obj.hide_set(True)

def export_stl(filepath):
    """Export the ring as STL file"""
    # Select only visible objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and not obj.hide_get():
            obj.select_set(True)
    
    # Export as STL using the new API
    bpy.ops.wm.stl_export(
        filepath=filepath,
        export_selected_objects=True,
        apply_modifiers=True
    )

def load_config(config_file):
    """Load configuration from JSON file"""
    with open(config_file, 'r') as f:
        return json.load(f)

def main():
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), "ring_config.json")
    
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        # Use default values
        config = {
            "ring": {
                "inner_radius": 0.9,
                "outer_radius": 1.0,
                "height": 0.2
            },
            "text": {
                "content": "LOVE",
                "font_size": 0.15,
                "extrude_depth": 0.03,
                "operation": "DIFFERENCE"
            },
            "output": {
                "stl_file": "ring_with_text.stl"
            }
        }
    else:
        config = load_config(config_path)
    
    # Clear the scene
    clear_scene()
    
    # Create ring
    ring_config = config["ring"]
    ring = create_ring(
        inner_radius=ring_config["inner_radius"],
        outer_radius=ring_config["outer_radius"],
        height=ring_config["height"]
    )
    
    # Create text
    text_config = config["text"]
    text = create_text(
        text_string=text_config["content"],
        font_size=text_config["font_size"],
        extrude_depth=text_config["extrude_depth"]
    )
    
    # Bend text to match ring curvature
    bend_text_to_ring(text, ring_radius=ring_config["outer_radius"])
    
    # Position text on ring
    position_text_on_ring(text, ring, ring_config["outer_radius"])
    
    # Boolean operation
    boolean_text_from_ring(ring, text, operation=text_config["operation"])
    
    # Export STL
    output_config = config["output"]
    stl_path = os.path.join(os.path.dirname(__file__), output_config["stl_file"])
    export_stl(stl_path)
    
    print(f"Ring with text exported to: {stl_path}")

if __name__ == "__main__":
    main()
