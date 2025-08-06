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

The ring creation as a cylinder should be smooth enough to be worn by human finger.

# Configuration JSON

A JSON configuration file of `config.json` to be passed as input of the script.

The config file would contain user inputs, including:

* Text to be written.
* Path to TTF font file.
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
* Log file name.
   * Containing errors and other logs.

# Export STL

Export STL result by `bpy.ops.wm.stl_export` API for recent Blender versions.

# Process

The script would process and create a jewelry ring with 3D text on it.

# Ring orientation

* The `x` axis and `y` axis would form the plane for the ring.
   * Ring center would be at `0,0,0` coordinates.
   * Ring would extend half-length towards `+z` and half-length towards `-z`.
* The `z` axis would be perpendicular to the ring's `xy` plane.

# Text orentation

The text would be written on the ring's surface:

* Text horizontal center would be located at the intersection of the ring's mesh with the `+y` axis.
* Text could possibly wrap around the entire ring circumference if text is too long.
   * If text wraps completely around and overlaps itself, it should stop at 360 degrees.
      * The remaining text is just truncated.
* Text could possibly cover just a portion of ring circumference if text is short.
* The text is curved to follow the ring’s curvature.
* The text should be on the outer surface the ring, at the outer diameter of ring.

# Text size

* Input text size in JSON file is the height along the Z-axis, parallel to ring length.
* It is measured before curving.
* It should be smaller the ring’s length, of course.

# Letter spacing

Letter spacing in JSON file:

* It is the the arc length between letters on the curved surface.
* It is measured from letter edge to edge:
   * The value is just added to the kerning from the font file.

# Text orientation

As just documentation about text orientation, this camera would read the text from left-to-right correctly:

* Camera is located on the `y` axis.
* Camera is looking at the `-y` direction.
* Camera's up vector is `-z` axis.

# Text alignment

* Text is centered vertically on the ring’s length.
* There are not options for text alignment (center, left, right), since the text is aligned this way:
   * Text horizontal center is the location of `+y` axis intersection with the ring outer circumference.

Text baseline is curved at ring’s outer surface, centered at positive Y axis.

# Text vertical centering

Text is centered vertically on the ring’s length. This mean:

* The text’s vertical center is at `Z=0`.
* Therefore, the text baseline is at `Z=-(text height or text size)/2`.

# Text wrapping

If the entire supplied text plus letter spacing does not fit before reaching 360 degrees, the script truncates it to fit and issues a warning/log.

# Error handling

The script should validate inputs and return proper error messages accordingly. For example when:

* If font file doesn’t exist.
* If inner diameter >= outer diameter.
* If text doesn’t fit on the ring, even after wrapping around the ring circumference.
   * If text wraps completely around and overlaps itself, it should stop at 360 degrees.
      * The remaining text is just truncated.
* Text Depth for Different Ring Thicknesses:
   * If text depth is greater than ring thickness
   * There should be validation for this case.

The script should return errors by:

* Print to console.
* Write to a log file.
* Return error codes.

# Font rendering

* Multi-line text are ignored. It means newlines are ignored in the string.
* Special characters not in the font are shown with question mark `?` or any other clear symbol.
* Right-to-left languages are ignored for now.

# STL export

The STL should be:

* binary.
* Millimeter units.
* Single mesh containing the 3D ring and the text on it.

# Boolean operation

For carved text, the boolean difference operation should handle edge cases, like when the carved depth is more than the ring thickness and the carving will be punching through the inner diameter.
