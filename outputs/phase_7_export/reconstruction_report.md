# 3D Photogrammetry Reconstruction Report: syncom_bottle

- **Generated:** 2026-10-15T05:51:05.611879
- **Vertices:** 19,660
- **Triangles:** 39,332
- **Watertight Manifold:** False
- **Width (X):** 8.9 cm
- **Height (Y):** 18.0 cm
- **Depth (Z):** 9.0 cm
- **Origin:** Ground plane contact ($Y = 0.0000$ m)

## Deliverables

| File | Format | Description |
| :--- | :--- | :--- |
| `asset.glb` | glTF 2.0 Binary | PBR material + embedded diffuse texture + vertex colors |
| `asset.obj` | Wavefront OBJ | Smooth shading normals `vn`, seam-split `vt`, `asset.mtl` |
| `asset.ply` | Stanford PLY | Fused mesh with RGB vertex colors |
| `textures/texture_diffuse.png` | PNG | 1024x1024 diffuse color texture map |
| `preview_render.png` | PNG | Multi-angle inspection preview board |

## How to View in Blender

1. Open Blender.
2. Select `File > Import > glTF 2.0 (.glb/.gltf)` (or `File > Import > Wavefront (.obj)`).
3. Select `C:\Users\aarin\OneDrive\Desktop\Vuforia\Aura-Project-\outputs\phase_7_export\asset.glb` (or `C:\Users\aarin\OneDrive\Desktop\Vuforia\Aura-Project-\outputs\phase_7_export\asset.obj`).
4. Press `Z` and choose **Material Preview** to view the full smooth textured 3D model.
