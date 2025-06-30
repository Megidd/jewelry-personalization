I need a WooCommerce platform with the following specifications. Can you help me with detailed setup instructions along with the WooCommerce source code to bring up such a platform on an Ubuntu 22.04.5 LTS server?

Setup instructions should include connecting the WooCommerce platform to a domain name like `facegold.com`.

Please explain it as if I'm a novice about programming and servers.

# UI

## Input

Through the UI, the user uploads an image. Please:

* Convert image to PNG if it's not in PNG file format.
* Modify the input image so that its width and width are equal.
* Max width and height size is `1000` pixels.
* Make sure the image is not _grayscale_ and input image has to be converted to RGB.

## Output

Through the UI, the user receives a 3D model corresponding to the uploaded image. Please:

* Return a sample placeholder 3D model in `*.ply` file format.
* For now, keep the 3D model a sample placeholder:
   * But in the future, sophisticated logic will be run to generate the corresponding 3D model.
* Display the returned 3D model on the UI.
* Please use some sort of 3D viewer:
   * So that the user will be able to view the 3D model in 3D space.
