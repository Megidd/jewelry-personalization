# Ring Generator with 3D Text - Technical Specifications

## 1. Overview

A Python script (`script.py`) using Blender Python API to generate a customizable ring with 3D text embossed or carved on its surface.

## 2. Execution

### 2.1 Command Line
```bash
blender --background --python script.py -- config.json
```
- Runs on Linux server without GUI
- Accepts JSON configuration file as argument

### 2.2 File Structure
- `script.py` - Main Python script
- `config.json` - Configuration file
- All paths are relative to the directory containing `config.json` (even if config.json is specified with an absolute path)

## 3. Configuration Parameters

### 3.1 Text Parameters
| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `text` | string | Text to be written on ring | UTF-8 encoded, case-sensitive, single-line only |
| `font_path` | string | Path to TTF/OTF font file | Must exist, relative to config directory |
| `text_size` | float | Height of text in mm (Z-axis) | Must be < ring_length |
| `text_depth` | float | Depth of embossing/carving in mm | See section 6.3 for capping behavior |
| `letter_spacing` | float | Additional arc length between letters in mm (beyond font kerning) | >= 0, < ring circumference |
| `embossed` | boolean | Text extends outward from surface | See section 3.4 for logic |
| `carved` | boolean | Text extends inward from surface | See section 3.4 for logic |
| `text_direction` | string | Text orientation | "normal" (readable from outside) or "inverted" (readable from inside) |

### 3.2 Ring Parameters
| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `inner_diameter` | float | Inner diameter in mm | Must be < outer_diameter |
| `outer_diameter` | float | Outer diameter in mm | Must be > inner_diameter |
| `ring_length` | float | Ring height/length in mm | Must be > 0 |
| `radial_segments` | integer | Number of segments around circumference | >= 128, default: 256 |
| `vertical_segments` | integer | Number of segments along Z-axis | >= 32, default: 64 |

### 3.3 Output Parameters
| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `stl_filename` | string | Output STL file path (relative to config dir) | Valid path string |
| `log_filename` | string | Log file path for errors/warnings (relative to config dir) | Valid path string |
| `create_parent_dirs` | boolean | Auto-create output directories if they don't exist | Default: true |

### 3.4 Embossed/Carved Logic
| embossed | carved | Result |
|----------|--------|--------|
| true | false | Text extends outward from surface |
| false | true | Text extends inward from surface |
| false | false | Defaults to embossed=true with warning |
| true | true | Error (exit code 1) |

## 4. Ring Geometry

### 4.1 Shape Specifications
- **Geometry**: Cylinder with configurable radial and vertical segments
- **Ring Thickness**: `(outer_diameter - inner_diameter) / 2`
- **Units**: All measurements in millimeters

### 4.2 Coordinate System
- **Origin**: Ring center at (0, 0, 0)
- **XY Plane**: Ring's circular plane
- **Z-Axis**: Ring extends from Z = -ring_length/2 to Z = +ring_length/2
- **Bottom**: Z = -ring_length/2
- **Top**: Z = +ring_length/2

## 5. Text Positioning

### 5.1 Placement Rules
- **Horizontal Center**: The geometric center of the complete text string is aligned with the intersection of +Y axis and outer circumference
- **Vertical Center**: Text baseline at Z = -text_size/2, top of text at Z = +text_size/2
- **Surface**: Outer surface of ring at outer diameter
- **Curvature**: Text follows ring's circular curvature

### 5.2 Text Wrapping
- Text wraps around circumference if needed
- Maximum wrap: 360 degrees minus a 2mm safety gap (to prevent first/last character overlap)
- If text exceeds available circumference: truncated with warning in log
- Wrapping calculation includes letter_spacing in total text length

### 5.3 Text Rendering
- **Character Encoding**: UTF-8 supported
- **Multi-line**: Newlines ignored (single line only)
- **Missing Characters**: Replaced with '?' if glyph not in font; if '?' also unavailable, character is skipped with warning
- **RTL Languages**: Not supported in current version
- **Font Scaling**: Text height matches text_size; width scales proportionally based on font metrics
- **Maximum Text Length**: 500 characters (for performance)

## 6. Boolean Operations

### 6.1 Embossed Text
- Text extends outward from outer surface by `text_depth`
- Boolean union operation with ring mesh

### 6.2 Carved Text
- Text extends inward from outer surface by `text_depth`
- Boolean difference operation with ring mesh

