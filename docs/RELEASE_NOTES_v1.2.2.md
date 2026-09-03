# BZ Ogre Mesh Tools v1.2.2

## Summary

Maintenance release containing the current robustness and code-health fixes since v1.2.1.

## Fixed

- Added safer exception handling around Ogre preview initialization.
- Defined the preview application directory consistently to avoid a potential `NameError`.
- Cleaned up preview formatting/indentation issues and invalid f-string usage.
- Removed unused imports from preview and normal-recalculation helpers.

## Download

Download `OgreMeshTools_Windows.exe` from this release.

This remains a Windows-focused packaged build because the conversion workflow includes the bundled Ogre command-line/runtime tools used by the application.
