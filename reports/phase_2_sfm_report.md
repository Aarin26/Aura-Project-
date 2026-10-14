# Phase 2: Image Preprocessing, Feature Matching, and SfM

| Brief | Details |
| :--- | :--- |
| **Goal** | Turn accepted photographs into a sparse reconstruction with estimated camera intrinsics/poses and 3D feature points |
| **Status** | 🔄 In Progress |
| **Depends on** | Phase 1 baseline (M1); Phase 0 dataset (M0) |
| **Exit milestone** | M2 — Coherent sparse model with camera poses and bundle-adjustment results saved |

---

## Task 2.1 — Preprocess and Inspect Metadata

- [ ] Load images and inspect EXIF metadata (focal length, camera model)
- [ ] Apply chosen tool's lens-distortion handling; add OpenCV correction step only if there is a clear need and it is documented
- [ ] If images come from different cameras/lenses, ensure the tool does not force one shared intrinsic model

## Task 2.2 — Extract and Match Features

- [ ] Run feature detection and cross-image matching (SIFT is a suitable offline choice)
- [ ] Inspect the image-match graph for disconnected clusters, weakly connected images, or likely false matches
- [ ] If matching fails, investigate image quality, overlap, camera grouping, and matching settings before changing later stages

## Task 2.3 — Estimate Structure from Motion

- [ ] Build the initial reconstruction from a strong overlapping image pair, then incrementally register additional images
- [ ] Run bundle adjustment to jointly refine camera parameters, poses, and sparse 3D points
- [ ] Save the sparse cloud, camera intrinsics/extrinsics, registered-image list, reprojection-error statistics, and logs

## Task 2.4 — Diagnose Registration Failures

- [ ] Identify images that did not register; determine whether each is redundant, low quality, or critical for a missing surface
- [ ] Do NOT silently drop a failed image if it is the only view of an important region
- [ ] If needed, revisit Phase 0 capture coverage or rerun with documented settings

---

## Running with COLMAP

```bash
# From the project root
python scripts/run_colmap_sfm.py \
    --image_dir data/01_reconstruction \
    --output_dir outputs/phase_2_sparse \
    --camera_model RADIAL
```

This will:
1. Extract features (SIFT)
2. Run exhaustive matching
3. Run the incremental SfM mapper
4. Convert the model to TXT format for inspection
5. Write `outputs/phase_2_sparse/run_settings.json` and `registration_report.md`

---

## Verification / Acceptance Gate (M2)

- [ ] Coherent single reconstruction produced (not disconnected components)
- [ ] Registered-image list and unregistered-image list reviewed and explained
- [ ] Camera poses and sparse geometry saved and re-openable
- [ ] Reprojection-error summary retained for comparison between runs

---

## Deliverables

| Deliverable | Path | Status |
| :--- | :--- | :--- |
| Sparse reconstruction | `outputs/phase_2_sparse/sparse/0/` | ⏳ Pending |
| Camera model and pose data | `outputs/phase_2_sparse/sparse/0/cameras.txt`, `images.txt` | ⏳ Pending |
| Registration/matching report | `outputs/phase_2_sparse/registration_report.md` | ⏳ Pending |
| Documented run settings | `outputs/phase_2_sparse/run_settings.json` | ⏳ Pending |

---

## Risks

| Risk | Handling |
| :--- | :--- |
| Repeated patterns, textureless regions, blur, reflections, weak overlap | Can cause incorrect matches or disconnected components — improve capture first |
| Missing EXIF data | Not an automatic blocker; if self-calibration is unstable, consider explicit camera calibration |

