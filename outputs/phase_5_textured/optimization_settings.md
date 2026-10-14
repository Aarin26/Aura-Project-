# Optimization Settings - Phase 5

- **Run Date:** 2026-10-14T21:47:03.884445
- **Asset Candidate:** `mesh_textured.obj`

## Polygon Count Evolution

| Pipeline Stage | Triangle Count | Vertex Count | Reduction Ratio |
| :--- | :--- | :--- | :--- |
| Raw Mesh (Phase 4) | 214 | 109 | Baseline (100%) |
| Cleaned Mesh (Task 5.1) | 214 | 109 | 100.0% |
| Optimized Candidate (Task 5.2) | 180 | 92 | 84.1% |

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
- **Dimensions:** Width = 0.3552 m, Height = 0.2141 m, Depth = 0.1449 m
