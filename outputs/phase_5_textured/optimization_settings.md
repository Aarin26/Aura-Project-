# Optimization Settings - Phase 5

> **Superseded for the current deliverable.** The current reconstruction uses a 128³ visual-hull grid and is not the 112-triangle Phase 5 mesh described below. See `outputs/phase_7_export/reconstruction_report.md` for current measured counts.

- **Run Date:** 2026-10-14T22:48:25.641564
- **Asset Candidate:** `mesh_textured.obj`

## Polygon Count Evolution

| Pipeline Stage | Triangle Count | Vertex Count | Reduction Ratio |
| :--- | :--- | :--- | :--- |
| Raw Mesh (Phase 4) | 112 | 58 | Baseline (100%) |
| Cleaned Mesh (Task 5.1) | 112 | 58 | 100.0% |
| Optimized Candidate (Task 5.2) | 112 | 58 | 100.0% |

## Decimation Configuration

- **Algorithm:** Quadric Edge Collapse Decimation
- **Target Budget:** ~200 triangles (suitable for real-time mobile AR/VR prop)
- **Boundary Preservation:** Enabled (silhouette boundaries protected)
- **Topology Invariant:** Manifold topology enforced; 0 duplicate or non-manifold faces

## UV Layout & Texture Settings

- **UV Mapping Method:** Normalized Non-Overlapping Atlas Mapping
- **Texture Resolution:** 2048 x 2048 (4.19 MP)
- **Color Space:** sRGB, 8-bit per channel PNG
- **Material Definition:** Standard Wavefront MTL (`Material_Diffuse`)
- **Texture Path:** `textures/texture_diffuse.png` (relative path enforced)

## Origin & Placement Specification

- **Origin ($0,0,0$):** Set to bottom-center of the object bounding box ($Y_{\min} = 0.0$)
- **Dimensions:** Width = 0.3552 m, Height = 0.3065 m, Depth = 0.2000 m
