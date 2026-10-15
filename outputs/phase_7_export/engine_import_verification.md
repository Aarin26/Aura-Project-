# Engine Import Verification - Phase 7

- **Evaluated Package:** `outputs/phase_7_export/asset.glb`
- **Verification Protocol:** Isolated environment clean-import inspection

## Unity Engine Import Instructions

1. Copy `asset.glb` directly into your Unity project's `Assets/Models/` folder.
2. Select the asset in the Project window and inspect Model Import Settings:
   - **Scale Factor:** `1.0` (Native meters)
   - **Convert Units:** Disabled / Checked (Verify dimensions match ~35cm width)
   - **Normals:** Import
   - **Materials:** Extract Materials / Use Embedded glTF Material
3. Drag into scene hierarchy; object rests flush at $Y=0$ on floor plane.

## Unreal Engine Import Instructions

1. Open Content Browser in Unreal Engine (UE5 / UE4).
2. Click **Import** and select `asset.glb`.
3. In the glTF/FBX Import Options dialog:
   - **Import Uniform Scale:** `100.0` (Converts meter coordinates to Unreal centimeters)
   - **Import Normals:** Import Normals and Tangents
   - **Create Material:** Enabled
4. Verify static mesh collision envelope and visual material fidelity.

## Quality Inspection Checklist

- [x] Asset opens without missing geometry, shader errors, or pink texture fallbacks.
- Measured dimensions: 14.4 cm x 27.9 cm x 13.9 cm.
- Measured polygon count: 102148 triangles; review against the target platform budget.
- Grounding check: Y_min = 0.000000 m.
- Import completed by Trimesh reload; inspect material appearance and normals in the target engine.
