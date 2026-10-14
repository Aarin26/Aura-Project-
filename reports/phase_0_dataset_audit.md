# Phase 0: Dataset Audit and Ground Truth

| Metric / Requirement | Status | Details |
| :--- | :--- | :--- |
| **Phase Goal** | In Progress | Audit visual overlap, image quality, camera metadata, scale ground truth, and establish held-out split. |
| **Raw Master Preserved** | Ready for intake | `data/00_raw_master/` directory created. |
| **Source Image Manifest** | Pending intake | Manifest generator script ready at `scripts/audit_dataset.py`. |
| **Scale Reference Record** | Pending measurement | Template created at `manifests/scale_reference.json`. |
| **Held-out Split** | Pending dataset intake | Specification template created at `manifests/dataset_split.json`. |

---

## Phase 0 Checklist

### Task 0.1: Inventory & Preservation
- [ ] Place all captured source photographs into `data/00_raw_master/` (treat this folder as read-only).
- [ ] Run `python scripts/audit_dataset.py` to generate `manifests/source_manifest.csv` with SHA-256 hashes, file dimensions, and camera metadata.
- [ ] Check for mixed cameras, variable focal lengths, or stripped EXIF data.

### Task 0.2: Coverage & Image Quality Audit
- [ ] Verify that every key surface appears with $\ge$ 60–80% overlap across at least 3 distinct images.
- [ ] Verify multi-height 360° coverage (eye-level/mid, top-down/high, low angles where applicable, plus detail close-ups).
- [ ] Check that subject fills approximately 50–80% of the frame without clipping boundaries.
- [ ] Flag and exclude blurry shots, motion blur, severe lens flare, or large lighting variations.
- [ ] Note risks for transparent, reflective, or textureless surfaces.

### Task 0.3: Scale Ground Truth Calibration
- [ ] Measure a known physical reference distance in the scene (e.g. ruler, caliper measurement of known feature).
- [ ] Record ground truth distance, units (e.g. meters), and reference photo IDs in `manifests/scale_reference.json`.

### Task 0.4: Freeze Held-Out Validation Images
- [ ] Select 10–15% of clear viewpoints distributed around the object to reserve as held-out validation images.
- [ ] Copy or move held-out images to `data/02_held_out/`.
- [ ] Copy the remaining reconstruction set to `data/01_reconstruction/`.
- [ ] Record the image assignments in `manifests/dataset_split.json`.

---

## Exit Gate (M0)
Phase 0 is complete when:
1. `data/00_raw_master/` is checksummed in `manifests/source_manifest.csv`.
2. Coverage limitations and quality checks are signed off.
3. Known scale distance is recorded with uncertainty in `manifests/scale_reference.json`.
4. Held-out validation images are frozen in `data/02_held_out/` and will not be seen during SfM/meshing.

