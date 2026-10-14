# Phase 6: Validation Against Held-Out Photos

| Brief | Details |
| :--- | :--- |
| **Goal** | Evaluate geometric and visual quality using photos deliberately excluded from reconstruction, measuring generalization to unseen viewpoints |
| **Status** | ⏳ Not started |
| **Depends on** | Phase 5 candidate asset (M5); Phase 0 held-out set (M0) |
| **Exit milestone** | M6 — Validation report records objective comparisons, visual findings, acceptance decisions, and required iterations |

---

## Task 6.1 — Estimate Held-Out Camera Poses

- [ ] Localize each held-out image against the COLMAP reconstruction (image_registrator) without adding the image to the reconstruction
- [ ] Record any held-out image that cannot be localized reliably, and explain why

```bash
colmap image_registrator \
    --database_path outputs/phase_2_sparse/colmap.db \
    --input_path outputs/phase_3_scaled \
    --output_path outputs/phase_6_validation/localized_poses
```

## Task 6.2 — Compare Render to Photo

- [ ] Render the candidate mesh from the estimated held-out camera viewpoint using Blender or Open3D
- [ ] Compare silhouette, proportions, visible features, and texture alignment against the real photograph
- [ ] Use SSIM as a supporting metric — NOT the only quality decision

```bash
python scripts/validate_held_out.py \
    --mesh outputs/phase_5_textured/mesh_textured.obj \
    --sparse_dir outputs/phase_3_scaled \
    --held_out_dir data/02_held_out \
    --output_dir outputs/phase_6_validation
```

## Task 6.3 — Measure Geometry and Document Defects

- [ ] Compare known dimensions against real measurements where available
- [ ] Record per-view observations, failed regions, and repeatable metrics
- [ ] Separate geometry defects from texture-only defects (different corrective actions)

## Task 6.4 — Iterate with Traceability

- [ ] Map each failed criterion to the earliest likely cause: capture → SfM → scale → dense → meshing → texturing
- [ ] Change one meaningful factor at a time and rerun affected downstream stages
- [ ] Do NOT move held-out photos into the reconstruction set just to improve scores

---

## Verification / Acceptance Gate (M6)

- [ ] Every held-out image has a recorded result (localized and compared, or marked unscorable with reason)
- [ ] Rendered-versus-real comparisons saved for representative views in `outputs/phase_6_validation/renders/`
- [ ] Known physical dimensions checked against ground truth where available
- [ ] Project owner accepts the documented quality, or asset returns to responsible phase
- [ ] Report distinguishes measured evidence from subjective visual review

---

## Deliverables

| Deliverable | Path | Status |
| :--- | :--- | :--- |
| Validation config | `outputs/phase_6_validation/validation_config.json` | ⏳ Pending |
| Rendered comparison images | `outputs/phase_6_validation/renders/` | ⏳ Pending |
| Per-view metrics CSV | `outputs/phase_6_validation/per_view_results.csv` | ⏳ Pending |
| Validation report | `outputs/phase_6_validation/validation_report.md` | ⏳ Pending |

---

## Risks

| Risk | Handling |
| :--- | :--- |
| SSIM/pixel metrics affected by lighting and exposure | Pair metrics with silhouette and geometry review |
| Repeated use of held-out photos to tune settings | Preserve a fresh validation subset; once held-out images tune settings, they are no longer independent |

