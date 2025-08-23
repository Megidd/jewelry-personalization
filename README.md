# Install Blender on Linux

Steps:

* Download from official [website](https://www.blender.org)
* `mkdir -p ~/Applications`
* `cd ~/Applications`
* Copy downloaded `blender-4.5.2-linux-x64.tar.xz` file into `~/Applications`
* Extract downloaded file inside `~/Applications` by `tar -xf blender-4.5.2-linux-x64.tar.xz`
* `sudo ln -s ~/Applications/blender-4.5.2-linux-x64/blender /usr/local/bin/blender`

# Run code

Steps:

* Go into this repository folder
* Go into a sub-directory like `ring-flow`
* Run `run.sh` on commandline
* Edit inputs inside `config.json` to try out

## Direct command

The `run.sh` file simply executes this command:

```
blender --background --python script.py -- config.json
```

The above command can be directly executed on commandline too.

## First call

After each system reboot or login, the first time Blender is called, it might take some seconds. But subsequent calls would get quite fast.

# Cursive fonts

The available cursive fonts are inside `fonts` sub-directory. Font path is used inside the `config.json` file.

# Products

## Flow product

One of our products is the **flow** product which is available inside `ring-flow` subfolder.

Text letters have a continuous **flow** around the ring, so it's named the **flow** product.

The text arc and the ring arc are explementary or conjugate, they would sum up to be 360 degrees.

![Flow product screenshot](screenshots/ring-flow.png?raw=true "Flow product screenshot")

## Emboss product

One of our products is the **emboss** product which is available inside `ring-emboss` subfolder.

Text letters are raised or embossed on the surface of the ring, so it's named the **emboss** product.

![Emboss product screenshot](screenshots/ring-emboss.png?raw=true "Emboss product screenshot")
