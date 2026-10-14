# Dimensions and Origin Note - Phase 7

- **Final Asset Deliverable:** `asset.glb`
- **Package Generation Date:** 2026-10-14T21:58:27.641437
- **File Size:** 8.16 MB (Embedded texture atlas)

## 1. Verified Metric Real-World Dimensions

| Dimension Axis | Size (Meters) | Size (Centimeters) | Ground Truth Target |
| :--- | :--- | :--- | :--- |
| **X (Width)** | **0.3552 m** | 35.5 cm | 0.3500 m (35.0 cm) |
| **Y (Height)** | **0.2141 m** | 21.4 cm | 0.2100 m (21.0 cm) |
| **Z (Depth)** | **0.1449 m** | 14.5 cm | 0.1400 m (14.0 cm) |

## 2. Origin & Pivot Point Convention

- **Origin Coordinate (0, 0, 0):** Positioned at the **bottom-center** of the object's bounding envelope.
- **Bounding Box Minimum:** `[-0.1776, 0.0000, -0.0724]` m
- **Bounding Box Maximum:** `[0.1776, 0.2141, 0.0724]` m
- **Engine Grounding:** When placed at $(0, 0, 0)$ in Unity or Unreal, the asset rests perfectly flush on flat ground/floors without sinking or floating.

## 3. Orientation & Coordinate Axis Conventions

| System | Forward Axis | Up Axis | Scale Setting on Import |
| :--- | :--- | :--- | :--- |
| **glTF Standard (asset.glb)** | +Z Forward | +Y Up | 1.0 (Metric meter standard) |
| **Unity Engine** | +Z Forward | +Y Up | Scale Factor = `1.0` (Do NOT rescale) |
| **Unreal Engine** | +X Forward | +Z Up | Uniform Import Scale = `100.0` (Converts m to cm) |
