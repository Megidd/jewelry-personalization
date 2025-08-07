import bpy
import sys
import json

def main():
    # --- parse arguments after “--” ---
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    if len(argv) < 1:
        print("Usage: blender --background --python generate_name_ring.py -- config.json")
        return

    # --- load JSON params ---
    config_path = argv[0]
    with open(config_path, 'r') as f:
        params = json.load(f)

    text_str       = params.get("text", "Name")
    font_path      = params.get("font_path", "")
    ring_diameter  = params.get("ring_diameter", 18)
    band_thickness = params.get("band_thickness", 2)
    extrude_depth  = params.get("extrude_depth", 2)
    output_stl     = params.get("output_stl", "ring.stl")

    # --- clear default scene ---
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # --- create and configure text object ---
    bpy.ops.object.text_add()
    txt_obj = bpy.context.object
    txt_obj.data.body = text_str

    if font_path:
        try:
            font = bpy.data.fonts.load(font_path)
            txt_obj.data.font = font
        except Exception as e:
            print(f"Warning: could not load font '{font_path}': {e}")

    txt_obj.data.extrude = extrude_depth

    # convert text→mesh
    bpy.ops.object.convert(target='MESH')

    # --- create circular path & curve-wrap the text mesh ---
    bpy.ops.curve.primitive_bezier_circle_add(radius=ring_diameter / 2)
    circle = bpy.context.object
    circle.name = "RingPath"

    bpy.context.view_layer.objects.active = txt_obj
    bpy.ops.object.modifier_add(type='CURVE')
    txt_obj.modifiers["Curve"].object = circle

    # offset so letters sit around the top of the circle
    txt_obj.location.x = ring_diameter / 2

    # --- give the band real thickness ---
    bpy.ops.object.modifier_add(type='SOLIDIFY')
    txt_obj.modifiers["Solidify"].thickness = band_thickness

    # --- export as STL (with modifiers applied) ---
    bpy.ops.object.select_all(action='DESELECT')
    txt_obj.select_set(True)
    bpy.context.view_layer.objects.active = txt_obj
            
    # Ensure we have a mesh
    if txt_obj.type != 'MESH':
        bpy.ops.object.convert(target='MESH')
            
    # Try new export API (Blender 3.3+)        
    bpy.ops.wm.stl_export(
        filepath=output_stl,
        export_selected_objects=True,
        ascii_format=False,
        apply_modifiers=True,
        global_scale=1.0
    )

    print(f"✅ Ring (‘{text_str}’) exported to: {output_stl}")


if __name__ == "__main__":
    main()
