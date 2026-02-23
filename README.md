# Ogre Mesh Tools

Ogre Mesh Tools is a Windows GUI utility for fixing and converting Ogre `.mesh` / `.xml` files. It wraps the core Ogre tools with a Battlezone-inspired interface and a clean, single-button workflow.

## What It Can Do

- Recalculate normals to fix bad lighting on legacy meshes.
- Convert Ogre meshes to OBJ (static mesh export).
- Convert Ogre meshes to glTF (`.glb`) using Blender (supports rigs/animations).
- Process a single file or batch-convert entire folders.
- Write outputs into `OBJ_Export` and `glTF_Export` directories next to your input.

## How To Use

1. Launch `ogre_mesh_tools_gui.py` (or the Windows release executable).
2. Choose a single `.mesh`/`.xml` file or enable `BATCH DIRECTORY MODE` and select a folder.
3. Select the operations you want: `RECALCULATE NORMALS`, `CONVERT TO OBJ`, `CONVERT TO glTF`.
4. `RECALCULATE NORMALS` uses XML conversion internally.
5. `CONVERT TO OBJ` outputs a standalone static mesh.
6. `CONVERT TO glTF` requires Blender for import and export.
7. If using glTF, set your Blender path in `SETTINGS`.
8. Click `INITIALIZE CONVERSION SEQUENCE`.
9. Click `OPEN EXPORT DIRECTORY` to jump to the results.

## Requirements

- Windows for the prebuilt executable.
- Python 3.x if running from source.
- Blender for glTF export (set in the GUI).
- `OgreXMLConverter.exe` bundled with the repo/release.

---
Created for the Battlezone 98 Redux Community.
