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
* Text depth
* Letter spacing
* Ring inner radius
* Ring outter radius
* Is ring shape of a cylinder with a height?
* Is ring shape of a torus?
* STL export file name

# Export STL

Export STL result by `bpy.ops.wm.stl_export` API for recent Blender versions.

