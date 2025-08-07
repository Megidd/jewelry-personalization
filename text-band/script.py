#!/usr/bin/env python3
"""
script.py - Blender script to create a 3D-printable name ring
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
        
        # Set defaults for ring parameters
        self.config.setdefault('text_height', 4.0)
        self.config.setdefault('text_depth', 0.8)  # How deep text is embossed/raised
        self.config.setdefault('ring_thickness', 2.5)
        self.config.setdefault('ring_width', 8.0)  # Width of the ring band
        self.config.setdefault('text_style', 'raised')  # 'raised' or 'engraved'
        self.config.setdefault('repeat_text', True)
        self.config.setdefault('text_spacing', 1.5)
        self.config.setdefault('radial_segments', 128)
        self.config.setdefault('create_parent_dirs', True)
        
        # Validate font path
        font_path = self.config['font_path']
        if not os.path.isabs(font_path):
            font_path = self.config_dir / font_path
        font_path = Path(font_path).resolve()
        
        if not font_path.exists():
            self.log(f"ERROR: Font file not found: {font_path}", "ERROR")
            return False
        
        self.config['_resolved_font_path'] = str(font_path)
        
        # Validate text
        text = self.config['text']
        if not text or len(text.strip()) == 0:
            self.log("ERROR: Text cannot be empty", "ERROR")
            return False
        
        self.config['text'] = text.strip()
        
        # Validate dimensions
        inner_d = self.config['inner_diameter']
        if inner_d <= 0:
            self.log("ERROR: Inner diameter must be positive", "ERROR")
            return False
        
        if inner_d < 10:
            self.log(f"WARNING: Inner diameter ({inner_d}mm) is very small", "WARNING")
        
        # Resolve output path
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
    
    def create_base_ring(self):
        """Create the actual wearable ring band"""
        inner_radius = self.config['inner_diameter'] / 2
        ring_thickness = self.config['ring_thickness']
        ring_width = self.config['ring_width']
        
        self.log(f"Creating base ring: inner_diameter={self.config['inner_diameter']}mm, thickness={ring_thickness}mm, width={ring_width}mm")
        
        # Create outer cylinder
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=self.config['radial_segments'],
            radius=inner_radius + ring_thickness,
            depth=ring_width,
            location=(0, 0, 0)
        )
        outer_cylinder = bpy.context.active_object
        outer_cylinder.name = "OuterCylinder"
        
        # Create inner cylinder (the hole for the finger)
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=self.config['radial_segments'],
            radius=inner_radius,
            depth=ring_width + 1,  # Make it slightly taller for clean boolean
            location=(0, 0, 0)
        )
        inner_cylinder = bpy.context.active_object
        inner_cylinder.name = "InnerCylinder"
        
        # Boolean difference to create the ring
        modifier = outer_cylinder.modifiers.new(name="Boolean", type='BOOLEAN')
        modifier.operation = 'DIFFERENCE'
        modifier.object = inner_cylinder
        
        # Apply modifier
        bpy.context.view_layer.objects.active = outer_cylinder
        bpy.ops.object.modifier_apply(modifier="Boolean")
        
        # Delete the inner cylinder
        bpy.data.objects.remove(inner_cylinder, do_unlink=True)
        
        # Clean up the mesh
        bpy.context.view_layer.objects.active = outer_cylinder
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.001)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        outer_cylinder.name = "Ring"
        
        return outer_cylinder
    
    def add_text_to_ring(self, ring_obj):
        """Add text embossed or engraved on the ring surface"""
        text = self.config['text']
        font_path = self.config['_resolved_font_path']
        inner_radius = self.config['inner_diameter'] / 2
        ring_thickness = self.config['ring_thickness']
        text_height = self.config['text_height']
        text_depth = self.config['text_depth']
        text_spacing = self.config['text_spacing']
        text_style = self.config.get('text_style', 'raised')
        
        self.log(f"Adding {text_style} text to ring...")
        
        # Load font
        try:
            font = bpy.data.fonts.load(font_path)
            self.log(f"Loaded font: {font_path}")
        except Exception as e:
            self.log(f"ERROR: Failed to load font: {e}", "ERROR")
            return ring_obj
        
        # Calculate outer radius and circumference
        outer_radius = inner_radius + ring_thickness
        circumference = 2 * math.pi * outer_radius
        
        # Create test text to measure dimensions
        test_curve = bpy.data.curves.new(type="FONT", name="TestText")
        test_curve.body = text
        test_curve.font = font
        test_curve.size = text_height
        test_curve.align_x = 'CENTER'
        test_curve.align_y = 'CENTER'
        test_curve.extrude = text_depth
        test_curve.bevel_depth = 0.05
        test_curve.bevel_resolution = 2
        
        test_obj = bpy.data.objects.new("TestText", test_curve)
        bpy.context.collection.objects.link(test_obj)
        
        # Convert to mesh
        test_obj.select_set(True)
        bpy.context.view_layer.objects.active = test_obj
        bpy.ops.object.convert(target='MESH')
        
        # Get text width
        bbox = [test_obj.matrix_world @ Vector(corner) for corner in test_obj.bound_box]
        text_width = max([v.x for v in bbox]) - min([v.x for v in bbox])
        
        # Remove test object
        bpy.data.objects.remove(test_obj, do_unlink=True)
        
        # Calculate repetitions
        total_text_space = text_width + text_spacing
        num_repetitions = int(circumference / total_text_space)
        
        if num_repetitions < 1:
            num_repetitions = 1
            self.log(f"WARNING: Text is too long for ring circumference", "WARNING")
        
        if not self.config.get('repeat_text', True):
            num_repetitions = 1
        
        self.log(f"Creating {num_repetitions} text instances around ring")
        
        # Create text instances
        text_objects = []
        angle_step = (2 * math.pi) / num_repetitions
        
        for i in range(num_repetitions):
            # Create text curve
            curve = bpy.data.curves.new(type="FONT", name=f"Text_{i}")
            curve.body = text
            curve.font = font
            curve.size = text_height
            curve.align_x = 'CENTER'
            curve.align_y = 'CENTER'
            curve.extrude = text_depth
            curve.bevel_depth = 0.05
            curve.bevel_resolution = 2
            
            text_obj = bpy.data.objects.new(f"Text_{i}", curve)
            bpy.context.collection.objects.link(text_obj)
            
            # Convert to mesh
            text_obj.select_set(True)
            bpy.context.view_layer.objects.active = text_obj
            bpy.ops.object.convert(target='MESH')
            
            # Position text on ring surface
            angle = i * angle_step
            
            # Position at outer surface of ring
            if text_style == 'raised':
                # Text sits on outer surface
                x = (outer_radius + text_depth/2) * math.cos(angle)
                y = (outer_radius + text_depth/2) * math.sin(angle)
            else:  # engraved
                # Text will be subtracted from ring
                x = outer_radius * math.cos(angle)
                y = outer_radius * math.sin(angle)
            
            z = 0  # Center vertically on ring
            
            text_obj.location = (x, y, z)
            
            # Rotate to face outward
            text_obj.rotation_euler = (0, 0, angle - math.pi/2)
            
            # Apply transforms
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            
            text_objects.append(text_obj)
        
        # Combine all text objects
        if len(text_objects) > 0:
            if len(text_objects) > 1:
                bpy.ops.object.select_all(action='DESELECT')
                for obj in text_objects:
                    obj.select_set(True)
                bpy.context.view_layer.objects.active = text_objects[0]
                bpy.ops.object.join()
                combined_text = bpy.context.active_object
            else:
                combined_text = text_objects[0]
            
            combined_text.name = "RingText"
            
            # Apply text to ring using boolean
            if text_style == 'raised':
                # Union - add text to ring
                modifier = ring_obj.modifiers.new(name="TextUnion", type='BOOLEAN')
                modifier.operation = 'UNION'
                modifier.object = combined_text
            else:  # engraved
                # Difference - subtract text from ring
                modifier = ring_obj.modifiers.new(name="TextDifference", type='BOOLEAN')
                modifier.operation = 'DIFFERENCE'
                modifier.object = combined_text
            
            # Apply modifier
            bpy.context.view_layer.objects.active = ring_obj
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                # Delete the text object after successful boolean
                bpy.data.objects.remove(combined_text, do_unlink=True)
            except Exception as e:
                self.log(f"WARNING: Boolean operation failed, trying alternative method: {e}", "WARNING")
                # If boolean fails, just join the meshes (for raised text)
                if text_style == 'raised':
                    bpy.ops.object.select_all(action='DESELECT')
                    ring_obj.select_set(True)
                    combined_text.select_set(True)
                    bpy.context.view_layer.objects.active = ring_obj
                    bpy.ops.object.join()
                    ring_obj = bpy.context.active_object
                else:
                    # For engraved, we can't do much without boolean
                    self.log("ERROR: Cannot engrave text without working boolean operation", "ERROR")
                    bpy.data.objects.remove(combined_text, do_unlink=True)
        
        # Final cleanup
        bpy.context.view_layer.objects.active = ring_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.001)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply smooth shading
        bpy.ops.object.shade_smooth()
        
        return ring_obj
    
    def export_stl(self, obj):
        """Export the final mesh as STL"""
        output_path = self.config['_resolved_output_path']
        
        self.log(f"Exporting STL to: {output_path}")
        
        try:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # Ensure mesh is valid
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.fill_holes(sides=0)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Export
            try:
                # Try new API (Blender 3.3+)
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
            return False
    
    def run(self):
        """Main execution method"""
        try:
            self.log("Starting ring generation...")
            self.log("="*60)
            
            if not self.load_config():
                return 2
            
            if not self.validate_config():
                return 1
            
            self.clear_scene()
            
            # Create the base ring first
            self.log("Creating base ring...")
            ring = self.create_base_ring()
            if not ring:
                self.log("ERROR: Failed to create base ring", "ERROR")
                return 3
            
            # Add text to the ring
            ring = self.add_text_to_ring(ring)
            
            # Export STL
            if not self.export_stl(ring):
                return 2
            
            self.log("="*60)
            self.log("Ring generation completed successfully!")
            self.log(f"Output file: {self.config['_resolved_output_path']}")
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
        print("ERROR: No config file specified")
        sys.exit(1)
    
    config_path = argv[0]
    
    generator = RingTextGenerator(config_path)
    exit_code = generator.run()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
