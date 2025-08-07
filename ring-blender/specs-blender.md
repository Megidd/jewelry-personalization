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
- All paths are relative to the directory containing `config.json`

## 3. Configuration Parameters

### 3.1 Text Parameters
| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `text` | string | Text to be written on ring | Case-sensitive, single-line only |
| `font_path` | string | Path to TTF font file | Must exist, relative to config directory |
| `text_size` | float | Height of text in mm (Z-axis) | Must be < ring_length |
| `text_depth` | float | Depth of embossing/carving in mm | Capped to ring thickness if exceeded |
| `letter_spacing` | float | Arc length between letters in mm | >= 0, < ring circumference |
| `embossed` | boolean | Text extends outward from surface | At least one of embossed/carved must be true |
| `carved` | boolean | Text extends inward from surface | Cannot be true if embossed is true |

### 3.2 Ring Parameters
| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `inner_diameter` | float | Inner diameter in mm | Must be < outer_diameter |
| `outer_diameter` | float | Outer diameter in mm | Must be > inner_diameter |
| `ring_length` | float | Ring height/length in mm | Must be > 0 |

### 3.3 Output Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `stl_filename` | string | Output STL file path |
| `log_filename` | string | Log file path for errors/warnings |

## 4. Ring Geometry

### 4.1 Shape Specifications
- **Geometry**: Cylinder with 256+ radial segments for smoothness
- **Ring Thickness**: `(outer_diameter - inner_diameter) / 2`
- **Units**: All measurements in millimeters

### 4.2 Coordinate System
- **Origin**: Ring center at (0, 0, 0)
- **XY Plane**: Ring's circular plane
- **Z-Axis**: Ring extends ±ring_length/2 from origin

## 5. Text Positioning

### 5.1 Placement Rules
- **Horizontal Center**: Intersection of +Y axis with outer circumference
- **Vertical Center**: Z = 0 (text baseline at Z = -text_size/2)
- **Surface**: Outer surface of ring at outer diameter
- **Curvature**: Text follows ring's circular curvature

### 5.2 Text Wrapping
- Text wraps around circumference if needed
- Maximum wrap: 360 degrees
- Excess text is truncated with warning

### 5.3 Text Rendering
- **Multi-line**: Newlines ignored (single line only)
- **Missing Characters**: Replaced with '?' or skipped if '?' unavailable
- **RTL Languages**: Not supported in current version

## 6. Boolean Operations

### 6.1 Embossed Text
- Text extends outward from outer surface by `text_depth`
- Boolean union operation with ring mesh

### 6.2 Carved Text
- Text extends inward from outer surface by `text_depth`
- Boolean difference operation with ring mesh
- Handles punch-through cases (when depth > ring thickness)

## 7. Export Specifications

### 7.1 STL Format
- **Format**: Binary STL
- **Units**: Millimeters
- **Mesh**: Single unified mesh (ring + text)
- **API**: `bpy.ops.wm.stl_export` (for recent Blender versions)

## 8. Error Handling

### 8.1 Exit Codes
| Code | Description | Examples |
|------|-------------|----------|
| 0 | Success | Normal execution |
| 1 | Input validation error | Invalid dimensions, missing required fields |
| 2 | File I/O error | Font file not found, cannot write STL |
| 3 | Blender operation error | Boolean operation failure, mesh generation error |

### 8.2 Validation Rules
- **Font File**: Must exist and be readable
- **Diameters**: inner_diameter < outer_diameter
- **Text Size**: < ring_length (auto-capped with warning if exceeded)
- **Text Depth**: <= ring_thickness (auto-capped with warning if exceeded)
- **Letter Spacing**: >= 0 and < ring_circumference
- **Embossed/Carved**: Default to embossed if both false

### 8.3 Logging
- Console output for immediate feedback
- Log file with timestamps for all warnings/errors
- Detailed error messages with suggested fixes

## 9. Default Values and Best Practices

### 9.1 Recommended Defaults
- **Radial Segments**: 256 (minimum for smooth wearing surface)
- **Text Mode**: Embossed (if not specified)
- **Letter Spacing**: 0 (use font's natural kerning)

### 9.2 Practical Constraints
- **Minimum Ring Thickness**: 1.5mm (for structural integrity)
- **Maximum Text Depth**: 50% of ring thickness (to prevent weakness)
- **Text Size Range**: 20-80% of ring length (for readability)

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
  "inner_diameter": 18.0,
  "outer_diameter": 22.0,
  "ring_length": 6.0,
  "stl_filename": "output/custom_ring.stl",
  "log_filename": "output/ring_generation.log"
}
```
