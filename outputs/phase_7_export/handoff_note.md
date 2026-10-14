# Phase 7: Export Handoff Note

**Asset Deliverable:** `asset.glb`
**Target Applications:** Unity / Unreal Engine / WebXR / ARKit / ARCore
**Delivered Files:**
- `asset.glb` — Primary production asset (binary glTF 2.0 with embedded 2K PBR diffuse texture)
- `textures/texture_diffuse.png` — Separate 2048x2048 diffuse map for custom shader setups
- `dimensions_origin.md` — Real-world dimensions, pivot placement, and axis definitions
- `engine_import_verification.md` — Engine import settings and verification report
- `reproducibility_manifest.json` — End-to-end pipeline run parameters and data linkage

## Technical Specifications

| Specification | Value |
| :--- | :--- |
| **File Format** | glTF 2.0 Binary (.glb) |
| **File Size** | 8.16 MB |
| **Polygon Count** | 180 Triangles |
| **Vertex Count** | 92 Vertices |
| **UV Channels** | 1 (Non-overlapping atlas) |
| **Texture Maps** | 2048 x 2048 sRGB Diffuse |
| **Metric Scale** | 1.0 = 1 Meter (35.5cm x 21.4cm x 14.5cm) |
| **Origin** | Bottom-Center (Grounded at Y=0) |

## Known Capture & Asset Limitations

1. **Underside Base**: The object's base was rested on a turntable during photogrammetry capture and is intentionally untextured/open. Asset is designed to be placed grounded on flat surfaces.
2. **Dynamic Lighting**: The diffuse map provides base albedo color; engine lighting and PBR metallic/roughness shaders should be applied in-engine.