### 6.3 Depth Capping Behavior
- **If text_depth > ring_thickness**:
  - For embossed: No capping (text extends beyond inner surface)
  - For carved: Capped to 90% of ring thickness to prevent complete punch-through
  - Warning logged in both cases
- **Recommended**: text_depth <= 50% of ring thickness for structural integrity

## 7. Export Specifications

### 7.1 STL Format
- **Format**: Binary STL
- **Units**: Millimeters
- **Mesh**: Single unified mesh (ring + text)
- **API**: `bpy.ops.wm.stl_export` (for Blender 3.3+) or `bpy.ops.export_mesh.stl` (for older versions)

## 8. Error Handling

### 8.1 Exit Codes
| Code | Description | Examples |
|------|-------------|----------|
| 0 | Success | Normal execution |
| 1 | Input validation error | Invalid dimensions, missing required fields, both embossed and carved true |
| 2 | File I/O error | Font file not found, cannot write STL, cannot create directories |
| 3 | Blender operation error | Boolean operation failure, mesh generation error |
| 4 | Font rendering error | Corrupted font file, unsupported font format |

### 8.2 Validation Rules
- **Font File**: Must exist, be readable, and be valid TTF or OTF format
- **Diameters**: inner_diameter < outer_diameter
- **Ring Thickness**: (outer_diameter - inner_diameter) / 2 >= 1.5mm (warning if less)
- **Text Size**: < ring_length (auto-capped to 80% of ring_length with warning if exceeded)
- **Text Depth**: See section 6.3 for capping rules
- **Letter Spacing**: >= 0 and < ring_circumference
- **Text Length**: <= 500 characters
- **Embossed/Carved**: Cannot both be true; if both false, defaults to embossed

### 8.3 Logging
- Console output for immediate feedback
- Log file with ISO 8601 timestamps for all warnings/errors
- Format: `[YYYY-MM-DD HH:MM:SS] [LEVEL] Message`
- Detailed error messages with suggested fixes
- Progress indicators for long operations

### 8.4 Error Recovery
- On boolean operation failure: Attempt fallback with increased mesh resolution
- On partial failure: Clean up temporary files
- On exit: Always close Blender properly to prevent memory leaks

## 9. Default Values and Best Practices

### 9.1 Default Values
| Parameter | Default Value | Rationale |
|-----------|---------------|-----------|
| `radial_segments` | 256 | Smooth surface for wearing |
| `vertical_segments` | 64 | Good vertical resolution |
| `letter_spacing` | 0 | Use font's natural kerning |
| `text_direction` | "normal" | Readable from outside |
| `embossed` | true (if both false) | More common use case |
| `create_parent_dirs` | true | Convenience |

### 9.2 Practical Constraints
- **Minimum Ring Thickness**: 1.5mm (for structural integrity)
- **Maximum Text Depth**: 50% of ring thickness (recommended)
- **Text Size Range**: 20-80% of ring length (for readability)
- **Minimum Inner Diameter**: 10mm (for practical wearability)
- **Maximum Outer Diameter**: 50mm (for practical wearability)

## 10. Example Configuration

```json
{
  "text": "FOREVER",
  "font_path": "./fonts/arial.ttf",
  "text_size": 3.0,
  "text_depth": 0.5,
  "letter_spacing": 0.2,
  "embossed": true,
  "carved": false,
  "text_direction": "normal",
  "inner_diameter": 18.0,
  "outer_diameter": 22.0,
  "ring_length": 6.0,
  "radial_segments": 256,
  "vertical_segments": 64,
  "stl_filename": "output/custom_ring.stl",
  "log_filename": "output/ring_generation.log",
  "create_parent_dirs": true
}
```

## 11. Implementation Notes

### 11.1 Font Handling
- Load font using Blender's font objects
- Validate font file before processing
- Cache font metrics for performance

### 11.2 Mesh Generation Order
1. Create ring cylinder mesh
2. Convert text to 3D mesh with proper depth
3. Position and curve text along ring surface
4. Perform boolean operation
5. Clean up mesh (remove doubles, recalculate normals)
6. Export to STL

### 11.3 Performance Considerations
- Text longer than 100 characters may increase processing time significantly
- Higher segment counts improve quality but increase file size and processing time
- Boolean operations are computationally expensive; provide progress feedback