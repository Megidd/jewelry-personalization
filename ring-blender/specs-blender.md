The following sections are the specifictions for the required code.

# Script

A Python script file of `script.py` to employ Blender Python API.

# How to run

The script is to be run by this command on a Linux server without graphical user interface:

```
blender --background --python script.py -- config.json
```

# Configuration JSON

A JSON configuration file of `config.json` to be passed as input of the script.

The config file would contain user inputs, including:

* Text to be written
* Path to TTF font file
* Text size
* Is text going to be embossed (raised) on the ring by a text depth?
* Is text going to be carved (removed) on the ring by a text depth?
* Letter spacing
* Ring inner radius
* Ring outter radius
* Is ring shape of a cylinder with a height?
* Is ring shape of a torus?
* STL export file name

# Export STL

Export STL result by `bpy.ops.wm.stl_export` API for recent Blender versions.

# Process

The script would process and create a jewelry ring with 3D text on it, like this:

* The `x` axis and `y` axis would form the plane for the ring.
* The `z` axis would be perpendicular to the ring's `xy` plane.
* The text would be written on the ring's surface.
   * Text center would be approximately located at the intersection of the ring's mesh with the `y` axis.
* This camera would read the text from left-to-right correctly:
   * Camera is located on the `y` axis.
   * Camera is looking at the `-y` direction.
   * Camera's up vector is `-z` axis.
