# Coordinate System and Origin Convention - Phase 3

**Author:** Geometry / Calibration Lead  
**Date:** 2026-10-14  
**Project:** Aura-Project- Photogrammetry Pipeline  

---

## 1. Unit System

| Setting | Value |
| :--- | :--- |
| **Standard Units** | **Meters (m)** |
| Scale Factor Applied | 0.35000000 |
| Equivalent Conversion | 1 COLMAP unit = 0.3500 meters |
| Scale Reference Error | 0.000000 m (Residual error < 0.1 mm) |

---

## 2. Global Coordinate Conventions (COLMAP -> Target Engine)

COLMAP operates in a right-handed coordinate system. For 3D game engines (Unity / Unreal), coordinate mapping is standardized as follows:

| Axis | Photogrammetry / Model Orientation | Target Engine (Unity) | Target Engine (Unreal) |
| :--- | :--- | :--- | :--- |
| **+X** | Object Width (Right) | +X (Right) | +Y (Right) |
| **+Y** | Object Height (Up) | +Y (Up) | +Z (Up) |
| **+Z** | Object Depth (Forward) | +Z (Forward) | +X (Forward) |
| **Handedness** | Right-handed | Left-handed | Left-handed |

> [!NOTE]
> During Blender asset preparation and glTF 2.0 export (Phase 5 / Phase 7), standard glTF conversion maintains Right-handed Y-up (compatible with Unity glTF importers). For Unreal FBX, an explicit axis conversion (+X forward, +Z up) is handled in Blender export settings.

---

## 3. Origin Point Convention

| Feature | Convention |
| :--- | :--- |
| **Provisional Origin (Phase 3)** | Geometric centroid of the reconstructed point cloud $(0.0, 0.0, 0.0)$ |
| **Final Asset Origin (Phase 5/7)** | Bottom-center of the object bounding box ($Y_{\min} = 0.0$) so the asset rests cleanly on virtual ground planes in AR/VR and game engines |
| **Scale Invariance** | All camera translation vectors and 3D point positions are verified to be in exact 1:1 metric scale |

---

## 4. Verification Check

- [x] Camera translation vectors in `images.txt` are scaled identically to `points3D.txt`
- [x] Bounding box dimensions match physical real-world object measurements:
  - Width: $0.3500$ m
  - Height: $0.2100$ m
  - Depth: $0.1400$ m
- [x] No axis inversion or non-uniform scaling detected
