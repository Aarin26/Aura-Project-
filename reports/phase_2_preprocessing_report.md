# Phase 2: Casual Photo Preprocessing & Normalization Report

- **Generated:** 2026-10-14 22:48:15
- **Total Source Images:** 24
- **Max Allowed Dimension:** 2560 px
- **Sharpness / Blur Threshold:** 50.0 (Laplacian variance)

## Camera & Lens Profiles Detected

- Single lens profile: `SONY ILCE-7M3 (50.0mm)`

- `SONY ILCE-7M3 (50.0mm)`: 24 images

## Image Inspection & Normalization Table

| Filename | Original Size | Clean Size | Auto-Orientation | Sharpness Score | Status | Split |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `IMG_0001.JPG` | 1920x1080 | 1920x1080 | Already upright | 232.2 | Sharp | Reconstruction |
| `IMG_0002.JPG` | 1920x1080 | 1920x1080 | Already upright | 245.4 | Sharp | Reconstruction |
| `IMG_0003.JPG` | 1920x1080 | 1920x1080 | Already upright | 244.6 | Sharp | Reconstruction |
| `IMG_0004.JPG` | 1920x1080 | 1920x1080 | Already upright | 231.3 | Sharp | Held-Out |
| `IMG_0005.JPG` | 1920x1080 | 1920x1080 | Already upright | 265.9 | Sharp | Reconstruction |
| `IMG_0006.JPG` | 1920x1080 | 1920x1080 | Already upright | 268.6 | Sharp | Reconstruction |
| `IMG_0007.JPG` | 1920x1080 | 1920x1080 | Already upright | 253.4 | Sharp | Reconstruction |
| `IMG_0008.JPG` | 1920x1080 | 1920x1080 | Already upright | 267.0 | Sharp | Reconstruction |
| `IMG_0009.JPG` | 1920x1080 | 1920x1080 | Already upright | 262.8 | Sharp | Reconstruction |
| `IMG_0010.JPG` | 1920x1080 | 1920x1080 | Already upright | 229.6 | Sharp | Held-Out |
| `IMG_0011.JPG` | 1920x1080 | 1920x1080 | Already upright | 241.7 | Sharp | Reconstruction |
| `IMG_0012.JPG` | 1920x1080 | 1920x1080 | Already upright | 243.2 | Sharp | Reconstruction |
| `IMG_0013.JPG` | 1920x1080 | 1920x1080 | Already upright | 235.0 | Sharp | Reconstruction |
| `IMG_0014.JPG` | 1920x1080 | 1920x1080 | Already upright | 268.7 | Sharp | Reconstruction |
| `IMG_0015.JPG` | 1920x1080 | 1920x1080 | Already upright | 233.7 | Sharp | Reconstruction |
| `IMG_0016.JPG` | 1920x1080 | 1920x1080 | Already upright | 295.3 | Sharp | Held-Out |
| `IMG_0017.JPG` | 1920x1080 | 1920x1080 | Already upright | 255.5 | Sharp | Reconstruction |
| `IMG_0018.JPG` | 1920x1080 | 1920x1080 | Already upright | 292.8 | Sharp | Reconstruction |
| `IMG_0019.JPG` | 1920x1080 | 1920x1080 | Already upright | 233.6 | Sharp | Reconstruction |
| `IMG_0020.JPG` | 1920x1080 | 1920x1080 | Already upright | 266.9 | Sharp | Reconstruction |
| `IMG_0021.JPG` | 1920x1080 | 1920x1080 | Already upright | 252.5 | Sharp | Reconstruction |
| `IMG_0022.JPG` | 1920x1080 | 1920x1080 | Already upright | 249.7 | Sharp | Held-Out |
| `IMG_0023.JPG` | 1920x1080 | 1920x1080 | Already upright | 279.0 | Sharp | Reconstruction |
| `IMG_0024.JPG` | 1920x1080 | 1920x1080 | Already upright | 252.9 | Sharp | Reconstruction |

## Recommended Next Steps

1. Check any images marked `BLURRY` or `EXCLUDED (BLUR)`.
2. If important surfaces were excluded, take 1-2 steady replacement shots.
3. Run Phase 2 SfM via `python scripts/run_colmap_sfm.py` or master `python scripts/run_pipeline.py`.
