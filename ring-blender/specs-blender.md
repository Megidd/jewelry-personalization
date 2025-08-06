The following sections are the specifictions for the required code.

# Script

A Python script file of `script.py` to employ Blender Python API.

# How to run

The script is to be run by this command on a Linux server without graphical user interface:

```
blender --background --python script.py -- config.json
```

# Units

All measurements are in millimeters.

# Case sensitivity

The written 3D text on the ring would be case sensitive.

# Ring

The ring's shape would be a cylinder with:

* Inner diameter.
* Outer diameter.
* Length.

# Configuration JSON

A JSON configuration file of `config.json` to be passed as input of the script.

The config file would contain user inputs, including:

* Text to be written.
* Path to TTF font file.
* Text diection.
   * Right-to-left.
   * Left-to-right.
   * One and only one of them should be true.
* Text size.
   * It's text height.
   * We don't get text width.
* Text is going to be either embossed (raised) or carved (removed) on the ring by a text depth.
   * At least either one of embossed or carved should be true.
   * Both cannot be true simultaneously.
   * if both are false, the script should default to embossed.
* Text depth.
   * The dimension of embossed or carved text with respect to the ring surface.
   * For embossing, text depth is how much text extends outward from the ring’s outer surface.
   * For carving, text depth is how much text extends inward from the ring's outer surface.
* Letter spacing.
   * It's in millimeter units betweeen letters.
* Ring inner diameter.
* Ring outter diameter.
* Ring length.
* STL export file name

# Export STL

Export STL result by `bpy.ops.wm.stl_export` API for recent Blender versions.

# Process

The script would process and create a jewelry ring with 3D text on it, like this:

* The `x` axis and `y` axis would form the plane for the ring.
   * Ring center would be at `0,0,0` coordinates.
   * Ring would extend half-length towards `+z` and half-length towards `-z`.
* The `z` axis would be perpendicular to the ring's `xy` plane.
* The text would be written on the ring's surface.
   * Text horizontal center would be located at the intersection of the ring's mesh with the `y` axis.
   * Text could possibly wrap around the entire ring circumference if text is too long.
      * If text wraps completely around and overlaps itself, it should stop at 360 degrees.
   * Text could possibly cover just a portion of ring circumference if text is short.
   * The text is curved to follow the ring’s curvature.
   * The text should be on the outer surface the ring, at the outer diameter of ring.

# Text orientation

As just documentation about text orientation, this camera would read the text from left-to-right correctly:

* Camera is located on the `y` axis.
* Camera is looking at the `-y` direction.
* Camera's up vector is `-z` axis.

# Text alignment

* Text is centered vertically on the ring’s length.
* There are not options for text alignment (center, left, right), since the text is aligned this way:
   * Text horizontal center is the location of `y` axis intersection with the ring outer circumference.

Text baseline is curved at ring’s outer surface, centered at positive Y axis.

# Error handling

The script should validate inputs and return proper error messages accordingly. For example when:

* If font file doesn’t exist.
* If inner diameter >= outer diameter.
* If text doesn’t fit on the ring, even after wrapping around the ring circumference.
   * If text wraps completely around and overlaps itself, it should stop at 360 degrees.

The script should return errors by:

* Print to console.
* Write to a log file.
* Return error codes.

# Font rendering

* Multi-line text are ignored. It means newlines are ignored in the string.
* Special characters not in the font are shown with question mark `?` or any other clear symbol.
* Right-to-left languages are handled by just switching the text direction.
   * Some fonts might lack the support for right-to-left characters:
      * In that case `?` symbol is shown for missing characters.

# STL export

The STL should be:

* binary.
* Millimeter units.
* Single mesh containing the 3D ring and the text on it.
