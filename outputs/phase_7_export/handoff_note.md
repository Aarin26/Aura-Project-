# Phase 7: Handoff Note

**Date:** *(fill in)*
**Prepared by:** *(fill in)*
**Receiving team:** *(Unity / Unreal team)*

---

## Delivered Files

| File | Description |
| :--- | :--- |
| `asset.glb` (or `.fbx`) | Final validated 3D asset |
| `textures/` | External texture maps (if not embedded in GLB) |
| `dimensions_origin.md` | Real-world dimensions, origin, and axis convention |
| `engine_import_verification.md` | Import checklist and evidence |
| `reproducibility_manifest.json` | Links export to source images and reconstruction settings |
| `../phase_6_validation/validation_report.md` | Held-out validation results |

---

## Import Instructions

1. Open the target engine project
2. Import the asset file
3. **Do not rescale** — asset is already in meters (Unity) or multiply by 100 (Unreal cm)
4. Verify orientation matches `dimensions_origin.md`
5. Check that all textures/materials appear correctly

---

## Known Limitations

*(Copy from `outputs/phase_5_textured/defect_list.md` — surfaces with capture gaps or geometry defects)*

---

## What Would Require Recapture

*(Document which surfaces or details, if needed in future, would require new photographs)*

---

## Contact

For reconstruction questions or to request revisions:
**Reconstruction owner:** *(fill in)*

