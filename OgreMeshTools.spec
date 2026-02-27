# OgreMeshTools.spec
# PyInstaller spec file for BZOgreMeshTools
# Build with: py -3.10 -m PyInstaller OgreMeshTools.spec --noconfirm

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# ── Locate the ogre-python package ────────────────────────────────────────────
import importlib.util
_ogre_spec = importlib.util.find_spec("Ogre")
if _ogre_spec.submodule_search_locations:
    OGRE_PKG = os.path.abspath(_ogre_spec.submodule_search_locations[0])
else:
    OGRE_PKG = os.path.abspath(os.path.dirname(_ogre_spec.origin))

# --- DEFINITIVE OGRE MEDIA SEARCH ---
# Ogre-python sometimes puts Media in site-packages/Ogre/Media, 
# or in the Python root (Python310/Media).
MEDIA_SRC = None
search_roots = [
    OGRE_PKG,
    os.path.dirname(OGRE_PKG), # site-packages
    os.path.dirname(os.path.dirname(OGRE_PKG)), # lib
    os.path.dirname(os.path.dirname(os.path.dirname(OGRE_PKG))) # Python root
]
for root in search_roots:
    potential = os.path.join(root, "Media")
    if os.path.isdir(potential):
        MEDIA_SRC = potential
        break

if not MEDIA_SRC:
    print(f"WARNING: Ogre Media folder NOT FOUND! Search roots: {search_roots}")
else:
    print(f"FOUND OGRE MEDIA AT: {MEDIA_SRC}")

# ── Locate customtkinter (needs its image assets) ─────────────────────────────
import customtkinter as _ctk
CTK_PKG = os.path.dirname(_ctk.__file__)

# ── All Ogre DLLs to bundle ───────────────────────────────────────────────────
OGRE_DLLS = [
    "OgreMain.dll",
    "OgreBites.dll",
    "OgreOverlay.dll",
    "OgreRTShaderSystem.dll",
    "OgreTerrain.dll",
    "OgreBullet.dll",
    "OgrePaging.dll",
    "RenderSystem_Direct3D11.dll",
    "RenderSystem_GL.dll",
    "RenderSystem_GL3Plus.dll",
    "RenderSystem_GLES2.dll",
    "RenderSystem_Tiny.dll",
    "Plugin_DotScene.dll",
    "Plugin_GLSLangProgramManager.dll",
    "Plugin_OctreeSceneManager.dll",
    "Plugin_ParticleFX.dll",
    "Codec_Assimp.dll",
    "Codec_STBI.dll",
    "SDL2.dll",
    "zlib.dll",
]

binaries = []
for dll in OGRE_DLLS:
    src = os.path.join(OGRE_PKG, dll)
    if os.path.isfile(src):
        binaries.append((src, "Ogre"))          # land in dist/OgreMeshTools_Windows/Ogre/

# Ogre .pyd extension modules land alongside the .py wrappers inside Ogre/
for f in os.listdir(OGRE_PKG):
    if f.endswith(".pyd"):
        binaries.append((os.path.join(OGRE_PKG, f), "Ogre"))

# ── Data files ────────────────────────────────────────────────────────────────
datas = [
    # Ogre Python wrapper scripts
    (os.path.join(OGRE_PKG, "*.py"),  "Ogre"),
    # Ogre Media (RTShader system headers, etc.)
    (MEDIA_SRC if MEDIA_SRC else os.path.join(OGRE_PKG, "Media"), "Ogre/Media"),
    # customtkinter assets (images, themes)
    (CTK_PKG, "customtkinter"),
    # Project data files
    ("BZONE.ttf",              "."),
    ("BZBase.material",        "."),
    ("MeshToObj.py",           "."),
    ("batch_ogre_to_gltf.py",  "."),
    ("OgreImport.py",          "."),
    ("recalculate_normals.py", "."),
    ("ogre_preview.py",        "."),
    # Helper executables
    ("OgreXMLConverter.exe",   "."),
    ("OgreMeshUpgrader.exe",   "."),
    ("OgreMeshMagick.exe",     "."),
    # Ogre companion DLLs already in the project root
    ("OgreMain.dll",               "."),
    ("OgreMeshLodGenerator.dll",   "."),
    ("zlib.dll",                   "."),
]

# Filter datas entries whose source glob/file doesn't exist
import glob
filtered_datas = []
for src, dst in datas:
    if glob.glob(src):          # glob handles wildcards
        filtered_datas.append((src, dst))
datas = filtered_datas

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["ogre_mesh_tools_gui.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "Ogre",
        "Ogre.Bites",
        "Ogre.RTShader",
        "Ogre.Overlay",
        "Ogre.Terrain",
        "customtkinter",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["rthook_ogre.py"],
    excludes=[
        # Ogre renderers we don't need on Windows
        "RenderSystem_Vulkan",
        "RenderSystem_GL",
        "RenderSystem_GL3Plus",
        "RenderSystem_GLES2",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,        # <-- embedded directly for --onefile
    a.datas,           # <-- embedded directly for --onefile
    name="OgreMeshTools_Windows",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,         # UPX breaks native DLLs
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,     # windowed — no console popup
    disable_windowed_traceback=False,
    icon=None,
)
# No COLLECT step — everything is inside the single EXE

