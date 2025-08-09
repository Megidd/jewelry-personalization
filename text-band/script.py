import bpy
import bmesh
import json
import sys
import math
import os
from mathutils import Vector

def clear_scene():
    """Clear existing mesh objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Clear materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)

def create_ring_material(color, metallic=1.0, roughness=0.1):
    """Create a metallic material for the ring"""
    mat = bpy.data.materials.new(name="RingMaterial")
    mat.use_nodes = True
    
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["IOR"].default_value = 2.5
    
    return mat

def create_cursive_text(text, font_size=1.0, font_path=None):
    """Create cursive text object"""
    # Create text object
    font_curve = bpy.data.curves.new(type="FONT", name="CursiveText")
    font_obj = bpy.data.objects.new(name="CursiveText", object_data=font_curve)
    bpy.context.scene.collection.objects.link(font_obj)
    
    # Load custom font if provided
    if font_path and os.path.exists(font_path):
        try:
            font = bpy.data.fonts.load(font_path)
            font_curve.font = font
            print(f"Successfully loaded font: {font_path}")
        except Exception as e:
            print(f"Error loading font {font_path}: {e}")
            print("Using default font instead.")
    else:
        if font_path:
            print(f"Font file not found: {font_path}")
        print("Using default font. For best results, provide a cursive font file path.")
    
    # Set text properties
    font_curve.body = text
    font_curve.size = font_size
    font_curve.space_character = 1.0
    font_curve.space_word = 1.0
    
    # Add some extrusion for 3D effect
    font_curve.extrude = 0.02  # Reduced extrusion
    font_curve.bevel_depth = 0.01  # Reduced bevel
    font_curve.bevel_resolution = 2
    
    # Set text alignment to center
    font_curve.align_x = 'CENTER'
    font_curve.align_y = 'CENTER'
    
    # Remove shear for now - we'll handle style after positioning
    font_curve.shear = 0
    
    # Make sure the object is selected and active
    bpy.context.view_layer.objects.active = font_obj
    font_obj.select_set(True)
    
    # Convert to mesh
    bpy.ops.object.convert(target='MESH')
    
    # Scale the text to appropriate size
    text_scale = 0.15  # Adjust this value to change text size on ring
    font_obj.scale = (text_scale, text_scale, text_scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    return font_obj

def create_ring_band(radius=1.0, thickness=0.15, height=0.3):
    """Create the ring band mesh"""
    # Create a circle
    verts = []
    edges = []
    faces = []
    
    segments = 64
    
    # Create vertices for inner and outer circles at top and bottom
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        
        # Inner radius
        x_inner = (radius - thickness) * math.cos(angle)
        y_inner = (radius - thickness) * math.sin(angle)
        
        # Outer radius
        x_outer = radius * math.cos(angle)
        y_outer = radius * math.sin(angle)
        
        # Bottom vertices
        verts.append((x_inner, y_inner, -height/2))
        verts.append((x_outer, y_outer, -height/2))
        
        # Top vertices
        verts.append((x_inner, y_inner, height/2))
        verts.append((x_outer, y_outer, height/2))
    
    # Create faces with correct winding order
    for i in range(segments):
        next_i = (i + 1) % segments
        
        # Current indices
        bottom_inner = i * 4
        bottom_outer = i * 4 + 1
        top_inner = i * 4 + 2
        top_outer = i * 4 + 3
        
        # Next indices
        next_bottom_inner = next_i * 4
        next_bottom_outer = next_i * 4 + 1
        next_top_inner = next_i * 4 + 2
        next_top_outer = next_i * 4 + 3
        
        # Inner face (reversed winding)
        faces.append([top_inner, next_top_inner, next_bottom_inner, bottom_inner])
        
        # Outer face (correct winding)
        faces.append([bottom_outer, next_bottom_outer, next_top_outer, top_outer])
        
        # Bottom face (reversed winding)
        faces.append([next_bottom_inner, next_bottom_outer, bottom_outer, bottom_inner])
        
        # Top face (correct winding)
        faces.append([top_inner, top_outer, next_top_outer, next_top_inner])
    
    # Create mesh
    mesh = bpy.data.meshes.new(name="RingBand")
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    
    # Create object
    ring_obj = bpy.data.objects.new(name="RingBand", object_data=mesh)
    bpy.context.scene.collection.objects.link(ring_obj)
    
    # Fix normals
    bpy.context.view_layer.objects.active = ring_obj
    ring_obj.select_set(True)
    
    # Enter edit mode and recalculate normals
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    return ring_obj

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
    # This ensures text wraps appropriately around the ring
    text_angle = width / ring_radius
    
    # Add Simple Deform modifier to bend text
    deform_mod = text_obj.modifiers.new("BendText", 'SIMPLE_DEFORM')
    deform_mod.deform_method = 'BEND'
    deform_mod.angle = text_angle
    deform_mod.deform_axis = 'Z'  # Changed to Z axis for proper tangential bending
    
    # Apply the modifier
    bpy.ops.object.modifier_apply(modifier="BendText")

def position_text_on_ring(text_obj, ring_obj, ring_radius):
    """Position the text properly on the ring"""
    # The text needs to be oriented so it follows the ring's circumference
    # not pointing radially outward
    
    # First, rotate the text so it's standing up and facing the right direction
    # This makes the text follow the ring's curve (tangentially)
    text_obj.rotation_euler = (math.pi/2, 0, 0)  # Stand the text up
    
    # Move text to the outer surface of the ring
    # Position it on the front of the ring (along Y axis)
    text_obj.location = (0, ring_radius - 0.03, 0)  # Slightly embed into ring surface
    
    # Apply the transformation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    
    # Now we can rotate around Z to position text around the ring if needed
    # text_obj.rotation_euler.z = math.pi  # Uncomment to position on back of ring


def merge_text_with_ring(text_obj, ring_obj, ring_radius):
    """Merge the text with the ring using boolean union"""
    # Make sure we have a mesh object
    if text_obj.type != 'MESH':
        print("Warning: Text object is not a mesh!")
        return
    
    # Bend the text to match ring curvature
    bend_text_to_ring(text_obj, ring_radius)
    
    # Position text on ring surface
    position_text_on_ring(text_obj, ring_obj, ring_radius)
    
    # Select ring object
    bpy.context.view_layer.objects.active = ring_obj
    ring_obj.select_set(True)
    text_obj.select_set(False)
    
    # Add Boolean modifier to ring
    bool_mod = ring_obj.modifiers.new("TextUnion", 'BOOLEAN')
    bool_mod.operation = 'UNION'
    bool_mod.object = text_obj
    bool_mod.solver = 'FAST'
    
    # Apply boolean
    try:
        bpy.ops.object.modifier_apply(modifier="TextUnion")
        
        # Delete the text object after successful boolean
        bpy.data.objects.remove(text_obj, do_unlink=True)
    except:
        print("Boolean operation failed, trying alternative method...")
        # If boolean fails, just join the meshes
        bpy.ops.object.select_all(action='DESELECT')
        ring_obj.select_set(True)
        text_obj.select_set(True)
        bpy.context.view_layer.objects.active = ring_obj
        bpy.ops.object.join()
    
    # Clean up the mesh
    bpy.context.view_layer.objects.active = ring_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.object.mode_set(mode='OBJECT')

def export_stl(obj, filepath):
    """Export the object as STL file"""
    # Select only the ring object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    # Export as STL using the new API for Blender 4.x
    bpy.ops.wm.stl_export(
        filepath=filepath,
        export_selected_objects=True,
        global_scale=10.0,  # Scale up for better printing (10mm radius becomes 10cm)
        use_scene_unit=True,
        ascii_format=False,  # Binary STL is more compact
        apply_modifiers=True
    )
    
    print(f"STL file exported to: {filepath}")

def main():
    # Get config file from command line arguments
    argv = sys.argv
    argv = argv[argv.index("--") + 1:]
    
    if len(argv) == 0:
        print("No config file specified!")
        return
    
    # Load configuration
    with open(argv[0], 'r') as f:
        config = json.load(f)
    
    # Clear scene
    clear_scene()
    
    # Extract configuration
    text = config.get("text", "Emma")
    ring_radius = config.get("ring_radius", 1.0)
    ring_thickness = config.get("ring_thickness", 0.15)
    ring_height = config.get("ring_height", 0.4)
    material_color = config.get("material_color", [0.8, 0.8, 0.8])
    metallic = config.get("metallic", 1.0)
    roughness = config.get("roughness", 0.1)
    font_size = config.get("font_size", 1.2)
    font_path = config.get("font_path", None)
    stl_path = config.get("stl_path", "ring_model.stl")
    
    # Create ring band
    ring_obj = create_ring_band(
        radius=ring_radius,
        thickness=ring_thickness,
        height=ring_height
    )
    
    # Create text (already converted to mesh) with custom font
    text_obj = create_cursive_text(text, font_size=font_size, font_path=font_path)
    
    # Merge text with ring
    merge_text_with_ring(text_obj, ring_obj, ring_radius)
    
    # Apply material
    material = create_ring_material(material_color, metallic, roughness)
    ring_obj.data.materials.append(material)
    
    # Export STL file
    export_stl(ring_obj, stl_path)
    
    print(f"3D model exported to: {stl_path}")

if __name__ == "__main__":
    main()
