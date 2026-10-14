# Known Defect List - Phase 5 Candidate Asset

- **Evaluation Date:** 2026-10-14T22:48:25.642572
- **Candidate Asset:** `mesh_textured.obj`
- **Status:** Ready for Phase 6 Held-Out Validation

## 1. Accepted Geometry Defects

| ID | Surface / Region | Defect Type | Severity | Rationale for Acceptance |
| :--- | :--- | :--- | :--- | :--- |
| G-01 | Underside (Base) | Open Boundary | Medium | Object rested on tabletop surface during multi-view capture. Bottom face is invisible when asset is grounded in engine. |
| G-02 | Edge Chamfers (<1mm) | Simplified Profile | Low | Minor sub-millimeter edge softening due to decimation budget; imperceptible at target viewing distance ($> 1$ m). |

## 2. Accepted Texture & UV Defects

| ID | Surface / Region | Defect Type | Severity | Rationale for Acceptance |
| :--- | :--- | :--- | :--- | :--- |
| T-01 | UV Seam at Back Corner | Seam Boundary | Low | Placed along rear edge to minimize visibility from primary frontal viewing angles. |
| T-02 | Lighting Variations | Ambient Luminance Gradient | Low | Normalized during texture baking; will receive dynamic engine lighting in Unity/Unreal. |

## 3. M5 Quality Gate Sign-Off

- [x] Zero floating artifacts or unreferenced geometry remaining.
- [x] Decimated mesh maintains exact silhouette of raw Phase 4 geometry.
- [x] Relative texture paths resolve cleanly without broken links.
- [x] Real-world scale (meters) and bottom-center origin verified.
- [x] Human inspection preview render generated (`preview_render.png`).
