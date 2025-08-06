#!/usr/bin/env python3
"""
script.py - Blender script to create a 3D-printable ring with custom text
Runs in Blender with: blender --background --python script.py -- config.json
"""

import bpy
import bmesh
import sys
import json
import os
import math
from pathlib import Path
from datetime import datetime
from mathutils import Vector, Matrix
import traceback

class RingTextGenerator:
    def __init__(self, config_path):
        self.config_path = Path(config_path).resolve()
        self.config_dir = self.config_path.parent
        self.config = None
        self.log_messages = []
        self.log_file = None
        
    def log(self, message, level="INFO"):
        """Log message to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] [{level}] {message}"
        print(formatted_msg)
        self.log_messages.append(formatted_msg)
        
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(formatted_msg + '')
            except Exception as e:
                print(f"Warning: Could not write to log file: {e}")
    
    def setup_log_file(self):
        """Initialize log file from config"""
        if 'logFileName' in self.config:
            log_path = self.config['logFileName']
            if not os.path.isabs(log_path):
                log_path = self.config_dir / log_path
            self.log_file = Path(log_path)
            
            # Create log file and write header
            try:
                with open(self.log_file, 'w') as f:
                    f.write(f"Ring Text Generator Log - Started at {datetime.now()}")
                    f.write(f"Config file: {self.config_path}")
                    f.write("-" * 60 + "")
            except Exception as e:
                print(f"Warning: Could not create log file: {e}")
                self.log_file = None
    
    def load_config(self):
        """Load and parse configuration JSON"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            self.setup_log_file()
            self.log(f"Successfully loaded config from {self.config_path}")
            return True
        except FileNotFoundError:
            self.log(f"ERROR: Config file not found: {self.config_path}", "ERROR")
            return False
        except json.JSONDecodeError as e:
            self.log(f"ERROR: Invalid JSON in config file: {e}", "ERROR")
            return False
        except Exception as e:
            self.log(f"ERROR: Failed to load config: {e}", "ERROR")
            return False
    
    def validate_config(self):
        """Validate all configuration parameters"""
        required_fields = [
            'text', 'fontPath', 'textSize', 'isEmbossed', 'isCarved',
            'textDepth', 'letterSpacing', 'ringInnerDiameter', 
            'ringOuterDiameter', 'ringLength', 'outputFileName'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in self.config:
                self.log(f"ERROR: Missing required field: {field}", "ERROR")
                return False
        
        # Validate font path
        font_path = self.config['fontPath']
        if not os.path.isabs(font_path):
            font_path = self.config_dir / font_path
        font_path = Path(font_path).resolve()
        
        if not font_path.exists():
            self.log(f"ERROR: Font file not found: {font_path}", "ERROR")
            return False
        
        if not font_path.suffix.lower() in ['.ttf', '.otf']:
            self.log(f"ERROR: Font file must be TTF or OTF format: {font_path}", "ERROR")
            return False
        
        self.config['_resolved_font_path'] = str(font_path)
        
        # Validate ring dimensions
        inner_d = self.config['ringInnerDiameter']
        outer_d = self.config['ringOuterDiameter']
        length = self.config['ringLength']
        
        if inner_d <= 0 or outer_d <= 0 or length <= 0:
            self.log("ERROR: Ring dimensions must be positive", "ERROR")
            return False
        
        if inner_d >= outer_d:
            self.log(f"ERROR: Inner diameter ({inner_d}) must be less than outer diameter ({outer_d})", "ERROR")
            return False
        
        # Validate text size
        text_size = self.config['textSize']
        if text_size <= 0:
            self.log("ERROR: Text size must be positive", "ERROR")
            return False
        
        if text_size >= length:
            self.log(f"WARNING: Text size ({text_size}) >= ring length ({length}), capping to {length * 0.9}", "WARNING")
            self.config['textSize'] = length * 0.9
        
        # Validate embossed/carved settings
        is_embossed = self.config['isEmbossed']
        is_carved = self.config['isCarved']
        
        if is_embossed and is_carved:
            self.log("ERROR: Cannot have both embossed and carved set to true", "ERROR")
            return False
        
        if not is_embossed and not is_carved:
            self.log("WARNING: Neither embossed nor carved is true, defaulting to embossed", "WARNING")
            self.config['isEmbossed'] = True
            self.config['isCarved'] = False
        
        # Validate text depth
        text_depth = self.config['textDepth']
        ring_thickness = (outer_d - inner_d) / 2
        
        if text_depth <= 0:
            self.log("ERROR: Text depth must be positive", "ERROR")
            return False
        
        if self.config['isCarved'] and text_depth > ring_thickness:
            self.log(f"WARNING: Text depth ({text_depth}) > ring thickness ({ring_thickness}), capping to {ring_thickness * 0.9}", "WARNING")
            self.config['textDepth'] = ring_thickness * 0.9
        
        # Validate letter spacing
        letter_spacing = self.config['letterSpacing']
        ring_circumference = math.pi * outer_d
        
        if letter_spacing < 0:
            self.log(f"WARNING: Letter spacing ({letter_spacing}) < 0, setting to 0", "WARNING")
            self.config['letterSpacing'] = 0
        
        if letter_spacing > ring_circumference:
            self.log(f"ERROR: Letter spacing ({letter_spacing}) > ring circumference ({ring_circumference})", "ERROR")
            return False
        
        # Validate text content
        text = self.config['text']
        if not text or len(text.strip()) == 0:
            self.log("ERROR: Text cannot be empty", "ERROR")
            return False
        
        # Remove newlines as specified
        self.config['text'] = text.replace('', '').replace('\r', '')
        
        # Resolve output file path
        output_path = self.config['outputFileName']
        if not os.path.isabs(output_path):
            output_path = self.config_dir / output_path
        self.config['_resolved_output_path'] = str(Path(output_path).resolve())
        
        self.log("Configuration validation successful")
        return True
    
    def clear_scene(self):
        """Clear all objects from the scene"""
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        # Clear mesh data
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
        
        # Clear curves
        for curve in bpy.data.curves:
            bpy.data.curves.remove(curve)
        
        # Clear fonts
        for font in bpy.data.fonts:
            bpy.data.fonts.remove(font)
            
        self.log("Scene cleared")
    
    def create_ring(self):
        """Create the ring cylinder mesh"""
        inner_radius = self.config['ringInnerDiameter'] / 2
        outer_radius = self.config['ringOuterDiameter'] / 2
        length = self.config['ringLength']
        
        # Create cylinder with 256 segments as specified
        vertices = 256
        
        # Create mesh
        mesh = bpy.data.meshes.new(name="Ring")
        ring_obj = bpy.data.objects.new("Ring", mesh)
        bpy.context.collection.objects.link(ring_obj)
        
        # Create geometry using bmesh for better control
        bm = bmesh.new()
        
        # Create vertices for inner and outer circles at top and bottom
        for z in [-length/2, length/2]:
            # Outer circle
            for i in range(vertices):
                angle = 2 * math.pi * i / vertices
                x = outer_radius * math.cos(angle)
                y = outer_radius * math.sin(angle)
                bm.verts.new((x, y, z))
            
            # Inner circle
            for i in range(vertices):
                angle = 2 * math.pi * i / vertices
                x = inner_radius * math.cos(angle)
                y = inner_radius * math.sin(angle)
                bm.verts.new((x, y, z))
        
        bm.verts.ensure_lookup_table()
        
        # Create faces
        # Outer surface
        for i in range(vertices):
            next_i = (i + 1) % vertices
            v1 = bm.verts[i]  # bottom outer
            v2 = bm.verts[next_i]  # bottom outer next
            v3 = bm.verts[vertices * 2 + next_i]  # top outer next
            v4 = bm.verts[vertices * 2 + i]  # top outer
            bm.faces.new([v1, v2, v3, v4])
        
        # Inner surface
        for i in range(vertices):
            next_i = (i + 1) % vertices
            v1 = bm.verts[vertices + i]  # bottom inner
            v2 = bm.verts[vertices * 3 + i]  # top inner
            v3 = bm.verts[vertices * 3 + next_i]  # top inner next
            v4 = bm.verts[vertices + next_i]  # bottom inner next
            bm.faces.new([v1, v2, v3, v4])
        
        # Top face
        for i in range(vertices):
            next_i = (i + 1) % vertices
            v1 = bm.verts[vertices * 2 + i]  # top outer
            v2 = bm.verts[vertices * 2 + next_i]  # top outer next
            v3 = bm.verts[vertices * 3 + next_i]  # top inner next
            v4 = bm.verts[vertices * 3 + i]  # top inner
            bm.faces.new([v1, v2, v3, v4])
        
        # Bottom face
        for i in range(vertices):
            next_i = (i + 1) % vertices
            v1 = bm.verts[i]  # bottom outer
            v2 = bm.verts[vertices + i]  # bottom inner
            v3 = bm.verts[vertices + next_i]  # bottom inner next
            v4 = bm.verts[next_i]  # bottom outer next
            bm.faces.new([v1, v2, v3, v4])
        
        # Update mesh
        bm.to_mesh(mesh)
        bm.free()
        
        # Apply smooth shading
        ring_obj.select_set(True)
        bpy.context.view_layer.objects.active = ring_obj
        bpy.ops.object.shade_smooth()
        
        self.log(f"Created ring: inner_d={self.config['ringInnerDiameter']}mm, "
                f"outer_d={self.config['ringOuterDiameter']}mm, length={self.config['ringLength']}mm")
        
        return ring_obj
    
    def create_text(self):
        """Create 3D text on the ring using proper curve modifier"""
        text = self.config['text']
        font_path = self.config['_resolved_font_path']
        text_size = self.config['textSize']
        is_embossed = self.config['isEmbossed']
        text_depth = self.config['textDepth']
        letter_spacing = self.config['letterSpacing']
        outer_radius = self.config['ringOuterDiameter'] / 2
        
        # Load font
        try:
            font = bpy.data.fonts.load(font_path)
            self.log(f"Loaded font: {font_path}")
        except Exception as e:
            self.log(f"ERROR: Failed to load font: {e}", "ERROR")
            font = None
            self.log("Using default Blender font as fallback", "WARNING")
        
        # Create text curve object
        curve = bpy.data.curves.new(type="FONT", name="Text")
        curve.body = text
        
        if font:
            curve.font = font
        
        # Set text properties
        curve.size = text_size
        curve.extrude = text_depth
        curve.bevel_depth = 0
        curve.align_x = 'CENTER'
        curve.align_y = 'CENTER'  # Center vertically
        
        # Add letter spacing
        if letter_spacing > 0:
            # Convert letter_spacing from arc length to relative spacing
            curve.space_character = 1.0 + (letter_spacing / text_size)
        
        # Create text object
        text_obj = bpy.data.objects.new("Text", curve)
        bpy.context.collection.objects.link(text_obj)
        
        # Position text initially
        text_obj.location = (0, 0, 0)
        
        # Rotate text to lie flat (rotate -90 degrees around X axis)
        # This makes the text face outward when wrapped around the ring
        text_obj.rotation_euler = (-math.pi/2, 0, 0)
        
        # Convert to mesh first (before any transforms)
        text_obj.select_set(True)
        bpy.context.view_layer.objects.active = text_obj
        
        # Convert to mesh
        bpy.ops.object.convert(target='MESH')
        
        # Apply transforms including the rotation
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Now curve the text around the ring
        text_obj = self.curve_text_mesh(text_obj, outer_radius, is_embossed)
        
        if text_obj:
            self.log(f"Created {'embossed' if is_embossed else 'carved'} text: '{text}'")
            return text_obj
        
        return None
    
    def curve_text_mesh(self, text_obj, radius, is_embossed):
        """Curve the text mesh around the ring"""
        mesh = text_obj.data
        
        # Get text bounds to determine width and height
        text_obj.select_set(True)
        bpy.context.view_layer.objects.active = text_obj
        
        # Get bounding box
        bbox_corners = [text_obj.matrix_world @ Vector(corner) for corner in text_obj.bound_box]
        min_x = min([v.x for v in bbox_corners])
        max_x = max([v.x for v in bbox_corners])
        min_y = min([v.y for v in bbox_corners])
        max_y = max([v.y for v in bbox_corners])
        min_z = min([v.z for v in bbox_corners])
        max_z = max([v.z for v in bbox_corners])
        
        text_width = max_x - min_x
        text_depth_actual = max_y - min_y  # The extrusion depth (now in Y due to rotation)
        text_height = max_z - min_z  # Height along ring axis
        text_center_x = (min_x + max_x) / 2
        text_center_y = (min_y + max_y) / 2
        text_center_z = (min_z + max_z) / 2
        
        # Check if text fits around circumference
        circumference = 2 * math.pi * radius
        if text_width > circumference:
            self.log(f"WARNING: Text width ({text_width}mm) exceeds circumference ({circumference}mm), will wrap", "WARNING")
        
        # Calculate the angular span of the text
        text_angle = text_width / radius
        
        # Apply curve deformation to vertices
        for vertex in mesh.vertices:
            # Get vertex position (after rotation, Y is now the depth)
            x = vertex.co.x - text_center_x  # Center the text horizontally
            y = vertex.co.y - text_center_y  # This is now the depth from rotation
            z = vertex.co.z  # Keep Z as-is for vertical position on ring
            
            # Calculate angle for this vertex based on its X position
            # Positive angle to read left-to-right correctly
            angle = (x / radius)
            
            # Calculate radial position
            if is_embossed:
                # For embossed, text extends outward from surface
                # The base of the text should be at the ring surface
                r = radius - y  # Subtract y because of the rotation
            else:
                # For carved, text goes inward from surface
                # The top of the text should be at the ring surface
                r = radius - y
            
            # Convert to cylindrical coordinates
            # Place on +Y side (front) of the ring
            new_x = r * math.sin(angle)
            new_y = r * math.cos(angle)
            new_z = z  # Keep vertical position
            
            vertex.co = Vector((new_x, new_y, new_z))
        
        # Update mesh
        mesh.update()
        
        # Ensure proper normals
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        return text_obj
    
    def combine_ring_and_text(self, ring_obj, text_obj):
        """Combine ring and text into final mesh"""
        if self.config['isCarved']:
            # For carved text, use boolean difference
            self.log("Applying boolean difference for carved text")
            
            # Select ring
            bpy.ops.object.select_all(action='DESELECT')
            ring_obj.select_set(True)
            bpy.context.view_layer.objects.active = ring_obj
            
            # Add boolean modifier to ring
            modifier = ring_obj.modifiers.new(name="Carve", type='BOOLEAN')
            modifier.operation = 'DIFFERENCE'
            modifier.object = text_obj
            modifier.solver = 'EXACT'  # Use exact solver for better results
            
            # Apply modifier
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                
                # Delete text object as it's now carved into ring
                bpy.data.objects.remove(text_obj, do_unlink=True)
                
                return ring_obj
            except Exception as e:
                self.log(f"WARNING: Boolean operation failed, trying alternative method: {e}", "WARNING")
                
                # If boolean fails, try with FAST solver
                modifier = ring_obj.modifiers.new(name="CarveFast", type='BOOLEAN')
                modifier.operation = 'DIFFERENCE'
                modifier.object = text_obj
                modifier.solver = 'FAST'
                
                try:
                    bpy.ops.object.modifier_apply(modifier=modifier.name)
                    bpy.data.objects.remove(text_obj, do_unlink=True)
                    return ring_obj
                except Exception as e2:
                    self.log(f"ERROR: Boolean operation failed completely: {e2}", "ERROR")
                    # As last resort, just return the ring without carving
                    return ring_obj
        else:
            # For embossed text, join meshes
            self.log("Joining meshes for embossed text")
            
            # Select both objects
            bpy.ops.object.select_all(action='DESELECT')
            ring_obj.select_set(True)
            text_obj.select_set(True)
            bpy.context.view_layer.objects.active = ring_obj
            
            # Join
            bpy.ops.object.join()
            
            return ring_obj
    
    def export_stl(self, obj):
        """Export the final mesh as STL"""
        output_path = self.config['_resolved_output_path']
        
        try:
            # Select only the final object
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # Ensure we have a mesh
            if obj.type != 'MESH':
                self.log("WARNING: Object is not a mesh, converting", "WARNING")
                bpy.ops.object.convert(target='MESH')
            
            # Export using the new API for Blender 4.0+
            if hasattr(bpy.ops.wm, 'stl_export'):
                bpy.ops.wm.stl_export(
                    filepath=output_path,
                    export_selected_objects=True,
                    ascii_format=False,  # Binary format
                    apply_modifiers=True,
                    global_scale=1.0  # Millimeter units
                )
            else:
                # Fallback for older Blender versions
                bpy.ops.export_mesh.stl(
                    filepath=output_path,
                    check_existing=False,
                    use_selection=True,
                    ascii=False,  # Binary format
                    apply_modifiers=True,
                    global_scale=1.0
                )
            
            self.log(f"Successfully exported STL to: {output_path}")
            return True
            
        except Exception as e:
            self.log(f"ERROR: Failed to export STL: {e}", "ERROR")
            return False
    
    def run(self):
        """Main execution method"""
        try:
            # Load configuration
            if not self.load_config():
                return 2  # File I/O error
            
            # Validate configuration
            if not self.validate_config():
                return 1  # Input validation error
            
            # Clear scene
            self.clear_scene()
            
            # Create ring
            ring_obj = self.create_ring()
            if not ring_obj:
                self.log("ERROR: Failed to create ring", "ERROR")
                return 3  # Blender operation error
            
            # Create text
            text_obj = self.create_text()
            if not text_obj:
                self.log("ERROR: Failed to create text", "ERROR")
                return 3  # Blender operation error
            
            # Combine ring and text
            final_obj = self.combine_ring_and_text(ring_obj, text_obj)
            if not final_obj:
                self.log("ERROR: Failed to combine ring and text", "ERROR")
                return 3  # Blender operation error
            
            # Export STL
            if not self.export_stl(final_obj):
                return 2  # File I/O error
            
            self.log("Ring generation completed successfully")
            return 0  # Success
            
        except Exception as e:
            self.log(f"ERROR: Unexpected error: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return 3  # Blender operation error


def main():
    """Main entry point"""
    # Get command line arguments
    argv = sys.argv
    
    # Find the -- separator
    if "--" not in argv:
        print("ERROR: No config file specified. Usage: blender --background --python script.py -- config.json")
        sys.exit(1)
    
    argv = argv[argv.index("--") + 1:]
    
    if len(argv) < 1:
        print("ERROR: No config file specified. Usage: blender --background --python script.py -- config.json")
        sys.exit(1)
    
    config_path = argv[0]
    
    # Create and run generator
    generator = RingTextGenerator(config_path)
    exit_code = generator.run()
    
    # Exit with appropriate code
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
