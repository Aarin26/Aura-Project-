# Phase 3: Scale Calibration and Sparse-Model Quality Gate

| Brief | Details |
| :--- | :--- |
| **Goal** | Resolve SfM scale ambiguity and confirm the sparse model is coherent enough to justify the cost of dense reconstruction |
| **Status** | ✅ Completed / Verified (Pilot Baseline) |
| **Depends on** | Phase 2 sparse reconstruction (M2) |
| **Exit milestone** | M3 — Reconstruction expressed in documented real-world units; scale and sparse geometry pass review |

---

## Task 3.1 — Apply Real-World Scale

- [x] Identified reference 3D points in sparse model corresponding to known physical measurement:
  - **Point 1 (Marker A)** and **Point 2 (Marker B)**
  - Unscaled SfM distance: $1.000000$ units
  - Real-world ground truth: $0.350000$ meters ($350$ mm)
  - Scale factor applied: `0.35000000`
- [x] Executed calibration utility:
  ```bash
  python scripts/apply_scale.py \
      --sparse_dir outputs/phase_2_sparse/sparse/0 \
      --output_dir outputs/phase_3_scaled \
      --scale_reference manifests/scale_reference.json
  ```
- [x] Verified `outputs/phase_3_scaled/scale_calibration_record.json` and `scale_calibration_record.md`.

## Task 3.2 — Set Coordinate Conventions

- [x] Standard unit documented: **Meters (m)**
- [x] Verified camera translation vectors and 3D point positions are scaled with 1:1 metric correspondence.
- [x] Provisional origin set at point cloud centroid $(0, 0, 0)$; final asset ground origin $(Y_{\min}=0)$ documented for Unity/Unreal handoff.
- [x] Complete coordinate specification recorded in `outputs/phase_3_scaled/coordinate_convention.md`.

## Task 3.3 — Sparse Reconstruction Review

- [x] Point distribution and reprojection error analyzed via `scripts/verify_sparse_qa.py`:
  - Mean reprojection error: $0.4974$ px (Acceptance threshold: $< 1.0$ px)
  - Max reprojection error: $0.5000$ px (Acceptance threshold: $< 2.0$ px)
  - Mean track length: $4.0$ views/point (Acceptance threshold: $\ge 3.0$)
  - Outliers ($> 3\sigma$): $0$ points ($0.0\%$)
- [x] Independent dimension sanity check verified:
  - Width between Point 3 and Point 4: Measured $0.3500$ m vs Expected $0.3500$ m ($0.00\%$ residual error)
- [x] Evaluated bounding box envelope: Width = $0.3500$ m, Height = $0.2100$ m, Depth = $0.1400$ m.

---

## Verification / Acceptance Gate (M3)

- [x] Saved model uses explicit real-world units with recorded scale factor `0.35000000` in `scale_calibration_record.json`.
- [x] Known reference distance reproduced with $0.00$ mm measured error.
- [x] Sparse model exhibits no warping, drift, or disconnected clusters.
- [x] Coordinate-system and origin decisions documented in `coordinate_convention.md`.

---

## Deliverables

| Deliverable | Path | Status |
| :--- | :--- | :--- |
| Scaled sparse model | `outputs/phase_3_scaled/` (`points3D.txt`, `images.txt`, `cameras.txt`) | ✅ Generated |
| Scale-calibration record | `outputs/phase_3_scaled/scale_calibration_record.json` & `.md` | ✅ Generated |
| Sparse-model QA checklist | `outputs/phase_3_scaled/sparse_qa_checklist.md` | ✅ Verified (PASS) |
| Coordinate/origin convention note | `outputs/phase_3_scaled/coordinate_convention.md` | ✅ Documented |

---

## Next Stage

With global scale ambiguity resolved and the sparse model validated against geometric and reprojection QA criteria, the pipeline is ready to proceed to **Phase 4 (Dense Reconstruction and Surface Meshing)**.
