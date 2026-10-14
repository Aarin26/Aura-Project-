# 3D Photogrammetry Reconstruction Pipeline

This repository implements the multi-view photogrammetry reconstruction pipeline outlined in the build plan.

## Directory Structure

```
Aura-Project-/
├── data/
│   ├── 00_raw_master/           # Immutable original photos (read-only master copy)
│   ├── 01_reconstruction/       # Images accepted for SfM & MVS reconstruction
│   ├── 02_held_out/             # Reserved validation images (never seen during build)
│   └── 03_preprocessed/         # Optional undistorted/preprocessed images
├── docs/                        # Build plans, phase checklists, and specifications
│   └── build_plan.md
├── manifests/                   # Image checksums, split definitions, and run manifests
│   ├── source_manifest.csv
│   ├── dataset_split.json
│   └── scale_reference.json
├── reports/                     # Quality audits, phase verification reports, logs
│   └── phase_0_dataset_audit.md
├── scripts/                     # Automation utilities for audit, SfM, scaling, QA
│   └── audit_dataset.py
└── outputs/                     # Pipeline stage deliverables
    ├── phase_1_baseline/
    ├── phase_2_sparse/
    ├── phase_3_scaled/
    ├── phase_4_dense/
    ├── phase_5_textured/
    ├── phase_6_validation/
    └── phase_7_export/
```

## Phases Overview
- **Phase 0: Dataset Audit & Ground Truth** (Current Phase)
- **Phase 1: Environment Setup & Baseline Reconstruction**
- **Phase 2: Preprocessing, Feature Matching & SfM**
- **Phase 3: Scale Calibration & Sparse QA Gate**
- **Phase 4: Dense Reconstruction & Surface Meshing**
- **Phase 5: Mesh Cleanup, Optimization, UVs & Texturing**
- **Phase 6: Held-out Validation**
- **Phase 7: Export & Engine Handoff**

