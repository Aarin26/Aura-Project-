# Phase 7: Export, Engine Import, and Handoff

| Brief | Details |
| :--- | :--- |
| **Goal** | Package the validated asset in a standard format with textures, real-world dimensions, and coordinate/origin metadata for Unity/Unreal import |
| **Status** | ⏳ Not started |
| **Depends on** | Phase 6 accepted validation report (M6) |
| **Exit milestone** | M7 — Asset imports into the target engine at expected size and appearance; handoff package complete |

---

## Task 7.1 — Export the Asset (Blender)

- [ ] Open the final candidate mesh in Blender
- [ ] Verify scale (1 Blender unit = 1 meter), origin, and orientation are correct
- [ ] Export as **glTF 2.0 (.glb or .gltf+bin)** — preferred format
  - File → Export → glTF 2.0
  - Check: Include → Mesh Data, Materials, UVs; Geometry → Apply Modifiers
- [ ] OR export as FBX if required by the receiving team's pipeline
- [ ] Save to: `outputs/phase_7_export/`

## Task 7.2 — Verify the Package

```bash
python scripts/export_asset.py \
    --export_file outputs/phase_7_export/asset.glb \
    --output_dir outputs/phase_7_export
```

- [ ] Open the exported file in a **clean** Blender session (File → New, then import)
- [ ] Check: dimensions in meters, origin placement, orientation, normals, material appearance, polygon count
- [ ] Confirm texture files are included or embedded; avoid absolute file paths

## Task 7.3 — Test in Unity or Unreal

- [ ] Import the asset into the target engine
- [ ] Verify scale, orientation, material/texture appearance, and expected visual quality
- [ ] Check whether axis conversion or specific import settings are needed; record the agreed convention
- [ ] Capture an import screenshot as evidence → save to `outputs/phase_7_export/engine_import_verification.md`

## Task 7.4 — Freeze and Archive the Release

- [ ] Version the final mesh, texture maps, export file, source image manifest, pipeline configuration, and validation report together
- [ ] Label the final deliverable clearly; keep intermediate/raw files available for future repairs
- [ ] Document known limitations and what would require recapture rather than downstream editing
- [ ] Finalize `outputs/phase_7_export/reproducibility_manifest.json`

---

## Verification / Acceptance Gate (M7)

- [ ] Exported FBX/glTF opens without missing geometry, material, or texture references
- [ ] Real-world dimensions, origin point, units, and orientation explicitly documented
- [ ] Target Unity/Unreal import verified by inspection (not assumed from export success)
- [ ] Final package contains asset, textures/materials, handoff note, and validation report
- [ ] Reproducible record links the final export to its source images and reconstruction settings

---

## Deliverables

| Deliverable | Path | Status |
| :--- | :--- | :--- |
| Final FBX or glTF asset | `outputs/phase_7_export/asset.glb` (or `.fbx`) | ⏳ Pending |
| Texture/material package | `outputs/phase_7_export/textures/` | ⏳ Pending |
| Dimensions and origin note | `outputs/phase_7_export/dimensions_origin.md` | ⏳ Pending |
| Engine import verification | `outputs/phase_7_export/engine_import_verification.md` | ⏳ Pending |
| Handoff note | `outputs/phase_7_export/handoff_note.md` | ⏳ Pending |
| Reproducibility manifest | `outputs/phase_7_export/reproducibility_manifest.json` | ⏳ Pending |

---

## Risks

| Risk | Handling |
| :--- | :--- |
| Axis, unit, and origin mismatches make a correct model unusable | Agree on target convention and test it in-engine before final handoff |
| Broken texture links on another machine | Keep export self-contained (GLB) or use relative texture paths |

