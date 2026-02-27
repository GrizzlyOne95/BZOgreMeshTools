# rthook_ogre.py — Runtime hook executed before any user code
# With --onefile, PyInstaller extracts all files to a temp folder (_MEIPASS).
# Ogre's native DLL loader (and Windows LoadLibrary) needs that folder on PATH
# so render-system plugins (RenderSystem_Direct3D11.dll, etc.) can be found.

import os
import sys

_meipass = getattr(sys, "_MEIPASS", None)
if _meipass:
    # Add extraction dir and Ogre subdir to PATH so Windows finds Ogre DLLs
    ogre_dir = os.path.join(_meipass, "Ogre")
    
    current_path = os.environ.get("PATH", "")
    new_path = f"{_meipass};{ogre_dir};{current_path}"
    os.environ["PATH"] = new_path
    
    # We do NOT os.chdir() here as it breaks relative paths for main app resources

