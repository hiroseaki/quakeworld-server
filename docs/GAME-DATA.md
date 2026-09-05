# Game data and maps

This project does not redistribute id Software game data.

## Required files

Copy your legally obtained files using lowercase names:

```text
data/id1/pak0.pak
data/id1/pak1.pak  # recommended
```

`pak0.pak` is required to start. `pak1.pak` supplies the rest of the registered
Quake content, including several maps in the default rotation. If you only have
`pak0.pak`, replace the rotation with maps available in that file, such as
`dm1`.

## Custom maps

Place loose server map files in `data/maps/`:

```text
data/maps/example.bsp
data/maps/example.ent  # optional entity override
```

Add the map base name (`example`) to `config/mapcycle.txt`, one map per line.
Blank lines and lines beginning with `#` are ignored. Location files go in
`data/locs/`.

Community map packs have their own licenses and redistribution terms. Verify
those terms before publishing them in an image or repository. Runtime mounts
are the safest default for privately owned or license-unclear assets.
