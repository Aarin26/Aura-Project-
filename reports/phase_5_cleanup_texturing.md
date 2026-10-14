# Phase 5: Mesh Cleanup, Optimization, UVs, and Texturing

| Brief | Details |
| :--- | :--- |
| **Goal** | Prepare a clean, efficient, textured asset that preserves recognizable shape and surface detail while meeting downstream runtime constraints |
| **Status** | ⏳ Not started |
| **Depends on** | Phase 4 raw mesh and dense cloud (M4) |
| **Exit milestone** | M5 — Cleaned, scaled, UV-mapped, textured candidate asset ready for validation and engine import |

---

## Task 5.1 — Clean the Mesh (MeshLab)

- [ ] Open `outputs/phase_4_dense/meshed.ply` in MeshLab
- [ ] Remove isolated floating fragments: Filters → Cleaning and Repairing → Remove Isolated Pieces
- [ ] Repair small holes: Filters → Remeshing → Close Holes (only well-bounded small holes)
- [ ] Recalculate normals: Filters → Normals, Curvatures and Orientation → Re-Compute Vertex Normals
- [ ] Remove duplicate geometry: Filters → Cleaning and Repairing → Remove Duplicate Faces/Vertices
- [ ] Save cleaned mesh to: `outputs/phase_5_textured/mesh_cleaned.ply`

## Task 5.2 — Optimize Polygon Count

- [ ] Measure raw triangle count in MeshLab
- [ ] Set polygon target based on intended Unity/Unreal use case; record the target in `optimization_settings.md`
- [ ] Apply decimation: Filters → Remeshing → Quadric Edge Collapse Decimation
- [ ] Check silhouette and fine details after each reduction step
- [ ] Save optimized mesh to: `outputs/phase_5_textured/mesh_optimized.ply`

## Task 5.3 — UV Unwrap (Blender)

- [ ] Import `mesh_optimized.ply` into Blender
- [ ] UV Unwrap using Smart UV Project or manual seams; inspect for overlaps, stretching, and wasted space
- [ ] Choose texture resolution based on object size and expected viewing distance; record in `optimization_settings.md`
- [ ] Save pre-UV mesh backup: `outputs/phase_5_textured/mesh_pre_uv.blend`

## Task 5.4 — Bake / Project Texture

- [ ] Project real image color using OpenMVS `TextureMesh` or Blender bake workflow
- [ ] Inspect seams, ghosting, color mismatches, blur, and texture bleeding around occluded regions
- [ ] Save texture maps as external files: `outputs/phase_5_textured/textures/`
- [ ] Confirm material references resolve correctly

## Task 5.5 — Prepare Asset Candidate

- [ ] Set object scale and origin per the documented convention in `outputs/phase_3_scaled/coordinate_convention.md`
- [ ] Name mesh, materials, and texture files consistently
- [ ] Create a preview render/turntable in Blender (separate from formal held-out validation)
- [ ] Save candidate: `outputs/phase_5_textured/mesh_textured.obj` (or `.blend`)

---

## Verification / Acceptance Gate (M5)

- [ ] No obvious floating fragments or accidental holes; any accepted defects listed in `defect_list.md`
- [ ] Decimation preserves overall silhouette and important details at target viewing distance
- [ ] UVs and material references are valid; texture seams and ghosting have been reviewed
- [ ] Candidate remains in documented real-world scale and coordinate convention
- [ ] Optimized mesh and texture files re-openable in Blender without missing assets

---

## Deliverables

| Deliverable | Path | Status |
| :--- | :--- | :--- |
| Cleaned/optimized mesh | `outputs/phase_5_textured/mesh_optimized.ply` | ⏳ Pending |
| UV layout | `outputs/phase_5_textured/mesh_textured.obj` + UVs | ⏳ Pending |
| Texture maps and material | `outputs/phase_5_textured/textures/` | ⏳ Pending |
| Candidate asset preview | `outputs/phase_5_textured/preview_render.png` | ⏳ Pending |
| Optimization settings | `outputs/phase_5_textured/optimization_settings.md` | ⏳ Pending |
| Known-defect list | `outputs/phase_5_textured/defect_list.md` | ⏳ Pending |

---

## Risks

| Risk | Handling |
| :--- | :--- |
| Aggressive decimation erases thin parts or surface detail | Compare against raw mesh at each optimization step |
| Texture quality constrained by photo coverage and exposure | Texturing cannot recover detail never captured |

