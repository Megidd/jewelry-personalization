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

# Cursive fonts

The available cursive fonts are inside `fonts` sub-directory. Font path is used inside the `config.json` file.
