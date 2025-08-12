#!/usr/bin/env python3
"""
script.py - Blender script to create a 3D-printable ring with custom embossed text
where text occupies part of the arc and ring fills the remainder
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
        self.report_data = {}  # Store data for JSON report
        self.text_start_angle = None  # Will store where text starts
        self.text_end_angle = None    # Will store where text ends
        
    def log(self, message, level="INFO"):
        """Log message to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] [{level}] {message}"
        print(formatted_msg)
        self.log_messages.append(formatted_msg)
        
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(formatted_msg + '\n')
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
                    f.write(f"Ring Text Generator Log - Started at {datetime.now()}\n")
                    f.write(f"Config file: {self.config_path}\n")
                    f.write("-" * 60 + "\n")
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
        
        # Validate material section if present
        if 'material' in self.config:
            material_config = self.config['material']
            # Set default density if not specified (PLA default)
            material_config.setdefault('density', 1.24)  # g/cm³
            material_config.setdefault('name', 'PLA')
            
            # Validate density
            if material_config['density'] <= 0:
                self.log("ERROR: Material density must be positive", "ERROR")
                return False
        else:
            # Create default material config
            self.config['material'] = {
                'name': 'PLA',
                'density': 1.24  # g/cm³
            }
        
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
        text_config['content'] = text.replace('\n', '').replace('\r', '')
        
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
        
        # Resolve output file paths
        output_path = output_config['stl_filename']
        if not os.path.isabs(output_path):
            output_path = self.config_dir / output_path
        output_config['_resolved_output_path'] = str(Path(output_path).resolve())
        
        # Resolve report file path if specified
        if 'report_filename' in output_config:
            report_path = output_config['report_filename']
            if not os.path.isabs(report_path):
                report_path = self.config_dir / report_path
            output_config['_resolved_report_path'] = str(Path(report_path).resolve())
        
        # Create parent directories if needed
        output_dir = Path(output_config['_resolved_output_path']).parent
        if output_config.get('create_parent_dirs', True) and output_dir:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.log(f"ERROR: Could not create output directory: {e}", "ERROR")
                return False
        
        # Create report directory if needed
        if '_resolved_report_path' in output_config:
            report_dir = Path(output_config['_resolved_report_path']).parent
            if output_config.get('create_parent_dirs', True) and report_dir:
                try:
                    report_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.log(f"ERROR: Could not create report directory: {e}", "ERROR")
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
    
    def create_text_and_calculate_arc(self):
        """Create 3D text and calculate the arc it occupies"""
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
        
        # Get text bounds before curving
        bbox_corners = [text_obj.matrix_world @ Vector(corner) for corner in text_obj.bound_box]
        min_x = min([v.x for v in bbox_corners])
        max_x = max([v.x for v in bbox_corners])
        text_width = max_x - min_x
        
        # Calculate the arc that the text will occupy
        text_angle_span = text_width / outer_radius
        
        # Add small padding (2 degrees on each side)
        padding_angle = math.radians(2)
        total_angle_span = text_angle_span + 2 * padding_angle
        
        # Calculate start and end angles
        # Center the text at angle 0 (positive Y axis)
        self.text_start_angle = -total_angle_span / 2
        self.text_end_angle = total_angle_span / 2
        
        self.log(f"Text arc: {math.degrees(self.text_start_angle):.2f}° to {math.degrees(self.text_end_angle):.2f}°")
        self.log(f"Text angular span: {math.degrees(total_angle_span):.2f}°")
        
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
        
        self.log(f"Curving text around ring (width: {text_width:.2f}mm)")
        self.log(f"Text depth range: {min_y:.3f} to {max_y:.3f}mm, applying offset: {y_offset:.3f}mm")
        
        # Apply curve deformation to vertices
        for vertex in mesh.vertices:
            x = vertex.co.x - text_center_x
            y = vertex.co.y + y_offset  # Apply the offset to normalize position
            z = vertex.co.z - text_center_z  # Center vertically
            
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
    
    def create_partial_ring(self, start_angle, end_angle):
        """Create a partial ring from end_angle to start_angle (to fill the gap left by text)"""
        ring_config = self.config['ring']
        inner_radius = ring_config['inner_diameter'] / 2
        outer_radius = ring_config['outer_diameter'] / 2
        length = ring_config['length']
        radial_segments = ring_config['radial_segments']
        vertical_segments = ring_config['vertical_segments']
        
        # The ring goes from text end to text start (wrapping around)
        # This means from end_angle to start_angle + 2π
        ring_start = end_angle
        ring_end = start_angle + 2 * math.pi
        ring_span = ring_end - ring_start
        
        # Calculate segments for this partial ring
        segments_for_arc = max(3, int(radial_segments * ring_span / (2 * math.pi)))
        
        self.log(f"Creating partial ring from {math.degrees(ring_start):.2f}° to {math.degrees(ring_end):.2f}°")
        self.log(f"Ring arc span: {math.degrees(ring_span):.2f}°")
        self.log(f"Using {segments_for_arc} radial segments for the arc")
        
        # Create mesh
        mesh = bpy.data.meshes.new(name="PartialRing")
        ring_obj = bpy.data.objects.new("PartialRing", mesh)
        bpy.context.collection.objects.link(ring_obj)
        
        # Create geometry using bmesh
        bm = bmesh.new()
        
        # Create vertices for rings at different heights
        for v_idx in range(vertical_segments + 1):
            z = -length/2 + (length * v_idx / vertical_segments)
            
            # Outer circle arc
            for r_idx in range(segments_for_arc + 1):
                angle = ring_start + (ring_span * r_idx / segments_for_arc)
                x = outer_radius * math.sin(angle)
                y = outer_radius * math.cos(angle)
                bm.verts.new((x, y, z))
            
            # Inner circle arc
            for r_idx in range(segments_for_arc + 1):
                angle = ring_start + (ring_span * r_idx / segments_for_arc)
                x = inner_radius * math.sin(angle)
                y = inner_radius * math.cos(angle)
                bm.verts.new((x, y, z))
        
        bm.verts.ensure_lookup_table()
        
        # Create faces
        verts_per_ring = (segments_for_arc + 1) * 2
        
        # Side faces
        for v_idx in range(vertical_segments):
            ring_offset = v_idx * verts_per_ring
            next_ring_offset = (v_idx + 1) * verts_per_ring
            
            # Outer surface
            for r_idx in range(segments_for_arc):
                v1 = bm.verts[ring_offset + r_idx]
                v2 = bm.verts[ring_offset + r_idx + 1]
                v3 = bm.verts[next_ring_offset + r_idx + 1]
                v4 = bm.verts[next_ring_offset + r_idx]
                bm.faces.new([v1, v2, v3, v4])
            
            # Inner surface
            inner_start = segments_for_arc + 1
            for r_idx in range(segments_for_arc):
                v1 = bm.verts[ring_offset + inner_start + r_idx]
                v2 = bm.verts[next_ring_offset + inner_start + r_idx]
                v3 = bm.verts[next_ring_offset + inner_start + r_idx + 1]
                v4 = bm.verts[ring_offset + inner_start + r_idx + 1]
                bm.faces.new([v1, v2, v3, v4])
        
        # Top face
        top_offset = vertical_segments * verts_per_ring
        for r_idx in range(segments_for_arc):
            v1 = bm.verts[top_offset + r_idx]
            v2 = bm.verts[top_offset + r_idx + 1]
            v3 = bm.verts[top_offset + segments_for_arc + 1 + r_idx + 1]
            v4 = bm.verts[top_offset + segments_for_arc + 1 + r_idx]
            bm.faces.new([v1, v2, v3, v4])
        
        # Bottom face
        for r_idx in range(segments_for_arc):
            v1 = bm.verts[r_idx]
            v2 = bm.verts[segments_for_arc + 1 + r_idx]
            v3 = bm.verts[segments_for_arc + 1 + r_idx + 1]
            v4 = bm.verts[r_idx + 1]
            bm.faces.new([v1, v2, v3, v4])
        
        # End caps (where the arc starts and ends)
        # Start cap
        for v_idx in range(vertical_segments):
            ring_offset = v_idx * verts_per_ring
            next_ring_offset = (v_idx + 1) * verts_per_ring
            
            v1 = bm.verts[ring_offset + 0]  # outer, current height
            v2 = bm.verts[ring_offset + segments_for_arc + 1]  # inner, current height
            v3 = bm.verts[next_ring_offset + segments_for_arc + 1]  # inner, next height
            v4 = bm.verts[next_ring_offset + 0]  # outer, next height
            bm.faces.new([v1, v2, v3, v4])
        
        # End cap
        for v_idx in range(vertical_segments):
            ring_offset = v_idx * verts_per_ring
            next_ring_offset = (v_idx + 1) * verts_per_ring
            
            v1 = bm.verts[ring_offset + segments_for_arc]  # outer, current height
            v2 = bm.verts[next_ring_offset + segments_for_arc]  # outer, next height
            v3 = bm.verts[next_ring_offset + segments_for_arc + 1 + segments_for_arc]  # inner, next height
            v4 = bm.verts[ring_offset + segments_for_arc + 1 + segments_for_arc]  # inner, current height
            bm.faces.new([v1, v2, v3, v4])
        
        # Update mesh
        bm.to_mesh(mesh)
        bm.free()
        
        # Apply smooth shading
        ring_obj.select_set(True)
        bpy.context.view_layer.objects.active = ring_obj
        bpy.ops.object.shade_smooth()
        
        self.log(f"Created partial ring: inner_d={ring_config['inner_diameter']}mm, "
                f"outer_d={ring_config['outer_diameter']}mm, length={ring_config['length']}mm")
        
        return ring_obj
    
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
    
    def combine_ring_and_text_with_wedges(self, ring_obj, text_obj, wedge_objs):
        """Combine ring, text, and wedges by merging meshes directly"""
        self.log("Merging ring, text, and wedge meshes...")

        try:
            # Get the mesh data
            ring_mesh = ring_obj.data
            text_mesh = text_obj.data
            
            # Create a new mesh for the combined result
            combined_mesh = bpy.data.meshes.new(name="CombinedRing")

            # Get vertex data from all meshes
            all_verts = []
            all_faces = []
            vertex_offset = 0
            
            # Add ring vertices and faces
            ring_verts = [(v.co.x, v.co.y, v.co.z) for v in ring_mesh.vertices]
            all_verts.extend(ring_verts)
            
            for poly in ring_mesh.polygons:
                face = [v for v in poly.vertices]
                all_faces.append(face)
            
            vertex_offset = len(ring_verts)
            
            # Add text vertices and faces
            text_verts = [(v.co.x, v.co.y, v.co.z) for v in text_mesh.vertices]
            all_verts.extend(text_verts)
            
            for poly in text_mesh.polygons:
                face = [v + vertex_offset for v in poly.vertices]
                all_faces.append(face)
            
            vertex_offset += len(text_verts)
            
            # Add wedge vertices and faces
            for wedge_obj in wedge_objs:
                wedge_mesh = wedge_obj.data
                wedge_verts = [(v.co.x, v.co.y, v.co.z) for v in wedge_mesh.vertices]
                all_verts.extend(wedge_verts)
                
                for poly in wedge_mesh.polygons:
                    face = [v + vertex_offset for v in poly.vertices]
                    all_faces.append(face)
                
                vertex_offset += len(wedge_verts)

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

            # Clean up duplicate vertices at boundaries
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
            for wedge_obj in wedge_objs:
                bpy.data.objects.remove(wedge_obj, do_unlink=True)

            self.log(f"Successfully merged meshes: {len(all_verts)} vertices, {len(all_faces)} faces")
            return combined_obj

        except Exception as e:
            self.log(f"ERROR: Failed to merge meshes: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return None

    def create_transition_wedges(self):
        """Create small wedge meshes to bridge gaps between text and ring"""
        ring_config = self.config['ring']
        inner_radius = ring_config['inner_diameter'] / 2
        outer_radius = ring_config['outer_diameter'] / 2
        length = ring_config['length']
        text_depth = self.config['text']['depth']
        
        wedges = []
        
        # First, we need to analyze the text mesh to find actual boundary vertices
        # Get the text object (assuming it exists in the scene)
        text_obj = None
        for obj in bpy.data.objects:
            if obj.name == "Text" and obj.type == 'MESH':
                text_obj = obj
                break
        
        if not text_obj:
            self.log("WARNING: Could not find text object for wedge creation", "WARNING")
            return wedges
        
        text_mesh = text_obj.data
        
        # Find the actual leftmost and rightmost vertices of the text
        leftmost_angle = float('inf')
        rightmost_angle = float('-inf')
        leftmost_vertices = []
        rightmost_vertices = []
        
        # Analyze all vertices to find boundaries
        for vertex in text_mesh.vertices:
            # Calculate angle for this vertex
            x, y, z = vertex.co
            if x != 0 or y != 0:  # Avoid division by zero
                angle = math.atan2(x, y)
                
                # Track extreme angles
                if angle < leftmost_angle:
                    leftmost_angle = angle
                    leftmost_vertices = [vertex]
                elif abs(angle - leftmost_angle) < 0.001:  # Within tolerance
                    leftmost_vertices.append(vertex)
                    
                if angle > rightmost_angle:
                    rightmost_angle = angle
                    rightmost_vertices = [vertex]
                elif abs(angle - rightmost_angle) < 0.001:  # Within tolerance
                    rightmost_vertices.append(vertex)
        
        self.log(f"Found text boundaries: left={math.degrees(leftmost_angle):.2f}°, right={math.degrees(rightmost_angle):.2f}°")
        
        # Create wedge at both text start and end
        wedge_angle = math.radians(2)  # Size of the wedge
        
        for side, text_angle, boundary_vertices in [
            ("start", leftmost_angle, leftmost_vertices), 
            ("end", rightmost_angle, rightmost_vertices)
        ]:
            mesh = bpy.data.meshes.new(name=f"Wedge_{side}")
            wedge_obj = bpy.data.objects.new(f"Wedge_{side}", mesh)
            bpy.context.collection.objects.link(wedge_obj)
            
            # Create bmesh for easier geometry creation
            bm = bmesh.new()
            
            # Define the wedge boundaries
            if side == "start":
                # Start wedge connects ring to text start
                angle1 = text_angle - wedge_angle  # Ring side
                angle2 = text_angle  # Text side (actual text boundary)
            else:
                # End wedge connects text end to ring
                angle1 = text_angle  # Text side (actual text boundary)
                angle2 = text_angle + wedge_angle  # Ring side
            
            # Analyze boundary vertices to find the exact radial positions
            boundary_radii = []
            boundary_z_positions = []
            for v in boundary_vertices:
                r = math.sqrt(v.co.x**2 + v.co.y**2)
                boundary_radii.append(r)
                boundary_z_positions.append(v.co.z)
            
            # Get min and max radii and z positions from actual text
            if boundary_radii:
                text_inner_r = min(boundary_radii)
                text_outer_r = max(boundary_radii)
                text_min_z = min(boundary_z_positions)
                text_max_z = max(boundary_z_positions)
            else:
                # Fallback to theoretical values
                text_inner_r = outer_radius
                text_outer_r = outer_radius + text_depth
                text_min_z = -length/2
                text_max_z = length/2
            
            self.log(f"Wedge {side}: text radii {text_inner_r:.2f}-{text_outer_r:.2f}mm, z range {text_min_z:.2f}-{text_max_z:.2f}mm")
            
            # Create vertices for the wedge
            vertices_grid = {}
            
            # Create vertices at multiple z-levels to match text height
            z_levels = 5  # More levels for better connection
            for z_idx in range(z_levels):
                z_coord = text_min_z + (text_max_z - text_min_z) * z_idx / (z_levels - 1)
                
                for angle_idx, angle in enumerate([angle1, angle2]):
                    # Ring side vertices (angle1 for start, angle2 for end)
                    if (side == "start" and angle_idx == 0) or (side == "end" and angle_idx == 1):
                        # Ring side: create vertices at ring radii
                        for r_idx, radius in enumerate([inner_radius, outer_radius]):
                            x = radius * math.sin(angle)
                            y = radius * math.cos(angle)
                            vert = bm.verts.new((x, y, z_coord))
                            vertices_grid[(z_idx, angle_idx, r_idx)] = vert
                    else:
                        # Text side: create vertices matching text boundary
                        # Use actual text radii
                        radii = [text_inner_r, text_outer_r]
                        for r_idx, radius in enumerate(radii):
                            x = radius * math.sin(angle)
                            y = radius * math.cos(angle)
                            vert = bm.verts.new((x, y, z_coord))
                            vertices_grid[(z_idx, angle_idx, r_idx + 10)] = vert  # Offset index for text side
            
            bm.verts.ensure_lookup_table()
            
            # Create faces to connect the vertices
            for z_idx in range(z_levels - 1):
                # Connect ring side to text side
                if side == "start":
                    # For start wedge: angle1 is ring side, angle2 is text side
                    # Inner surface
                    if all((z_idx + dz, 0, 0) in vertices_grid and (z_idx + dz, 1, 10) in vertices_grid 
                        for dz in [0, 1]):
                        bm.faces.new([
                            vertices_grid[(z_idx, 0, 0)],
                            vertices_grid[(z_idx, 1, 10)],
                            vertices_grid[(z_idx + 1, 1, 10)],
                            vertices_grid[(z_idx + 1, 0, 0)]
                        ])
                    
                    # Outer surface
                    if all((z_idx + dz, 0, 1) in vertices_grid and (z_idx + dz, 1, 11) in vertices_grid 
                        for dz in [0, 1]):
                        bm.faces.new([
                            vertices_grid[(z_idx, 0, 1)],
                            vertices_grid[(z_idx + 1, 0, 1)],
                            vertices_grid[(z_idx + 1, 1, 11)],
                            vertices_grid[(z_idx, 1, 11)]
                        ])
                    
                    # Ring side face
                    if all((z_idx + dz, 0, r) in vertices_grid for dz in [0, 1] for r in [0, 1]):
                        bm.faces.new([
                            vertices_grid[(z_idx, 0, 0)],
                            vertices_grid[(z_idx + 1, 0, 0)],
                            vertices_grid[(z_idx + 1, 0, 1)],
                            vertices_grid[(z_idx, 0, 1)]
                        ])
                    
                    # Text side face
                    if all((z_idx + dz, 1, r + 10) in vertices_grid for dz in [0, 1] for r in [0, 1]):
                        bm.faces.new([
                            vertices_grid[(z_idx, 1, 10)],
                            vertices_grid[(z_idx, 1, 11)],
                            vertices_grid[(z_idx + 1, 1, 11)],
                            vertices_grid[(z_idx + 1, 1, 10)]
                        ])
                
                else:  # end wedge
                    # For end wedge: angle1 is text side, angle2 is ring side
                    # Inner surface
                    if all((z_idx + dz, 0, 10) in vertices_grid and (z_idx + dz, 1, 0) in vertices_grid 
                        for dz in [0, 1]):
                        bm.faces.new([
                            vertices_grid[(z_idx, 0, 10)],
                            vertices_grid[(z_idx + 1, 0, 10)],
                            vertices_grid[(z_idx + 1, 1, 0)],
                            vertices_grid[(z_idx, 1, 0)]
                        ])
                    
                    # Outer surface
                    if all((z_idx + dz, 0, 11) in vertices_grid and (z_idx + dz, 1, 1) in vertices_grid 
                        for dz in [0, 1]):
                        bm.faces.new([
                            vertices_grid[(z_idx, 0, 11)],
                            vertices_grid[(z_idx, 1, 1)],
                            vertices_grid[(z_idx + 1, 1, 1)],
                            vertices_grid[(z_idx + 1, 0, 11)]
                        ])
                    
                    # Text side face
                    if all((z_idx + dz, 0, r + 10) in vertices_grid for dz in [0, 1] for r in [0, 1]):
                        bm.faces.new([
                            vertices_grid[(z_idx, 0, 10)],
                            vertices_grid[(z_idx, 0, 11)],
                            vertices_grid[(z_idx + 1, 0, 11)],
                            vertices_grid[(z_idx + 1, 0, 10)]
                        ])
                    
                    # Ring side face
                    if all((z_idx + dz, 1, r) in vertices_grid for dz in [0, 1] for r in [0, 1]):
                        bm.faces.new([
                            vertices_grid[(z_idx, 1, 0)],
                            vertices_grid[(z_idx + 1, 1, 0)],
                            vertices_grid[(z_idx + 1, 1, 1)],
                            vertices_grid[(z_idx, 1, 1)]
                        ])
            
            # Top and bottom caps
            # Bottom cap
            z_idx = 0
            if side == "start":
                if all((z_idx, a, 0) in vertices_grid for a in [0, 1]) and \
                all((z_idx, a, 1) in vertices_grid for a in [0]) and \
                all((z_idx, a, 10) in vertices_grid for a in [1]) and \
                all((z_idx, a, 11) in vertices_grid for a in [1]):
                    bm.faces.new([
                        vertices_grid[(z_idx, 0, 0)],
                        vertices_grid[(z_idx, 0, 1)],
                        vertices_grid[(z_idx, 1, 11)],
                        vertices_grid[(z_idx, 1, 10)]
                    ])
            else:
                if all((z_idx, a, 0) in vertices_grid for a in [1]) and \
                all((z_idx, a, 1) in vertices_grid for a in [1]) and \
                all((z_idx, a, 10) in vertices_grid for a in [0]) and \
                all((z_idx, a, 11) in vertices_grid for a in [0]):
                    bm.faces.new([
                        vertices_grid[(z_idx, 0, 10)],
                        vertices_grid[(z_idx, 0, 11)],
                        vertices_grid[(z_idx, 1, 1)],
                        vertices_grid[(z_idx, 1, 0)]
                    ])
            
            # Top cap
            z_idx = z_levels - 1
            if side == "start":
                if all((z_idx, a, 0) in vertices_grid for a in [0, 1]) and \
                all((z_idx, a, 1) in vertices_grid for a in [0]) and \
                all((z_idx, a, 10) in vertices_grid for a in [1]) and \
                all((z_idx, a, 11) in vertices_grid for a in [1]):
                    bm.faces.new([
                        vertices_grid[(z_idx, 0, 0)],
                        vertices_grid[(z_idx, 1, 10)],
                        vertices_grid[(z_idx, 1, 11)],
                        vertices_grid[(z_idx, 0, 1)]
                    ])
            else:
                if all((z_idx, a, 0) in vertices_grid for a in [1]) and \
                all((z_idx, a, 1) in vertices_grid for a in [1]) and \
                all((z_idx, a, 10) in vertices_grid for a in [0]) and \
                all((z_idx, a, 11) in vertices_grid for a in [0]):
                    bm.faces.new([
                        vertices_grid[(z_idx, 0, 10)],
                        vertices_grid[(z_idx, 1, 0)],
                        vertices_grid[(z_idx, 1, 1)],
                        vertices_grid[(z_idx, 0, 11)]
                    ])
            
            # Update mesh
            bm.to_mesh(mesh)
            bm.free()
            
            # Apply smooth shading
            wedge_obj.select_set(True)
            bpy.context.view_layer.objects.active = wedge_obj
            bpy.ops.object.shade_smooth()
            
            wedges.append(wedge_obj)
            
            self.log(f"Created transition wedge at {side} (angle: {math.degrees(text_angle):.2f}°)")
        
        return wedges

    def write_json_report(self, volume_mm3, volume_cm3, weight_g):
        """Write JSON report with volume and weight data"""
        if '_resolved_report_path' not in self.config['output']:
            return  # No report file specified
        
        report_path = self.config['output']['_resolved_report_path']
        
        try:
            # Prepare report data
            report = {
                "timestamp": datetime.now().isoformat(),
                "config_file": str(self.config_path),
                "ring_parameters": {
                    "inner_diameter": self.config['ring']['inner_diameter'],
                    "outer_diameter": self.config['ring']['outer_diameter'],
                    "length": self.config['ring']['length'],
                    "radial_segments": self.config['ring']['radial_segments'],
                    "vertical_segments": self.config['ring']['vertical_segments']
                },
                "text_parameters": {
                    "content": self.config['text']['content'],
                    "font_size": self.config['text']['font_size'],
                    "depth": self.config['text']['depth'],
                    "direction": self.config['text']['direction']
                },
                "material": {
                    "name": self.config['material']['name'],
                    "density": self.config['material']['density']
                },
                "results": {
                    "volume_mm3": round(volume_mm3, 2),
                    "volume_cm3": round(volume_cm3, 3),
                    "weight_g": round(weight_g, 2),
                    "stl_file": self.config['output']['_resolved_output_path']
                }
            }
            
            # Add text arc information
            if self.text_start_angle is not None and self.text_end_angle is not None:
                report["text_arc"] = {
                    "start_angle_deg": round(math.degrees(self.text_start_angle), 2),
                    "end_angle_deg": round(math.degrees(self.text_end_angle), 2),
                    "span_deg": round(math.degrees(self.text_end_angle - self.text_start_angle), 2)
                }
            
            # Write JSON report
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.log(f"Written JSON report to: {report_path}")
            
        except Exception as e:
            self.log(f"ERROR: Failed to write JSON report: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
    
    def export_stl(self, obj):
        """Export the final mesh as STL"""
        output_path = self.config['output']['_resolved_output_path']
        
        # Calculate volume before export
        self.log("Calculating mesh volume...")
        volume_mm3, volume_cm3 = self.calculate_mesh_volume(obj)
        
        if volume_mm3 is not None:
            # Get material properties
            material_name = self.config['material']['name']
            material_density = self.config['material']['density']  # g/cm³
            
            # Calculate weight
            weight_g = volume_cm3 * material_density
            
            self.log(f"Mesh volume: {volume_mm3:.2f} mm³ ({volume_cm3:.3f} cm³)")
            self.log(f"Material: {material_name} (density: {material_density} g/cm³)")
            self.log(f"Estimated weight: {weight_g:.2f} g")
            
            # Write JSON report if configured
            self.write_json_report(volume_mm3, volume_cm3, weight_g)
        else:
            self.log("WARNING: Could not calculate mesh volume", "WARNING")
            weight_g = None
        
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
                    self.log(f"  Weight: {weight_g:.2f} g ({material_name})")
                if '_resolved_report_path' in self.config['output']:
                    self.log(f"  Report file: {self.config['output']['_resolved_report_path']}")
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

            # Create text and calculate its arc
            self.log("Creating text geometry and calculating arc...")
            text_obj = self.create_text_and_calculate_arc()
            if not text_obj:
                self.log("ERROR: Failed to create text", "ERROR")
                return 4  # Font rendering error

            # Create partial ring based on text arc
            self.log("Creating partial ring geometry...")
            ring_obj = self.create_partial_ring(self.text_start_angle, self.text_end_angle)
            if not ring_obj:
                self.log("ERROR: Failed to create ring", "ERROR")
                return 3  # Blender operation error

            # Create transition wedges
            self.log("Creating transition wedges...")
            wedge_objs = self.create_transition_wedges()
            if not wedge_objs:
                self.log("WARNING: Failed to create transition wedges", "WARNING")
                # Continue without wedges
                wedge_objs = []

            # Combine everything
            self.log("Combining all geometry...")
            if wedge_objs:
                # Use the new method that includes wedges
                final_obj = self.combine_ring_and_text_with_wedges(ring_obj, text_obj, wedge_objs)
            else:
                # Fall back to original method
                final_obj = self.combine_ring_and_text(ring_obj, text_obj)
            
            if not final_obj:
                self.log("ERROR: Failed to combine geometry", "ERROR")
                self.cleanup_on_error()
                return 3  # Blender operation error

            # Export as STL
            if not self.export_stl(final_obj):
                self.cleanup_on_error()
                return 2  # File I/O error

            self.log("Ring generation completed successfully!")
            return 0  # Success

        except Exception as e:
            self.log(f"ERROR: Unexpected error: {e}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            self.cleanup_on_error()
            return 3  # Blender operation error

        finally:
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
