import bpy
import json
import sys
import os

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

def create_curved_text(text="CUSTOM TEXT", radius=2.25, font_size=0.3, extrude_depth=0.1, font_path=None):
    """Create 3D text that curves around the ring"""
    
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

def add_materials(ring, text):
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
    text.data.materials.append(text_mat)

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
    output_path="ring_with_text.stl"
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
    output_path : str
        Path for the exported file
    """
    
    # Clear the scene
    clear_scene()
    
    # Create the ring
    ring = create_ring(inner_radius, outer_radius, ring_height)
    
    # Create curved text
    text_obj, text_path = create_curved_text(
        text=text,
        radius=(inner_radius + outer_radius) / 2,
        font_size=font_size,
        extrude_depth=text_extrude,
        font_path=font_path
    )
    
    # Add materials
    add_materials(ring, text_obj)
    
    # Export the result
    export_result(output_path)
    
    return ring, text_obj

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
        output_path=export_config.get('output_path', 'ring.stl')
    )

# Usage with config file
if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_path = sys.argv[-1]
        if os.path.exists(config_path) and config_path.endswith('.json'):
            create_customizable_ring_from_config(config_path)
