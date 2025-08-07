import bpy
import bmesh
import numpy as np
from mathutils import Vector
import os
from enum import Enum

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
        """Import STL file"""
        print(f"Importing STL from: {self.input_path}")
        
        # Import the STL file
        bpy.ops.import_mesh.stl(filepath=self.input_path)
        
        # Get the imported object (should be the active object)
        self.original_mesh = bpy.context.active_object
        
        if self.original_mesh is None:
            raise Exception("Failed to import STL file")
            
        self.original_mesh.name = "Original_Mesh"
        
        # Make sure it's selected and active
        bpy.context.view_layer.objects.active = self.original_mesh
        self.original_mesh.select_set(True)
        
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
            min_edge_length = min(min_edge_length, length)
            avg_edge_length += length
            edge_count += 1
            
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
                           nozzle_diameter=0.4, layer_height=0.1):
        """
        Calculate optimal voxel size based on mesh statistics and printing parameters
        """
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
        """Export the repaired mesh as STL"""
        print(f"Exporting repaired mesh to: {self.output_path}")
        
        # Select only the repaired object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Export as STL
        bpy.ops.export_mesh.stl(
            filepath=self.output_path,
            use_selection=True,
            ascii=False  # Binary STL for smaller file size
        )
        
        print("Export complete")
    
    def repair(self, printing_type=PrintingType.GENERAL, 
               nozzle_diameter=0.4, layer_height=0.1,
               use_multi_resolution=False, preserve_features=True):
        """
        Main repair function
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
            self.pre_process_mesh(self.original_mesh)
            
            # Calculate optimal voxel size
            voxel_size = self.calculate_voxel_size(
                mesh_stats, 
                printing_type, 
                nozzle_diameter, 
                layer_height
            )
            
            # Apply repair strategy
            if use_multi_resolution and mesh_stats['non_manifold_count'] > 100:
                self.repaired_mesh = self.multi_resolution_repair(self.original_mesh, mesh_stats)
            else:
                # Single resolution repair
                self.apply_voxel_remesh(
                    self.original_mesh, 
                    voxel_size,
                    apply_closing=(mesh_stats['hole_count'] > 0),
                    smooth_iterations=2 if preserve_features else 0
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


# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def repair_stl_with_openvdb(input_stl_path, output_stl_path, 
                           printing_type="GENERAL",
                           nozzle_diameter=0.4,
                           layer_height=0.1,
                           use_multi_resolution=False,
                           preserve_features=True):
    """
    Main function to repair an STL file using OpenVDB approach
    
    Args:
        input_stl_path: Path to input STL file
        output_stl_path: Path to save repaired STL file
        printing_type: "FDM", "SLA", or "GENERAL"
        nozzle_diameter: For FDM printing (mm)
        layer_height: For SLA printing (mm)
        use_multi_resolution: Use multi-resolution strategy for complex repairs
        preserve_features: Apply feature preservation post-processing
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Map string to enum
    printing_type_map = {
        "FDM": PrintingType.FDM,
        "SLA": PrintingType.SLA,
        "GENERAL": PrintingType.GENERAL
    }
    
    printing_type_enum = printing_type_map.get(printing_type.upper(), PrintingType.GENERAL)
    
    # Create repair instance
    repairer = MeshRepairOpenVDB(input_stl_path, output_stl_path)
    
    # Execute repair
    success = repairer.repair(
        printing_type=printing_type_enum,
        nozzle_diameter=nozzle_diameter,
        layer_height=layer_height,
        use_multi_resolution=use_multi_resolution,
        preserve_features=preserve_features
    )
    
    return success


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example usage - modify these paths for your files
    INPUT_STL = "/path/to/your/broken_model.stl"
    OUTPUT_STL = "/path/to/your/repaired_model.stl"
    
    # For FDM printing with 0.4mm nozzle
    success = repair_stl_with_openvdb(
        input_stl_path=INPUT_STL,
        output_stl_path=OUTPUT_STL,
        printing_type="FDM",
        nozzle_diameter=0.4,
        use_multi_resolution=True,
        preserve_features=True
    )
    
    # For SLA printing with 0.05mm layer height
    # success = repair_stl_with_openvdb(
    #     input_stl_path=INPUT_STL,
    #     output_stl_path=OUTPUT_STL,
    #     printing_type="SLA",
    #     layer_height=0.05,
    #     use_multi_resolution=False,
    #     preserve_features=True
    # )
    
    # For general repair with automatic parameters
    # success = repair_stl_with_openvdb(
    #     input_stl_path=INPUT_STL,
    #     output_stl_path=OUTPUT_STL,
    #     printing_type="GENERAL",
    #     use_multi_resolution=True,
    #     preserve_features=True
    # )
