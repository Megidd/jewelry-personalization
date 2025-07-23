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

There is a note that might be considered.

The frontend technologies like JavaScrip and libraries like ThreeJS would offload the computational expenses on user browser. So, the server can be cheaper.

The backend technologies like Python or Golang would require a more expensive server to do the 3D processing.

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

# Process

## Ring creation

The logic would create a simple 3D model for the ring according to the standard size passed as input. The ring is just like a simple tube or donut or torus. ~~The ring is created in STL ASCII file format.~~

## Text adjustment

* Text is convereted to a 3D model according to the font passed as input.
* A curvature is applied to the text 3D model to be able to add it to the 3D model of the ring.
* A different curvature might be applied to each letter of the text 3D model.
   * So that each text letter is perpendicular to the ring radius.
   * The text should be 
* Text 3D model is resized so that it can fit properly on the ring.
* Text 3D model can occupy at most 90 degrees out of the 360 degrees available on the ring.

## Ring cut

The 3D model of the ring is cut at the location which is occupied by the text 3D model. But the 3D model of the ring is properly connected to the 3D text to be a coherent 3D model without falling apart.

# Output

These 3D models are connected together to create the final 3D model:

* Ring 3D model:
   * Cut at the sections which are occupied by the 3D model of the text.
* Text 3D model:
   * Curved and resized according to the ring size and curvature.

The UI would display the final 3D model. User can view the final 3D model.

# UI

A minimal UI to take inputs and display the output would be great to test and evaluate the reliability of the logic.
