# Scale Calibration Record - Phase 3

- **Calibration Date:** 2026-10-14T22:10:25.028339
- **Target Object:** Aura Robotic Sensor Pod (Industrial Calibration Pilot)
- **Measurement Tool:** precision laser-etched optical calibration bar
- **Estimated Uncertainty:** ±0.1 mm

## Reference Calibration

| Parameter | Value |
| :--- | :--- |
| Reference Point 1 (ID) | Point 1 |
| Reference Point 2 (ID) | Point 2 |
| Unscaled Distance (SfM units) | 1.000000 |
| Ground Truth Physical Distance | 0.250000 meters |
| **Applied Scale Factor** | **0.25000000** |
| Verified Reconstructed Distance | 0.250000 meters |
| Calibration Error | 0.00000000 m |

## Dimensions in Real-World Scale (Meters)

| Axis | Dimension (meters) |
| :--- | :--- |
| Width (X) | 0.3000 m |
| Height (Y) | 0.2000 m |
| Depth (Z) | 0.2000 m |

## Independent Sanity Check

- **Feature:** Top panel width between Corner 3 and Corner 4 (Between Point 3 and Point 4)
- **Expected Distance:** 0.3000 m
- **Measured Distance:** 0.3000 m
- **Residual Error:** 0.000000 m (0.00%)
- **Tolerance Check:** PASSED (< 1% error)

## Acceptance Sign-Off

- [x] Global scale ambiguity resolved with documented real-world units (meters)
- [x] Point cloud and camera translations scaled consistently
- [x] Sanity check dimension verified within agreed tolerance
- [x] Coordinate convention documented in `coordinate_convention.md`
