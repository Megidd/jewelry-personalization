import bpy
import bmesh
import numpy as np
from mathutils import Vector
import os
import sys
import json
from enum import Enum
from pathlib import Path

class PrintingType(Enum):
    FDM = "FDM"
    SLA = "SLA"
    GENERAL = "GENERAL"

class MeshRepairOpenVDB:
    """
    Advanced mesh repair using OpenVDB voxelization in Blender.
    Fixes topology issues, non-manifold geometry, holes, and self-intersections.
    """
    
    def __init__(self, input_stl_path, output_stl_path):
        self.input_path = input_stl_path
        self.output_path = output_stl_path
        self.original_mesh = None
        self.repaired_mesh = None
        
    def clear_scene(self):
        """Clear all mesh objects from the scene"""
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        # Clear orphan data
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
            
    def import_stl(self):
        """Import STL file with version compatibility"""
        print(f"Importing STL from: {self.input_path}")
        print(f"Blender version: {bpy.app.version_string}")
        
        # Check if file exists
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input STL file not found: {self.input_path}")
        
        # Store initial object count
        initial_objects = set(bpy.data.objects)
        
        # Try different import methods based on Blender version
        try:
            # For Blender 4.0+
            if hasattr(bpy.ops.wm, 'stl_import'):
                bpy.ops.wm.stl_import(filepath=self.input_path)
            # For Blender 3.x
            elif hasattr(bpy.ops.import_mesh, 'stl'):
                bpy.ops.import_mesh.stl(filepath=self.input_path)
            # For Blender 4.x alternative method
            elif hasattr(bpy.ops, 'import_mesh') and hasattr(bpy.ops.import_mesh, 'stl'):
                bpy.ops.import_mesh.stl(filepath=self.input_path)
            else:
                # Fallback: Try to use the new API
                bpy.ops.wm.stl_import(filepath=self.input_path)
        except AttributeError as e:
            print(f"Failed with standard import operators: {e}")
            print("Attempting alternative import method...")
            
            # Alternative method: manually construct the operator call
            try:
                # This works in Blender 4.0+
                bpy.ops.wm.stl_import(filepath=self.input_path)
            except:
                # Last resort: Try old operator
                try:
                    bpy.ops.import_mesh.stl(filepath=self.input_path)
                except:
                    raise Exception(f"Unable to import STL file. Blender version {bpy.app.version_string} may not be supported.")
        
        # Get the newly imported object
        new_objects = set(bpy.data.objects) - initial_objects
        
        if not new_objects:
            raise Exception("Failed to import STL file - no new objects created")
        
        # Get the imported object (should be the only new object)
        self.original_mesh = list(new_objects)[0]
        self.original_mesh.name = "Original_Mesh"
        
        # Make sure it's selected and active
        bpy.context.view_layer.objects.active = self.original_mesh
        self.original_mesh.select_set(True)
        
        print(f"Successfully imported: {self.original_mesh.name}")
        return self.original_mesh
    
    def analyze_mesh(self, obj):
        """Analyze mesh to determine optimal parameters"""
        mesh = obj.data
        
        # Calculate bounding box diagonal
        bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        bbox_min = Vector((min(c.x for c in bbox_corners),
                          min(c.y for c in bbox_corners),
                          min(c.z for c in bbox_corners)))
        bbox_max = Vector((max(c.x for c in bbox_corners),
                          max(c.y for c in bbox_corners),
                          max(c.z for c in bbox_corners)))
        bbox_diagonal = (bbox_max - bbox_min).length
        
        # Calculate mesh statistics
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        # Find minimum edge length for detail preservation
        min_edge_length = float('inf')
        avg_edge_length = 0
        edge_count = 0
        
        for edge in bm.edges:
            length = edge.calc_length()
            if length > 0:  # Avoid zero-length edges
                min_edge_length = min(min_edge_length, length)
            avg_edge_length += length
            edge_count += 1
            
        if min_edge_length == float('inf'):
            min_edge_length = bbox_diagonal * 0.001
            
        avg_edge_length = avg_edge_length / edge_count if edge_count > 0 else bbox_diagonal * 0.01
        
        # Detect non-manifold edges
        non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
        non_manifold_count = len(non_manifold_edges)
        
        # Detect holes (boundary edges)
        boundary_edges = [e for e in bm.edges if e.is_boundary]
        hole_count = len(boundary_edges)
        
        bm.free()
        
        print(f"Mesh Analysis:")
        print(f"  - Vertices: {len(mesh.vertices)}")
        print(f"  - Faces: {len(mesh.polygons)}")
        print(f"  - Bounding Box Diagonal: {bbox_diagonal:.3f}")
        print(f"  - Min Edge Length: {min_edge_length:.3f}")
        print(f"  - Avg Edge Length: {avg_edge_length:.3f}")
        print(f"  - Non-manifold Edges: {non_manifold_count}")
        print(f"  - Boundary Edges (holes): {hole_count}")
        
        return {
            'bbox_diagonal': bbox_diagonal,
            'min_edge_length': min_edge_length,
            'avg_edge_length': avg_edge_length,
            'non_manifold_count': non_manifold_count,
            'hole_count': hole_count,
            'vertex_count': len(mesh.vertices),
            'face_count': len(mesh.polygons)
        }
    
    def calculate_voxel_size(self, mesh_stats, printing_type=PrintingType.GENERAL, 
                           nozzle_diameter=0.4, layer_height=0.1, custom_voxel_size=None):
        """
        Calculate optimal voxel size based on mesh statistics and printing parameters
        """
        # If custom voxel size is specified, use it
        if custom_voxel_size is not None and custom_voxel_size > 0:
            print(f"Using custom voxel size: {custom_voxel_size:.4f}")
            return custom_voxel_size
        
        bbox_diagonal = mesh_stats['bbox_diagonal']
        min_edge_length = mesh_stats['min_edge_length']
        
        if printing_type == PrintingType.FDM:
            # For FDM: voxel size = 0.5-1.0 × nozzle diameter
            voxel_size = nozzle_diameter * 0.75
            
        elif printing_type == PrintingType.SLA:
            # For SLA/DLP: voxel size = 2-4 × layer height
            voxel_size = layer_height * 3.0
            
        else:  # GENERAL
            # Adaptive calculation based on mesh complexity
            base_voxel_size = bbox_diagonal * 0.002  # 0.2% of diagonal
            
            # Adjust based on mesh detail
            if min_edge_length < base_voxel_size * 2:
                # Fine details present, use smaller voxels
                voxel_size = min_edge_length * 0.5
            else:
                voxel_size = base_voxel_size
            
            # Adjust based on damage level
            damage_score = (mesh_stats['non_manifold_count'] + mesh_stats['hole_count']) / max(mesh_stats['edge_count'], 1)
            if damage_score > 0.1:  # Heavily damaged
                # Use larger voxels for more aggressive repair
                voxel_size *= 1.5
        
        # Clamp voxel size to reasonable range
        min_voxel = bbox_diagonal * 0.0001  # 0.01% minimum
        max_voxel = bbox_diagonal * 0.01    # 1% maximum
        voxel_size = max(min_voxel, min(max_voxel, voxel_size))
        
        print(f"Calculated Voxel Size: {voxel_size:.4f}")
        
        return voxel_size
    
    def pre_process_mesh(self, obj):
        """Pre-process mesh to remove obvious defects"""
        print("Pre-processing mesh...")
        
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        
        # Enter edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Select all
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Remove doubles/duplicate vertices
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        
        # Delete loose vertices and edges
        bpy.ops.mesh.delete_loose()
        
        # Fix normals
        bpy.ops.mesh.normals_make_consistent(inside=False)
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        print("Pre-processing complete")
    
    def apply_voxel_remesh(self, obj, voxel_size, apply_closing=True, smooth_iterations=1):
        """
        Apply OpenVDB voxel remeshing using Blender's Remesh modifier
        """
        print(f"Applying voxel remesh with size: {voxel_size:.4f}")
        
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        
        # Add Remesh modifier (uses OpenVDB internally in VOXEL mode)
        remesh_modifier = obj.modifiers.new(name="OpenVDB_Remesh", type='REMESH')
        remesh_modifier.mode = 'VOXEL'
        remesh_modifier.voxel_size = voxel_size
        remesh_modifier.adaptivity = 0.0  # 0 for uniform, increase for adaptive
        remesh_modifier.use_smooth_shade = False
        
        # Apply the modifier
        bpy.ops.object.modifier_apply(modifier=remesh_modifier.name)
        
        if apply_closing:
            # Morphological closing operation using Smooth and Corrective Smooth
            self.apply_morphological_closing(obj, voxel_size)
        
        if smooth_iterations > 0:
            # Apply smoothing to reduce voxel artifacts
            self.apply_smoothing(obj, smooth_iterations, voxel_size)
        
        print("Voxel remesh complete")
    
    def apply_morphological_closing(self, obj, voxel_size):
        """
        Simulate morphological closing (dilation followed by erosion) to fill small holes
        """
        print("Applying morphological closing...")
        
        # Dilation using Displace modifier
        displace_mod = obj.modifiers.new(name="Dilate", type='DISPLACE')
        displace_mod.strength = voxel_size * 0.5
        displace_mod.mid_level = 0.0
        bpy.ops.object.modifier_apply(modifier=displace_mod.name)
        
        # Quick remesh to clean up
        remesh_mod = obj.modifiers.new(name="Clean_Dilate", type='REMESH')
        remesh_mod.mode = 'VOXEL'
        remesh_mod.voxel_size = voxel_size
        bpy.ops.object.modifier_apply(modifier=remesh_mod.name)
        
        # Erosion using negative displacement
        displace_mod = obj.modifiers.new(name="Erode", type='DISPLACE')
        displace_mod.strength = -voxel_size * 0.5
        displace_mod.mid_level = 0.0
        bpy.ops.object.modifier_apply(modifier=displace_mod.name)
    
    def apply_smoothing(self, obj, iterations, voxel_size):
        """Apply smoothing to reduce voxelization artifacts"""
        print(f"Applying smoothing ({iterations} iterations)...")
        
        smooth_mod = obj.modifiers.new(name="Smooth", type='SMOOTH')
        smooth_mod.iterations = iterations
        smooth_mod.factor = 0.5
        bpy.ops.object.modifier_apply(modifier=smooth_mod.name)
    
    def apply_feature_preservation(self, obj, mesh_stats):
        """
        Post-process to preserve/enhance features
        """
        print("Applying feature preservation...")
        
        # Use Weighted Normal modifier to improve shading
        weighted_normal_mod = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
        weighted_normal_mod.weight = 50
        weighted_normal_mod.keep_sharp = True
        bpy.ops.object.modifier_apply(modifier=weighted_normal_mod.name)
        
        # Decimate with planar mode to simplify flat areas while preserving features
        if mesh_stats['face_count'] > 100000:
            decimate_mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
            decimate_mod.decimate_type = 'DISSOLVE'
            decimate_mod.angle_limit = np.radians(5)  # 5 degrees
            bpy.ops.object.modifier_apply(modifier=decimate_mod.name)
    
    def multi_resolution_repair(self, obj, mesh_stats):
        """
        Apply multi-resolution repair strategy
        """
        print("Starting multi-resolution repair...")
        
        # First pass: Coarse voxelization for major topology fixes
        coarse_voxel_size = mesh_stats['bbox_diagonal'] * 0.005
        print(f"Pass 1: Coarse repair (voxel size: {coarse_voxel_size:.4f})")
        
        # Duplicate object for coarse pass
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.duplicate()
        coarse_obj = bpy.context.active_object
        coarse_obj.name = "Coarse_Repair"
        
        self.apply_voxel_remesh(coarse_obj, coarse_voxel_size, apply_closing=True, smooth_iterations=0)
        
        # Second pass: Fine voxelization for detail preservation
        fine_voxel_size = mesh_stats['bbox_diagonal'] * 0.001
        print(f"Pass 2: Fine repair (voxel size: {fine_voxel_size:.4f})")
        
        self.apply_voxel_remesh(coarse_obj, fine_voxel_size, apply_closing=False, smooth_iterations=2)
        
        # Delete original and rename
        bpy.data.objects.remove(obj, do_unlink=True)
        coarse_obj.name = "Repaired_Mesh"
        
        return coarse_obj
    
    def validate_repair(self, obj):
        """Validate the repaired mesh"""
        print("Validating repaired mesh...")
        
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        # Check for non-manifold geometry
        non_manifold = [e for e in bm.edges if not e.is_manifold]
        
        # Check for boundaries (holes)
        boundaries = [e for e in bm.edges if e.is_boundary]
        
        bm.free()
        
        is_valid = len(non_manifold) == 0 and len(boundaries) == 0
        
        print(f"Validation Results:")
        print(f"  - Is Watertight: {len(boundaries) == 0}")
        print(f"  - Is Manifold: {len(non_manifold) == 0}")
        print(f"  - Overall Valid: {is_valid}")
        
        return is_valid
    
    def export_stl(self, obj):
        """Export the repaired mesh as STL with version compatibility"""
        print(f"Exporting repaired mesh to: {self.output_path}")
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(self.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Select only the repaired object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Try different export methods based on Blender version
        try:
            # For Blender 4.0+
            if hasattr(bpy.ops.wm, 'stl_export'):
                bpy.ops.wm.stl_export(
                    filepath=self.output_path,
                    export_selected_objects=True,
                    ascii_format=False  # Binary STL for smaller file size
                )
            # For Blender 3.x and earlier
            elif hasattr(bpy.ops.export_mesh, 'stl'):
                bpy.ops.export_mesh.stl(
                    filepath=self.output_path,
                    use_selection=True,
                    ascii=False  # Binary STL for smaller file size
                )
            else:
                # Fallback attempt
                bpy.ops.wm.stl_export(
                    filepath=self.output_path,
                    export_selected_objects=True,
                    ascii_format=False
                )
        except AttributeError as e:
            print(f"Failed with standard export operators: {e}")
            print("Attempting alternative export method...")
            
            # Alternative: Try the new API
            try:
                bpy.ops.wm.stl_export(
                    filepath=self.output_path,
                    export_selected_objects=True,
                    ascii_format=False
                )
            except:
                # Last resort: Try old operator
                try:
                    bpy.ops.export_mesh.stl(
                        filepath=self.output_path,
                        use_selection=True,
                        ascii=False
                    )
                except:
                    raise Exception(f"Unable to export STL file. Blender version {bpy.app.version_string} may not be supported.")
        
        print("Export complete")
    
    def repair(self, printing_type=PrintingType.GENERAL, 
               nozzle_diameter=0.4, layer_height=0.1,
               use_multi_resolution=False, preserve_features=True,
               custom_voxel_size=None, pre_process=True,
               apply_closing=True, smooth_iterations=2):
        """
        Main repair function with additional parameters
        """
        print("="*50)
        print("Starting OpenVDB Mesh Repair Process")
        print("="*50)
        
        try:
            # Clear scene
            self.clear_scene()
            
            # Import STL
            self.import_stl()
            
            # Analyze mesh
            mesh_stats = self.analyze_mesh(self.original_mesh)
            mesh_stats['edge_count'] = len(self.original_mesh.data.edges)
            
            # Pre-process
            if pre_process:
                self.pre_process_mesh(self.original_mesh)
            
            # Calculate optimal voxel size
            voxel_size = self.calculate_voxel_size(
                mesh_stats, 
                printing_type, 
                nozzle_diameter, 
                layer_height,
                custom_voxel_size
            )
            
            # Apply repair strategy
            if use_multi_resolution and mesh_stats['non_manifold_count'] > 100:
                self.repaired_mesh = self.multi_resolution_repair(self.original_mesh, mesh_stats)
            else:
                # Single resolution repair
                self.apply_voxel_remesh(
                    self.original_mesh, 
                    voxel_size,
                    apply_closing=apply_closing or (mesh_stats['hole_count'] > 0),
                    smooth_iterations=smooth_iterations if preserve_features else 0
                )
                self.repaired_mesh = self.original_mesh
            
            # Post-process for feature preservation
            if preserve_features:
                self.apply_feature_preservation(self.repaired_mesh, mesh_stats)
            
            # Validate repair
            is_valid = self.validate_repair(self.repaired_mesh)
            
            if not is_valid:
                print("Warning: Mesh may still have issues. Applying additional repair pass...")
                # Apply more aggressive repair
                aggressive_voxel_size = voxel_size * 2
                self.apply_voxel_remesh(self.repaired_mesh, aggressive_voxel_size, True, 3)
                self.validate_repair(self.repaired_mesh)
            
            # Export result
            self.export_stl(self.repaired_mesh)
            
            # Final statistics
            print("" + "="*50)
            print("Repair Complete!")
            print(f"Original faces: {mesh_stats['face_count']}")
            print(f"Repaired faces: {len(self.repaired_mesh.data.polygons)}")
            print(f"Output saved to: {self.output_path}")
            print("="*50)
            
            return True
            
        except Exception as e:
            print(f"Error during repair: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def load_config(config_path):
    """
    Load configuration from JSON file
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"Configuration loaded from: {config_path}")
        print(f"Config: {json.dumps(config, indent=2)}")
        
        return config
    
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)


def validate_config(config):
    """
    Validate configuration and set defaults for missing values
    """
    # Required fields
    if 'input_stl' not in config:
        raise ValueError("Missing required field: 'input_stl'")
    if 'output_stl' not in config:
        raise ValueError("Missing required field: 'output_stl'")
    
    # Optional fields with defaults
    defaults = {
        'printing_type': 'GENERAL',
        'nozzle_diameter': 0.4,
        'layer_height': 0.1,
        'use_multi_resolution': False,
        'preserve_features': True,
        'voxel_size': None,  # None means auto-calculate
        'pre_process': True,
        'apply_closing': True,
        'smooth_iterations': 2
    }
    
    # Apply defaults for missing fields
    for key, default_value in defaults.items():
        if key not in config:
            config[key] = default_value
            print(f"Using default value for '{key}': {default_value}")
    
    # Validate printing_type
    valid_types = ['FDM', 'SLA', 'GENERAL']
    if config['printing_type'].upper() not in valid_types:
        print(f"Warning: Invalid printing_type '{config['printing_type']}'. Using 'GENERAL'")
        config['printing_type'] = 'GENERAL'
    
    return config


def main():
    """
    Main entry point for command-line execution
    """
    print("="*50)
    print("OpenVDB Mesh Repair Tool")
    print(f"Blender Version: {bpy.app.version_string}")
    print("="*50)
    
    # Parse command line arguments
    argv = sys.argv
    
    # Find the "--" separator
    try:
        separator_index = argv.index("--")
        script_args = argv[separator_index + 1:]
    except ValueError:
        print("Error: No configuration file specified")
        print("Usage: blender --background --python repair.py -- config.json")
        sys.exit(1)
    
    if len(script_args) < 1:
        print("Error: No configuration file specified")
        print("Usage: blender --background --python repair.py -- config.json")
        sys.exit(1)
    
    config_path = script_args[0]
    
    # Make path absolute if relative
    if not os.path.isabs(config_path):
        config_path = os.path.abspath(config_path)
    
    # Load configuration
    config = load_config(config_path)
    
    # Validate and apply defaults
    config = validate_config(config)
    
    # Make paths absolute if they're relative
    if not os.path.isabs(config['input_stl']):
        # If relative, make it relative to the config file's directory
        config_dir = os.path.dirname(config_path)
        config['input_stl'] = os.path.abspath(os.path.join(config_dir, config['input_stl']))
    
    if not os.path.isabs(config['output_stl']):
        config_dir = os.path.dirname(config_path)
        config['output_stl'] = os.path.abspath(os.path.join(config_dir, config['output_stl']))
    
    # Map string to enum for printing type
    printing_type_map = {
        "FDM": PrintingType.FDM,
        "SLA": PrintingType.SLA,
        "GENERAL": PrintingType.GENERAL
    }
    printing_type_enum = printing_type_map.get(config['printing_type'].upper(), PrintingType.GENERAL)
    
    # Create repair instance
    repairer = MeshRepairOpenVDB(config['input_stl'], config['output_stl'])
    
    # Execute repair with all parameters
    success = repairer.repair(
        printing_type=printing_type_enum,
        nozzle_diameter=config['nozzle_diameter'],
        layer_height=config['layer_height'],
        use_multi_resolution=config['use_multi_resolution'],
        preserve_features=config['preserve_features'],
        custom_voxel_size=config['voxel_size'],
        pre_process=config['pre_process'],
        apply_closing=config['apply_closing'],
        smooth_iterations=config['smooth_iterations']
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
