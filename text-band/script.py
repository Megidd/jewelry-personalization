#!/usr/bin/env python3
"""
script.py - Blender script to create a 3D-printable name ring with readable script
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
        
        # Set defaults for name ring style
        self.config.setdefault('text_height', 5.0)  # Height of text
        self.config.setdefault('text_thickness', 1.5)  # Thickness/extrusion of text
        self.config.setdefault('ring_thickness', 2.5)  # Total ring thickness
        self.config.setdefault('text_position', 'center')  # center, inner, outer
        self.config.setdefault('repeat_text', True)  # Repeat text around ring
        self.config.setdefault('text_spacing', 2.0)  # Space between text repetitions
        self.config.setdefault('connect_letters', True)  # Connect letters smoothly
        self.config.setdefault('base_ring', False)  # Add thin base ring for support
        self.config.setdefault('base_ring_height', 1.0)
        self.config.setdefault('radial_segments', 256)
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
    
    def create_name_ring(self):
        """Create a ring where text forms a decorative band"""
        text = self.config['text']
        font_path = self.config['_resolved_font_path']
        inner_radius = self.config['inner_diameter'] / 2
        text_height = self.config['text_height']
        text_thickness = self.config['text_thickness']
        ring_thickness = self.config['ring_thickness']
        text_spacing = self.config['text_spacing']
        
        self.log("Creating name ring with properly positioned text...")
        
        # Calculate outer radius based on ring thickness
        outer_radius = inner_radius + ring_thickness
        
        # Load font
        try:
            font = bpy.data.fonts.load(font_path)
            self.log(f"Loaded font: {font_path}")
        except Exception as e:
            self.log(f"ERROR: Failed to load font: {e}", "ERROR")
            return None
        
        # Create list to hold all text objects
        text_objects = []
        
        # Calculate circumference at the middle of the ring
        middle_radius = inner_radius + (ring_thickness / 2)
        circumference = 2 * math.pi * middle_radius
        
        # Create initial text to measure its size
        test_curve = bpy.data.curves.new(type="FONT", name="TestText")
        test_curve.body = text
        test_curve.font = font
        test_curve.size = text_height
        test_curve.align_x = 'CENTER'
        test_curve.align_y = 'CENTER'
        
        test_obj = bpy.data.objects.new("TestText", test_curve)
        bpy.context.collection.objects.link(test_obj)
        
        # Convert to mesh to get accurate dimensions
        test_obj.select_set(True)
        bpy.context.view_layer.objects.active = test_obj
        bpy.ops.object.convert(target='MESH')
        
        # Get text width
        bbox = [test_obj.matrix_world @ Vector(corner) for corner in test_obj.bound_box]
        text_width = max([v.x for v in bbox]) - min([v.x for v in bbox])
        
        # Remove test object
        bpy.data.objects.remove(test_obj, do_unlink=True)
        
        # Calculate how many times text fits around ring
        total_text_space = text_width + text_spacing
        num_repetitions = int(circumference / total_text_space)
        
        if num_repetitions < 1:
            num_repetitions = 1
            self.log(f"WARNING: Text is too long for ring, using single instance", "WARNING")
        
        if not self.config.get('repeat_text', True):
            num_repetitions = 1
        
        self.log(f"Placing {num_repetitions} instances of text around ring")
        
        # Create text instances around the ring
        angle_step = (2 * math.pi) / num_repetitions
        
        for i in range(num_repetitions):
            # Create text object
            curve = bpy.data.curves.new(type="FONT", name=f"Text_{i}")
            curve.body = text
            curve.font = font
            curve.size = text_height
            curve.align_x = 'CENTER'
            curve.align_y = 'CENTER'
            curve.extrude = text_thickness
            curve.bevel_depth = 0.1  # Small bevel for smoother edges
            curve.bevel_resolution = 2
            
            text_obj = bpy.data.objects.new(f"Text_{i}", curve)
            bpy.context.collection.objects.link(text_obj)
            
            # Convert to mesh
            text_obj.select_set(True)
            bpy.context.view_layer.objects.active = text_obj
            bpy.ops.object.convert(target='MESH')
            
            # Position text
            angle = i * angle_step
            
            # Calculate position based on text_position setting
            if self.config.get('text_position', 'center') == 'outer':
                pos_radius = outer_radius - (text_thickness / 2)
            elif self.config.get('text_position', 'center') == 'inner':
                pos_radius = inner_radius + (text_thickness / 2)
            else:  # center
                pos_radius = middle_radius
            
            # Position at the correct angle and radius
            x = pos_radius * math.cos(angle)
            y = pos_radius * math.sin(angle)
            z = 0
            
            text_obj.location = (x, y, z)
            
            # Rotate to face outward
            text_obj.rotation_euler = (0, 0, angle - math.pi/2)
            
            # Apply transforms
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            
            text_objects.append(text_obj)
        
        # Join all text objects into one
        if len(text_objects) > 1:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in text_objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = text_objects[0]
            bpy.ops.object.join()
            combined_text = bpy.context.active_object
        else:
            combined_text = text_objects[0]
        
        combined_text.name = "NameRingText"
        
        # Create connecting geometry if requested
        if self.config.get('connect_letters', True):
            self.log("Creating letter connections...")
            combined_text = self.create_letter_connections(combined_text, middle_radius)
        
        # Add base ring if requested
        if self.config.get('base_ring', False):
            self.log("Adding base ring...")
            base_ring = self.create_base_ring(inner_radius, ring_thickness)
            
            # Combine with text
            bpy.ops.object.select_all(action='DESELECT')
            combined_text.select_set(True)
            bpy.context.view_layer.objects.active = combined_text
            
            modifier = combined_text.modifiers.new(name="BaseRing", type='BOOLEAN')
            modifier.operation = 'UNION'
            modifier.object = base_ring
            modifier.solver = 'EXACT'
            
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                bpy.data.objects.remove(base_ring, do_unlink=True)
            except:
                self.log("WARNING: Could not apply base ring boolean", "WARNING")
        
        # Clean up the mesh
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.01)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply smooth shading
        bpy.ops.object.shade_smooth()
        
        return combined_text
    
    def create_letter_connections(self, text_obj, radius):
        """Create smooth connections between letter instances"""
        # Add a solidify modifier to ensure manifold geometry
        solidify = text_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
        solidify.thickness = 0.2
        solidify.offset = 0
        bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Create a torus that will act as the connecting band
        bpy.ops.mesh.primitive_torus_add(
            major_radius=radius,
            minor_radius=self.config['text_height'] * 0.15,  # Thin connector
            major_segments=self.config['radial_segments'],
            minor_segments=16,
            location=(0, 0, 0)
        )
        
        connector = bpy.context.active_object
        connector.name = "Connector"
        
        # Combine text with connector
        bpy.ops.object.select_all(action='DESELECT')
        text_obj.select_set(True)
        bpy.context.view_layer.objects.active = text_obj
        
        modifier = text_obj.modifiers.new(name="Connect", type='BOOLEAN')
        modifier.operation = 'UNION'
        modifier.object = connector
        modifier.solver = 'EXACT'
        
        try:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            bpy.data.objects.remove(connector, do_unlink=True)
        except:
            self.log("WARNING: Could not create smooth connections", "WARNING")
            bpy.data.objects.remove(connector, do_unlink=True)
        
        return text_obj
    
    def create_base_ring(self, inner_radius, ring_thickness):
        """Create a thin base ring for structural support"""
        base_height = self.config.get('base_ring_height', 1.0)
        
        # Create cylinder for base ring
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=self.config['radial_segments'],
            radius=inner_radius + ring_thickness,
            depth=base_height,
            location=(0, 0, -self.config['text_height']/2 + base_height/2)
        )
        
        outer_cylinder = bpy.context.active_object
        
        # Create inner cylinder to subtract
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=self.config['radial_segments'],
            radius=inner_radius,
            depth=base_height * 2,
            location=(0, 0, -self.config['text_height']/2 + base_height/2)
        )
        
        inner_cylinder = bpy.context.active_object
        
        # Boolean difference to create ring
        outer_cylinder.select_set(True)
        bpy.context.view_layer.objects.active = outer_cylinder
        
        modifier = outer_cylinder.modifiers.new(name="MakeRing", type='BOOLEAN')
        modifier.operation = 'DIFFERENCE'
        modifier.object = inner_cylinder
        modifier.solver = 'EXACT'
        
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.data.objects.remove(inner_cylinder, do_unlink=True)
        
        outer_cylinder.name = "BaseRing"
        
        return outer_cylinder
    
    def export_stl(self, obj):
        """Export the final mesh as STL"""
        output_path = self.config['_resolved_output_path']
        
        self.log(f"Exporting STL to: {output_path}")
        
        try:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
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
            
            # Create the name ring
            self.log("Creating name ring...")
            ring_obj = self.create_name_ring()
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
        print("ERROR: No config file specified")
        sys.exit(1)
    
    config_path = argv[0]
    
    generator = RingTextGenerator(config_path)
    exit_code = generator.run()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
