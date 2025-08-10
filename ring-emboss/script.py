#!/usr/bin/env python3
"""
script.py - Blender script to create a 3D-printable ring with custom embossed text
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
        if 'output' in self.config and 'log_filename' in self.config['output']:
            log_path = self.config['output']['log_filename']
            if not os.path.isabs(log_path):
                log_path = self.config_dir / log_path
            self.log_file = Path(log_path)
            
            # Create parent directories if needed and configured
            if self.config['output'].get('create_parent_dirs', True) and self.log_file.parent:
                try:
                    self.log_file.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"Warning: Could not create log directory: {e}")
                    self.log_file = None
                    return
            
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
        # Check for required sections
        required_sections = ['ring', 'text', 'output']
        for section in required_sections:
            if section not in self.config:
                self.log(f"ERROR: Missing required section: {section}", "ERROR")
                return False
        
        # Validate ring section
        ring_config = self.config['ring']
        required_ring_fields = ['inner_diameter', 'outer_diameter', 'length']
        
        for field in required_ring_fields:
            if field not in ring_config:
                self.log(f"ERROR: Missing required ring field: {field}", "ERROR")
                return False
        
        # Set ring defaults
        ring_config.setdefault('radial_segments', 256)
        ring_config.setdefault('vertical_segments', 64)
        
        # Validate text section
        text_config = self.config['text']
        
        required_text_fields = ['content', 'font_path', 'font_size', 'depth', 'direction']
        
        for field in required_text_fields:
            if field not in text_config:
                self.log(f"ERROR: Missing required text field: {field}", "ERROR")
                return False
        
        # Validate output section
        output_config = self.config['output']
        if 'stl_filename' not in output_config:
            self.log("ERROR: Missing required output field: stl_filename", "ERROR")
            return False
        
        # Set output defaults
        output_config.setdefault('create_parent_dirs', True)
        
        # Validate font path
        font_path = text_config['font_path']
        if not os.path.isabs(font_path):
            font_path = self.config_dir / font_path
        font_path = Path(font_path).resolve()
        
        if not font_path.exists():
            self.log(f"ERROR: Font file not found: {font_path}", "ERROR")
            return False
        
        if not font_path.suffix.lower() in ['.ttf', '.otf']:
            self.log(f"ERROR: Font file must be TTF or OTF format: {font_path}", "ERROR")
            return False
        
        text_config['_resolved_font_path'] = str(font_path)
        
        # Validate text content
        text = text_config['content']
        if not text or len(text.strip()) == 0:
            self.log("ERROR: Text content cannot be empty", "ERROR")
            return False
        
        # Remove newlines as specified
        text_config['content'] = text.replace('', '').replace('\r', '')
        
        # Check text length
        if len(text_config['content']) > 500:
            self.log(f"ERROR: Text length ({len(text_config['content'])}) exceeds maximum of 500 characters", "ERROR")
            return False
        
        # Validate ring dimensions
        inner_d = ring_config['inner_diameter']
        outer_d = ring_config['outer_diameter']
        length = ring_config['length']
        
        if inner_d <= 0 or outer_d <= 0 or length <= 0:
            self.log("ERROR: Ring dimensions must be positive", "ERROR")
            return False
        
        if inner_d >= outer_d:
            self.log(f"ERROR: Inner diameter ({inner_d}) must be less than outer diameter ({outer_d})", "ERROR")
            return False
        
        # Check minimum inner diameter
        if inner_d < 10:
            self.log(f"WARNING: Inner diameter ({inner_d}mm) is less than recommended minimum of 10mm", "WARNING")
        
        # Check maximum outer diameter
        if outer_d > 50:
            self.log(f"WARNING: Outer diameter ({outer_d}mm) exceeds recommended maximum of 50mm", "WARNING")
        
        # Check ring thickness
        ring_thickness = (outer_d - inner_d) / 2
        if ring_thickness < 1.5:
            self.log(f"WARNING: Ring thickness ({ring_thickness}mm) is less than recommended minimum of 1.5mm", "WARNING")
        
        # Validate font_size
        font_size = text_config['font_size']
        if font_size <= 0:
            self.log("ERROR: Font size must be positive", "ERROR")
            return False
        
        # Validate text depth
        text_depth = text_config['depth']
        
        if text_depth <= 0:
            self.log("ERROR: Text depth must be positive", "ERROR")
            return False

        # Validate text direction
        text_direction = text_config.get('direction', 'normal')
        if text_direction not in ['normal', 'inverted']:
            self.log(f"ERROR: Invalid text direction '{text_direction}', must be 'normal' or 'inverted'", "ERROR")
            return False
        
        # Validate segment counts
        radial_segments = ring_config['radial_segments']
        vertical_segments = ring_config['vertical_segments']
        
        if radial_segments < 128:
            self.log(f"ERROR: radial_segments ({radial_segments}) must be >= 128", "ERROR")
            return False
        
        if vertical_segments < 32:
            self.log(f"ERROR: vertical_segments ({vertical_segments}) must be >= 32", "ERROR")
            return False
        
        # Resolve output file path
        output_path = output_config['stl_filename']
        if not os.path.isabs(output_path):
            output_path = self.config_dir / output_path
        output_config['_resolved_output_path'] = str(Path(output_path).resolve())
        
        # Create parent directories if needed
        output_dir = Path(output_config['_resolved_output_path']).parent
        if output_config.get('create_parent_dirs', True) and output_dir:
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
        ring_config = self.config['ring']
        inner_radius = ring_config['inner_diameter'] / 2
        outer_radius = ring_config['outer_diameter'] / 2
        length = ring_config['length']
        radial_segments = ring_config['radial_segments']
        vertical_segments = ring_config['vertical_segments']
        
        self.log(f"Creating ring mesh with {radial_segments} radial and {vertical_segments} vertical segments...")
        
        # Create mesh
        mesh = bpy.data.meshes.new(name="Ring")
        ring_obj = bpy.data.objects.new("Ring", mesh)
        bpy.context.collection.objects.link(ring_obj)
        
        # Create geometry using bmesh for better control
        bm = bmesh.new()
        
        # Create vertices for rings at different heights
        for v_idx in range(vertical_segments + 1):
            z = -length/2 + (length * v_idx / vertical_segments)
            
            # Outer circle
            for r_idx in range(radial_segments):
                angle = 2 * math.pi * r_idx / radial_segments
                x = outer_radius * math.cos(angle)
                y = outer_radius * math.sin(angle)
                bm.verts.new((x, y, z))
            
            # Inner circle
            for r_idx in range(radial_segments):
                angle = 2 * math.pi * r_idx / radial_segments
                x = inner_radius * math.cos(angle)
                y = inner_radius * math.sin(angle)
                bm.verts.new((x, y, z))
        
        bm.verts.ensure_lookup_table()
        
        # Create faces
        verts_per_ring = radial_segments * 2
        
        # Side faces
        for v_idx in range(vertical_segments):
            ring_offset = v_idx * verts_per_ring
            next_ring_offset = (v_idx + 1) * verts_per_ring
            
            # Outer surface
            for r_idx in range(radial_segments):
                next_r = (r_idx + 1) % radial_segments
                v1 = bm.verts[ring_offset + r_idx]
                v2 = bm.verts[ring_offset + next_r]
                v3 = bm.verts[next_ring_offset + next_r]
                v4 = bm.verts[next_ring_offset + r_idx]
                bm.faces.new([v1, v2, v3, v4])
            
            # Inner surface
            for r_idx in range(radial_segments):
                next_r = (r_idx + 1) % radial_segments
                v1 = bm.verts[ring_offset + radial_segments + r_idx]
                v2 = bm.verts[next_ring_offset + radial_segments + r_idx]
                v3 = bm.verts[next_ring_offset + radial_segments + next_r]
                v4 = bm.verts[ring_offset + radial_segments + next_r]
                bm.faces.new([v1, v2, v3, v4])
        
        # Top face
        top_offset = vertical_segments * verts_per_ring
        for r_idx in range(radial_segments):
            next_r = (r_idx + 1) % radial_segments
            v1 = bm.verts[top_offset + r_idx]
            v2 = bm.verts[top_offset + next_r]
            v3 = bm.verts[top_offset + radial_segments + next_r]
            v4 = bm.verts[top_offset + radial_segments + r_idx]
            bm.faces.new([v1, v2, v3, v4])
        
        # Bottom face
        for r_idx in range(radial_segments):
            next_r = (r_idx + 1) % radial_segments
            v1 = bm.verts[r_idx]
            v2 = bm.verts[radial_segments + r_idx]
            v3 = bm.verts[radial_segments + next_r]
            v4 = bm.verts[next_r]
            bm.faces.new([v1, v2, v3, v4])
        
        # Update mesh
        bm.to_mesh(mesh)
        bm.free()
        
        # Apply smooth shading
        ring_obj.select_set(True)
        bpy.context.view_layer.objects.active = ring_obj
        bpy.ops.object.shade_smooth()
        
        self.log(f"Created ring: inner_d={ring_config['inner_diameter']}mm, "
                f"outer_d={ring_config['outer_diameter']}mm, length={ring_config['length']}mm")
        
        return ring_obj
    
    def create_text(self):
        """Create 3D text positioned on the ring"""
        text_config = self.config['text']
        ring_config = self.config['ring']
        
        text = text_config['content']
        font_path = text_config['_resolved_font_path']
        font_size = text_config['font_size']
        text_depth = text_config['depth']
        outer_radius = ring_config['outer_diameter'] / 2
        text_direction = text_config.get('direction', 'normal')
        
        self.log("Creating text object...")
        
        # Load font
        try:
            font = bpy.data.fonts.load(font_path)
            self.log(f"Loaded font: {font_path}")
        except Exception as e:
            self.log(f"ERROR: Failed to load font: {e}", "ERROR")
            return None
        
        # Create text curve object
        curve = bpy.data.curves.new(type="FONT", name="Text")
        curve.body = text
        curve.font = font
        
        # Set text properties
        curve.size = font_size
        curve.extrude = text_depth
        curve.bevel_depth = 0
        curve.align_x = 'CENTER'
        curve.align_y = 'CENTER'
        
        # No letter spacing adjustment - let the font handle natural spacing
        # This preserves cursive connections
        
        # Create text object
        text_obj = bpy.data.objects.new("Text", curve)
        bpy.context.collection.objects.link(text_obj)
        
        # Convert to mesh
        text_obj.select_set(True)
        bpy.context.view_layer.objects.active = text_obj
        
        self.log("Converting text to mesh...")
        bpy.ops.object.convert(target='MESH')
        
        # Apply initial rotation to make text face outward
        text_obj.rotation_euler = (-math.pi/2, 0, 0)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Curve the text around the ring
        success = self.curve_text_mesh(text_obj, outer_radius, text_direction)
        
        if success:
            self.log(f"Created embossed text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            return text_obj
        else:
            return None
    
    def curve_text_mesh(self, text_obj, radius, text_direction):
        """Curve the text mesh around the ring with proper positioning"""
        text_config = self.config['text']
        mesh = text_obj.data
        
        # Get text bounds
        text_obj.select_set(True)
        bpy.context.view_layer.objects.active = text_obj
        
        # Calculate bounding box
        bbox_corners = [text_obj.matrix_world @ Vector(corner) for corner in text_obj.bound_box]
        min_x = min([v.x for v in bbox_corners])
        max_x = max([v.x for v in bbox_corners])
        min_y = min([v.y for v in bbox_corners])
        max_y = max([v.y for v in bbox_corners])
        min_z = min([v.z for v in bbox_corners])
        max_z = max([v.z for v in bbox_corners])
        
        text_width = max_x - min_x
        text_depth_actual = max_y - min_y
        text_height = max_z - min_z
        text_center_x = (min_x + max_x) / 2
        text_center_z = (min_z + max_z) / 2
        
        # For embossed text, we need to position the back face at the surface
        y_offset = -min_y  # This moves the back face to Y=0
        
        # Check if text fits around circumference
        circumference = 2 * math.pi * radius
        available_circumference = circumference - 2  # 2mm safety gap
        
        if text_width > available_circumference:
            self.log(f"WARNING: Text width ({text_width:.2f}mm) exceeds available circumference ({available_circumference:.2f}mm), "
                    f"text will be truncated", "WARNING")
        
        # Calculate angular span
        text_angle = min(text_width / radius, (available_circumference / radius))
        
        self.log(f"Curving text around ring (width: {text_width:.2f}mm, angle: {math.degrees(text_angle):.2f}°)")
        self.log(f"Text depth range: {min_y:.3f} to {max_y:.3f}mm, applying offset: {y_offset:.3f}mm")
        
        # Apply curve deformation to vertices
        for vertex in mesh.vertices:
            x = vertex.co.x - text_center_x
            y = vertex.co.y + y_offset  # Apply the offset to normalize position
            z = vertex.co.z - text_center_z  # Center vertically
            
            # Check if vertex is within allowed range
            if abs(x) > available_circumference / 2:
                continue  # Skip vertices outside allowed range (truncation)
            
            # Calculate angle for this vertex
            if text_direction == 'inverted':
                # For inverted text, reverse the angle
                angle = -(x / radius)
            else:
                # Normal text direction
                angle = (x / radius)
            
            # Calculate radial position
            # For embossed text, add to radius (going outward)
            r = radius + y  # y will be >= 0, so this increases radius
            
            # Convert to cylindrical coordinates
            # Position at +Y axis intersection as per spec
            new_x = r * math.sin(angle)
            new_y = r * math.cos(angle)
            new_z = z
            
            vertex.co = Vector((new_x, new_y, new_z))
        
        # Update mesh
        mesh.update()
        
        # Ensure proper normals
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        return True
    
    def calculate_mesh_volume(self, mesh_obj):
        """Calculate the volume of a mesh object using bmesh"""
        try:
            # Get the mesh data
            mesh = mesh_obj.data
            
            # Create bmesh from mesh
            bm = bmesh.new()
            bm.from_mesh(mesh)
            
            # Ensure mesh is triangulated for accurate volume calculation
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            
            # Calculate volume using the divergence theorem
            # Volume = (1/3) * sum of (face_normal · face_center) * face_area
            volume = 0.0
            
            for face in bm.faces:
                # Get face center
                center = face.calc_center_median()
                
                # Get face normal
                normal = face.normal
                
                # Get face area
                area = face.calc_area()
                
                # Add contribution to volume
                # The dot product gives us the signed distance from origin
                volume += (center.dot(normal) * area) / 3.0
            
            # Clean up
            bm.free()
            
            # Convert to positive value (in case normals were flipped)
            volume = abs(volume)
            
            # Convert from cubic Blender units to cubic millimeters
            # (assuming 1 Blender unit = 1mm as per the script design)
            volume_mm3 = volume
            
            # Also calculate in cubic centimeters for easier reading
            volume_cm3 = volume_mm3 / 1000.0
            
            return volume_mm3, volume_cm3
            
        except Exception as e:
            self.log(f"ERROR: Failed to calculate volume: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return None, None
    
    def combine_ring_and_text(self, ring_obj, text_obj):
        """Combine ring and text by merging meshes directly"""
        self.log("Merging ring and text meshes...")
        
        try:
            # Get the mesh data
            ring_mesh = ring_obj.data
            text_mesh = text_obj.data
            
            # Create a new mesh for the combined result
            combined_mesh = bpy.data.meshes.new(name="CombinedRing")
            
            # Get vertex and face data from both meshes
            ring_verts = [(v.co.x, v.co.y, v.co.z) for v in ring_mesh.vertices]
            text_verts = [(v.co.x, v.co.y, v.co.z) for v in text_mesh.vertices]
            
            # Combine vertices
            all_verts = ring_verts + text_verts
            
            # Get faces from ring mesh
            ring_faces = []
            for poly in ring_mesh.polygons:
                face = [v for v in poly.vertices]
                ring_faces.append(face)
            
            # Get faces from text mesh and offset indices
            text_faces = []
            vertex_offset = len(ring_verts)
            for poly in text_mesh.polygons:
                face = [v + vertex_offset for v in poly.vertices]
                text_faces.append(face)
            
            # Combine faces
            all_faces = ring_faces + text_faces
            
            # Create the combined mesh
            combined_mesh.from_pydata(all_verts, [], all_faces)
            combined_mesh.update()
            
            # Create new object with combined mesh
            combined_obj = bpy.data.objects.new("FinalRing", combined_mesh)
            bpy.context.collection.objects.link(combined_obj)
            
            # Copy materials if any
            if len(ring_obj.data.materials) > 0:
                for mat in ring_obj.data.materials:
                    combined_obj.data.materials.append(mat)
            
            # Select and make active
            bpy.ops.object.select_all(action='DESELECT')
            combined_obj.select_set(True)
            bpy.context.view_layer.objects.active = combined_obj
            
            # Clean up duplicate vertices at boundaries (optional but recommended)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Apply smooth shading
            bpy.ops.object.shade_smooth()
            
            # Delete the original objects
            bpy.data.objects.remove(ring_obj, do_unlink=True)
            bpy.data.objects.remove(text_obj, do_unlink=True)
            
            self.log(f"Successfully merged meshes: {len(all_verts)} vertices, {len(all_faces)} faces")
            return combined_obj
            
        except Exception as e:
            self.log(f"ERROR: Failed to merge meshes: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return None
    
    def export_stl(self, obj):
        """Export the final mesh as STL"""
        output_path = self.config['output']['_resolved_output_path']
        
        # Calculate volume before export
        self.log("Calculating mesh volume...")
        volume_mm3, volume_cm3 = self.calculate_mesh_volume(obj)
        
        if volume_mm3 is not None:
            self.log(f"Mesh volume: {volume_mm3:.2f} mm³ ({volume_cm3:.3f} cm³)")
            
            # Also log some useful derived information
            # Assuming common 3D printing materials
            pla_density = 1.24  # g/cm³
            abs_density = 1.05  # g/cm³
            petg_density = 1.27  # g/cm³
            
            self.log("Estimated material weight:")
            self.log(f"  - PLA: {volume_cm3 * pla_density:.2f} g")
            self.log(f"  - ABS: {volume_cm3 * abs_density:.2f} g")
            self.log(f"  - PETG: {volume_cm3 * petg_density:.2f} g")
        else:
            self.log("WARNING: Could not calculate mesh volume", "WARNING")
        
        self.log(f"Exporting STL to: {output_path}")
        
        try:
            # Select only the final object
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # Ensure we have a mesh
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
            
            # Verify file was created
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                self.log(f"Successfully exported STL ({file_size:,} bytes)")
                
                # Log final summary
                self.log("-" * 60)
                self.log("EXPORT SUMMARY:")
                self.log(f"  Output file: {output_path}")
                self.log(f"  File size: {file_size:,} bytes")
                if volume_mm3 is not None:
                    self.log(f"  Volume: {volume_mm3:.2f} mm³ ({volume_cm3:.3f} cm³)")
                self.log("-" * 60)
                
                return True
            else:
                self.log("ERROR: STL file was not created", "ERROR")
                return False
            
        except Exception as e:
            self.log(f"ERROR: Failed to export STL: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return False
    
    def cleanup_on_error(self):
        """Clean up temporary files on error"""
        try:
            # Clean up any partial output files
            if hasattr(self, 'config') and 'output' in self.config and '_resolved_output_path' in self.config['output']:
                output_path = Path(self.config['output']['_resolved_output_path'])
                if output_path.exists() and output_path.stat().st_size == 0:
                    output_path.unlink()
                    self.log("Cleaned up empty output file")
        except Exception as e:
            self.log(f"Warning: Could not clean up files: {e}", "WARNING")
    
    def run(self):
        """Main execution method"""
        try:
            # Load configuration
            self.log("Starting ring generation...")
            if not self.load_config():
                return 2  # File I/O error
            
            # Validate configuration
            if not self.validate_config():
                return 1  # Input validation error
            
            # Clear scene
            self.clear_scene()
            
            # Create ring
            self.log("Creating ring geometry...")
            ring_obj = self.create_ring()
            if not ring_obj:
                self.log("ERROR: Failed to create ring", "ERROR")
                return 3  # Blender operation error
            
            # Create text
            self.log("Creating text geometry...")
            text_obj = self.create_text()
            if not text_obj:
                self.log("ERROR: Failed to create text", "ERROR")
                return 4  # Font rendering error
            
            # Combine ring and text
            self.log("Combining ring and text...")
            final_obj = self.combine_ring_and_text(ring_obj, text_obj)
            if not final_obj:
                self.log("ERROR: Failed to combine ring and text", "ERROR")
                self.cleanup_on_error()
                return 3  # Blender operation error
            
            # Export STL
            if not self.export_stl(final_obj):
                self.cleanup_on_error()
                return 2  # File I/O error
            
            self.log("Ring generation completed successfully")
            return 0  # Success
            
        except Exception as e:
            self.log(f"ERROR: Unexpected error: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            self.cleanup_on_error()
            return 3  # Blender operation error
        finally:
            # Always ensure Blender is properly closed
            self.log("Cleaning up Blender resources...")


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
