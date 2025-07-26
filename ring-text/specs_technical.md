The specifications for 3D logic of roadmap phase 1 are described here.

# Technology

Any programming language is fine, as far as:

* Code is simple and readable
* Code is straightforward
* Code is easy to maintain
* Result is reliable
* Result is convenient to test
* MVP UI is easy to develop and test

## Backend vs frontend

The frontend technologies like JavaScrip and libraries like ThreeJS would offload the computational expenses on user browser. So, the server can be cheaper.

The backend technologies like Python or Golang would require a more expensive server to do the 3D processing.

### Preference

Therefore, JavaScript technology is preferred along with a robust library like ThreeJS.

# Input

* Text
   * User would enter a text.
   * Like their name or the name of their loved ones.
* Font
   * User would choose a font.
   * Its just a personal preference.
   * UI would display a list of fonts to choose from.
   * Selectable fonts are the ones that connect letters together somehow.
      * To avoid the letters being fallen apart.
* Assets
   * For now, we skip the extra assets
* Ring standard size
   * User would choose the ring standard size from a list.
   * The ring size should be according to a popular industry standard.
* Text configuration
   * Space between letters
   * The max arch degrees on the ring occupied by the tex
   * ...

# Process

## Ring creation

The logic would create a simple 3D model for the ring according to the standard size passed as input. The ring is just like a simple tube or donut or torus.

## Text adjustment

* Text is convereted to a 3D model according to the font passed as input.
* A curvature is applied to the text 3D model to be able to add it to the 3D model of the ring.
   * Focusing on text baseline is not the current approach.
   * Each should individual letter should be rotated and positioned properly.
* A curvature might be applied to each letter of the text 3D model.
   * Implementing proper curving is done by applying proper rotation and position to each letter.
   * So that each individual letter is perpendicular to the ring radius.
   * So that each individual letter has proper curving in addition to positioning.
   * Individual letters shouldn't be deformed or warped.
   * Each letter can be roated around the cylindrical axis of the ring to follow the ring’s cylindrical surface.
* Text 3D model is resized so that it can fit properly on the ring.
   * Spacing between letters can be adjusted too.
* Text 3D model can occupy an arch in degrees available on the ring.
   * Spacing between letters can be adjusted.

### Mathematical formulas for curvature

For now, some sane assumptions might be employed for curvature formulas.

## Ring cutout

The 3D model of the ring is cut out at the arch which is occupied by the text 3D model. But the 3D model of the ring is properly connected to the 3D text to be a coherent 3D model without falling apart.

### CSG

For constructive solid geometry, the following CSG library for ThreeJS can be used:

https://github.com/gkjohnson/three-bvh-csg

A demo of the CSG library is available on ThreeJS official website at this page:

https://threejs.org/examples/webgl_geometry_csg.html

#### CSG expense

CSG can be computationally expensive. But for now, ignore the computational expense.

CSG operations are done in real-time.

#### CSG fail

If CSG operations fail or produce invalid geometry, show an alert on the UI and ask user to change inputs accordingly.

## Precise measurements

* Ring thickness/width
   * For now, a reasonable assumption is made according to:
      * Ring size passed as input
* Text depth/height relative to ring
   * For now, a resaonable assumption is made according to:
      * Ring size passed as input
* Minimum/maximum text size constraints
   * For now, a reasonable assumption is made according to:
      * Ring size passed as input
* Gap tolerances between letters
   * For now, a reasonable assumption is made according to:
      * Ring size passed as input
      * SLA 3D print constraints

# Output

These 3D models are connected together to create the final 3D model:

* Ring 3D model:
   * Cut out at the arch occupied by the 3D model of the text.
* Text 3D model:
   * Curved and resized according to the ring size and curvature.
* Total weight:
   * Weight estimation based on volume calculation and gold's material density.
   * Weight = Volume × Material Density
   * gold density = 19.3 g/cm³

The UI would display the final 3D model. User can view the final 3D model.

# UI

A minimal UI to take inputs and display the output would be great to test and evaluate the reliability of the logic.

## HTML, CSS, and JavaScript

The minimal UI can be a simple HTML/CSS file. The file would make use of the JavaScript code and libraries like ThreeJS to handle the 3D processing.

# Data format

Any data format might be picked up. Like:

* Data buffers provided by the libraries employed. Like ThreeJS.
* STL ASCII file format.
* Any other data format.

Readability and reliability will be preserved.

# Manufacturing constraints

For now, the manufacturing constraints are ignored, like:

* SLA 3D print constraints
* Metal casting constraints

Currently, we just focus on aesthetics and user preference.

## Witertight

At the moment, it should be ensured that the final mesh is a single, watertight geometry suitable for 3D printing

### Validation

Validation of watertight geometry can be ignored for now.

# Example

## Without text

Rough schematics for side view of a ring without text:

```
    .--------.
  ,'          `.
 /              \
|                |
|                |
 \              /
  `.          ,'
    `--------'
```

## With text

Rough schematics for side view of a ring with text:

```
    .--TEXT--.
  ,'          `.
 /              \
|                |
|                |
 \              /
  `.          ,'
    `--------'
```
