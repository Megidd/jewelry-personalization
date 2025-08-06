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
* Text size.
* Text is going to be either embossed (raised) or carved (removed) on the ring by a text depth.
   * At least either one of embossed or carved should be true.
   * Both cannot be true simultaneously.
* Text depth.
   * The dimension of embossed or carved text with respect to the ring surface.
* Letter spacing.
* Ring inner diameter.
* Ring outter diameter.
* Ring length.
* STL export file name

# Export STL

Export STL result by `bpy.ops.wm.stl_export` API for recent Blender versions.

# Process

The script would process and create a jewelry ring with 3D text on it, like this:

* The `x` axis and `y` axis would form the plane for the ring.
* The `z` axis would be perpendicular to the ring's `xy` plane.
* The text would be written on the ring's surface.
   * Text center would be approximately located at the intersection of the ring's mesh with the `y` axis.
   * Text could possibly wrap around the entire ring circumference if text is too long.
   * Text could possibly cover just a portion of ring circumference if text is short.
   * If text is too long to fit, it should wrap around.
   * The text is curved to follow the ring’s curvature.
   * The text should be on the outer surface the ring, at the outer diameter of ring.
* This camera would read the text from left-to-right correctly:
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
