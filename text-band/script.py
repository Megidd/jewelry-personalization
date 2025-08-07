#!/usr/bin/env python3
"""
script.py - Blender script to create a 3D-printable name ring with flowing script
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
        if 'log_filename' in self.config:
            log_path = self.config['log_filename']
            if not os.path.isabs(log_path):
                log_path = self.config_dir / log_path
            self.log_file = Path(log_path)
            
            if self.config.get('create_parent_dirs', True) and self.log_file.parent:
                try:
                    self.log_file.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"Warning: Could not create log directory: {e}")
                    self.log_file = None
                    return
            
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
            with open(self.config_path, 'r', encoding='utf-8') as f:
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
            'text', 'font_path', 'inner_diameter', 'stl_filename'
        ]
        
        for field in required_fields:
            if field not in self.config:
                self.log(f"ERROR: Missing required field: {field}", "ERROR")
                return False
        
        # Set defaults for script-style name ring
        self.config.setdefault('ring_height', 5.0)  # Height of the text/ring band
        self.config.setdefault('ring_thickness', 2.0)  # Thickness of the band
        self.config.setdefault('text_style', 'flowing')  # New parameter for flowing script
        self.config.setdefault('radial_segments', 256)
        self.config.setdefault('vertical_segments', 64)
        self.config.setdefault('create_parent_dirs', True)
        self.config.setdefault('smooth_connections', True)  # Smooth letter connections
        self.config.setdefault('add_base_band', False)  # Optional solid band beneath text
        self.config.setdefault('base_band_height', 1.0)  # Height of base band if enabled
        
        # Validate font path
        font_path = self.config['font_path']
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
        
        # Validate text
        text = self.config['text']
        if not text or len(text.strip()) == 0:
            self.log("ERROR: Text cannot be empty", "ERROR")
            return False
        
        self.config['text'] = text.replace('', '').replace('\r', '')
        
        # Validate ring dimensions
        inner_d = self.config['inner_diameter']
        
        if inner_d <= 0:
            self.log("ERROR: Ring dimensions must be positive", "ERROR")
            return False
        
        if inner_d < 10:
            self.log(f"WARNING: Inner diameter ({inner_d}mm) is less than recommended minimum of 10mm", "WARNING")
        
        # Resolve output file path
        output_path = self.config['stl_filename']
        if not os.path.isabs(output_path):
            output_path = self.config_dir / output_path
        self.config['_resolved_output_path'] = str(Path(output_path).resolve())
        
        output_dir = Path(self.config['_resolved_output_path']).parent
        if self.config.get('create_parent_dirs', True) and output_dir:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.log(f"ERROR: Could not create output directory: {e}", "ERROR")
                return False
        
        self.log("Configuration validation successful")
        return True
    
    def clear_scene(self):
        """Clear all objects from the scene"""
        self.log("Clearing scene...")
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
        
        for curve in bpy.data.curves:
            bpy.data.curves.remove(curve)
        
        for font in bpy.data.fonts:
            bpy.data.fonts.remove(font)
            
        self.log("Scene cleared")
    
    def create_flowing_name_ring(self):
        """Create a ring where the text forms the actual band of the ring"""
        text = self.config['text']
        font_path = self.config['_resolved_font_path']
        inner_radius = self.config['inner_diameter'] / 2
        ring_height = self.config['ring_height']
        ring_thickness = self.config['ring_thickness']
        
        self.log("Creating flowing script name ring...")
        
        # Load font
        try:
            font = bpy.data.fonts.load(font_path)
            self.log(f"Loaded font: {font_path}")
        except Exception as e:
            self.log(f"ERROR: Failed to load font: {e}", "ERROR")
            return None
        
        # Create text curve object
        curve = bpy.data.curves.new(type="FONT", name="NameText")
        curve.body = text
        curve.font = font
        
        # Set text properties for flowing script style
        curve.size = ring_height
        curve.align_x = 'CENTER'
        curve.align_y = 'CENTER'
        
        # Create initial text object
        text_obj = bpy.data.objects.new("NameText", curve)
        bpy.context.collection.objects.link(text_obj)
        
        # Convert to mesh
        text_obj.select_set(True)
        bpy.context.view_layer.objects.active = text_obj
        
        self.log("Converting text to mesh...")
        bpy.ops.object.convert(target='MESH')
        
        # Center the text
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
        
        # Get text width for proper scaling
        bbox = [text_obj.matrix_world @ Vector(corner) for corner in text_obj.bound_box]
        text_width = max([v.x for v in bbox]) - min([v.x for v in bbox])
        
        # Calculate the circumference and required scale
        circumference = 2 * math.pi * inner_radius
        
        # We want the text to wrap around with some overlap for seamless connection
        # Add slight overlap (10% of text width) for better connection
        overlap_factor = 1.1
        scale_factor = circumference / (text_width * overlap_factor)
        
        # Apply scaling to make text fit circumference
        text_obj.scale = (scale_factor, 1, 1)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Create the ring by bending the text into a circle
        self.log("Bending text into ring shape...")
        ring_obj = self.bend_text_into_ring(text_obj, inner_radius, ring_thickness)
        
        if ring_obj:
            # Add optional base band for stability
            if self.config.get('add_base_band', False):
                base_band = self.create_base_band(inner_radius, ring_thickness)
                if base_band:
                    self.log("Adding base band for stability...")
                    ring_obj = self.combine_with_base_band(ring_obj, base_band)
            
            self.log(f"Created flowing name ring with text: '{text}'")
            return ring_obj
        else:
            return None
    
    def bend_text_into_ring(self, text_obj, radius, thickness):
        """Bend the linear text mesh into a ring shape"""
        mesh = text_obj.data
        
        # Get bounds
        bbox_corners = [text_obj.matrix_world @ Vector(corner) for corner in text_obj.bound_box]
        min_x = min([v.x for v in bbox_corners])
        max_x = max([v.x for v in bbox_corners])
        min_y = min([v.y for v in bbox_corners])
        max_y = max([v.y for v in bbox_corners])
        min_z = min([v.z for v in bbox_corners])
        max_z = max([v.z for v in bbox_corners])
        
        text_width = max_x - min_x
        text_height = max_z - min_z
        text_depth = max_y - min_y
        
        # Center values
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        # First, extrude the text to give it thickness
        self.log("Adding thickness to text...")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Solidify for thickness
        bpy.ops.object.mode_set(mode='OBJECT')
        solidify_modifier = text_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
        solidify_modifier.thickness = thickness
        solidify_modifier.offset = 0  # Center the thickness
        solidify_modifier.use_even_offset = True
        solidify_modifier.use_quality_normals = True
        
        # Apply solidify modifier
        bpy.ops.object.modifier_apply(modifier=solidify_modifier.name)
        
        # Now bend into ring shape
        self.log("Bending into ring shape...")
        
        # Apply the cylindrical transformation
        for vertex in mesh.vertices:
            # Get original position relative to center
            x = vertex.co.x - center_x
            y = vertex.co.y - center_y
            z = vertex.co.z - center_z
            
            # Map X position to angle around the ring
            # Full text width maps to full circle (2π)
            angle = (x / text_width) * 2 * math.pi
            
            # The radius for this vertex depends on its Y position (depth)
            # This creates the thickness of the ring
            vertex_radius = radius + y
            
            # Convert to cylindrical coordinates
            new_x = vertex_radius * math.sin(angle)
            new_y = vertex_radius * math.cos(angle)
            new_z = z  # Keep vertical position
            
            vertex.co = Vector((new_x, new_y, new_z))
        
        # Update mesh
        mesh.update()
        
        # Clean up the seam where the text meets
        self.log("Cleaning up seam...")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Remove doubles to merge vertices at the seam
        bpy.ops.mesh.remove_doubles(threshold=0.1)
        
        # Smooth the mesh for better appearance
        bpy.ops.mesh.vertices_smooth(factor=0.5, repeat=2)
        
        # Recalculate normals
        bpy.ops.mesh.normals_make_consistent(inside=False)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply smooth shading
        bpy.ops.object.shade_smooth()
        
        # Add subdivision surface for smoother result
        if self.config.get('smooth_connections', True):
            subsurf_modifier = text_obj.modifiers.new(name="Subdivision", type='SUBSURF')
            subsurf_modifier.levels = 1
            subsurf_modifier.render_levels = 2
            bpy.ops.object.modifier_apply(modifier=subsurf_modifier.name)
        
        return text_obj
    
    def create_base_band(self, radius, thickness):
        """Create an optional solid band beneath the text"""
        band_height = self.config.get('base_band_height', 1.0)
        
        self.log("Creating base band...")
        
        # Create a simple torus for the base band
        bpy.ops.mesh.primitive_torus_add(
            major_radius=radius,
            minor_radius=thickness/2,
            major_segments=128,
            minor_segments=32,
            location=(0, 0, -band_height/2)
        )
        
        base_band = bpy.context.active_object
        base_band.name = "BaseBand"
        
        # Scale it to be more like a band
        base_band.scale[2] = band_height / thickness
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        return base_band
    
    def combine_with_base_band(self, ring_obj, base_band):
        """Combine the text ring with the base band"""
        self.log("Combining text with base band...")
        
        # Select ring
        bpy.ops.object.select_all(action='DESELECT')
        ring_obj.select_set(True)
        bpy.context.view_layer.objects.active = ring_obj
        
        # Add boolean modifier
        modifier = ring_obj.modifiers.new(name="BaseBandUnion", type='BOOLEAN')
        modifier.operation = 'UNION'
        modifier.object = base_band
        modifier.solver = 'EXACT'
        
        try:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            bpy.data.objects.remove(base_band, do_unlink=True)
            
            # Clean up
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            return ring_obj
        except Exception as e:
            self.log(f"WARNING: Could not combine with base band: {e}", "WARNING")
            return ring_obj
    
    def export_stl(self, obj):
        """Export the final mesh as STL"""
        output_path = self.config['_resolved_output_path']
        
        self.log(f"Exporting STL to: {output_path}")
        
        try:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            if obj.type != 'MESH':
                self.log("Converting object to mesh for export", "INFO")
                bpy.ops.object.convert(target='MESH')
            
            # Try new export API first (Blender 3.3+)
            try:
                bpy.ops.wm.stl_export(
                    filepath=output_path,
                    export_selected_objects=True,
                    ascii_format=False,
                    apply_modifiers=True,
                    global_scale=1.0
                )
                self.log("Exported using new STL export API")
            except AttributeError:
                # Fall back to old API
                bpy.ops.export_mesh.stl(
                    filepath=output_path,
                    check_existing=False,
                    use_selection=True,
                    ascii=False,
                    apply_modifiers=True,
                    global_scale=1.0
                )
                self.log("Exported using legacy STL export API")
            
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                self.log(f"Successfully exported STL ({file_size:,} bytes)")
                return True
            else:
                self.log("ERROR: STL file was not created", "ERROR")
                return False
            
        except Exception as e:
            self.log(f"ERROR: Failed to export STL: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return False
    
    def run(self):
        """Main execution method"""
        try:
            self.log("Starting name ring generation...")
            if not self.load_config():
                return 2
            
            if not self.validate_config():
                return 1
            
            self.clear_scene()
            
            # Create the flowing name ring
            self.log("Creating flowing name ring...")
            ring_obj = self.create_flowing_name_ring()
            if not ring_obj:
                self.log("ERROR: Failed to create name ring", "ERROR")
                return 3
            
            # Export STL
            if not self.export_stl(ring_obj):
                return 2
            
            self.log("Name ring generation completed successfully")
            return 0
            
        except Exception as e:
            self.log(f"ERROR: Unexpected error: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return 3
        finally:
            self.log("Cleaning up Blender resources...")


def main():
    """Main entry point"""
    argv = sys.argv
    
    if "--" not in argv:
        print("ERROR: No config file specified. Usage: blender --background --python script.py -- config.json")
        sys.exit(1)
    
    argv = argv[argv.index("--") + 1:]
    
    if len(argv) < 1:
        print("ERROR: No config file specified. Usage: blender --background --python script.py -- config.json")
        sys.exit(1)
    
    config_path = argv[0]
    
    generator = RingTextGenerator(config_path)
    exit_code = generator.run()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
