# Dimensions and Origin Note - Phase 7

- **Final Asset Deliverable:** `asset.glb`
- **Package Generation Date:** 2026-10-15T03:13:00.243387
- **File Size:** 4.59 MB (Embedded texture atlas)

## 1. Verified Metric Real-World Dimensions

| Dimension Axis | Size (Meters) | Size (Centimeters) | Ground Truth Target |
| :--- | :--- | :--- | :--- |
| **X (Width)** | **0.1439 m** | 14.4 cm | Measured from exported mesh |
| **Y (Height)** | **0.2790 m** | 27.9 cm | Measured from exported mesh |
| **Z (Depth)** | **0.1387 m** | 13.9 cm | Measured from exported mesh |

## 2. Origin & Pivot Point Convention

- **Origin Coordinate (0, 0, 0):** Positioned at the **bottom-center** of the object's bounding envelope.
- **Bounding Box Minimum:** `[-0.0699, 0.0000, -0.0693]` m
- **Bounding Box Maximum:** `[0.0739, 0.2790, 0.0693]` m
- **Engine Grounding:** When placed at $(0, 0, 0)$ in Unity or Unreal, the asset rests perfectly flush on flat ground/floors without sinking or floating.

## 3. Orientation & Coordinate Axis Conventions

| System | Forward Axis | Up Axis | Scale Setting on Import |
| :--- | :--- | :--- | :--- |
| **glTF Standard (asset.glb)** | +Z Forward | +Y Up | 1.0 (Metric meter standard) |
| **Unity Engine** | +Z Forward | +Y Up | Scale Factor = `1.0` (Do NOT rescale) |
| **Unreal Engine** | +X Forward | +Z Up | Uniform Import Scale = `100.0` (Converts m to cm) |
