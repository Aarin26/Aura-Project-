# Casual Smartphone Capture Guide: Real-World 3D Reconstruction

This guide explains how to capture real-world physical objects using **any standard smartphone** (iPhone, Samsung Galaxy, Google Pixel, OnePlus, etc.) without needing a professional photoshoot, studio lighting, or expensive hardware.

---

## 1. How Our Automated Pipeline Handles Casual Smartphone Photos

Smartphone cameras introduce unique variables that traditional photogrammetry often struggles with. Our pipeline includes automated preprocessing to solve these hurdles:

| Challenge | What Happens in Raw Mobile Photos | How Our Pipeline Solves It |
| :--- | :--- | :--- |
| **Portrait vs. Landscape Tilt** | Phones write EXIF tag 274; raw pixel buffers are often stored sideways or upside-down. | `scripts/preprocess_casual_photos.py` detects EXIF tags and **physically transposes pixels upright** so all tools see properly oriented images. |
| **Hand Shake & Motion Blur** | Handheld shots in indoor ambient lighting can be blurry or out of focus. | Computes **Laplacian variance $\mathrm{Var}(\nabla^2 I)$** sharpness. Photos below the threshold (< 50.0) are automatically isolated into `data/03_preprocessed/excluded_blurry/`. |
| **Massive Megapixels (OOM)** | Modern phones shoot 12MP, 48MP, or 108MP, which can crash GPU/CPU memory during dense matching. | Automatically downscales oversized photos to **2560px max edge** using high-fidelity **Lanczos resampling**, preserving details while preventing memory crashes. |
| **Multi-Lens Cameras & Zoom** | Phones switch between Ultra-wide, Wide, and Telephoto lenses or pinch-zoom. | Inspects EXIF focal lengths. When multiple lenses are detected, it configures COLMAP with `--ImageReader.single_camera 0` so each lens is calibrated independently. |
| **Cluttered Room Background** | Handheld photos contain desk clutter, room walls, and furniture. | Enables **guided feature matching** (`--SiftMatching.guided_matching 1`) and extracts 8,192 SIFT keypoints, prioritizing the parallax of the central target object. |
| **Dataset Partitioning** | Manually separating photos into reconstruction and validation is tedious. | Automatically samples **85% reconstruction** and **15% held-out test photos** evenly spaced around the object. |

---

## 2. Best Practices for Handheld Mobile Shooting

You do **not** need a studio lightbox or a motorized turntable. Just follow these simple rules:

### A. The Orbital Walk-Around Pattern
- Place the object on a stable surface (a table, desk, or floor).
- Walk around the object in circles, keeping your distance relatively consistent (~0.5 to 1.5 meters depending on object size):
  - **Ring 1 (Eye Level):** Circle the object at ~0° elevation, taking a photo every 15–20° (around 18–24 photos).
  - **Ring 2 (High Angle):** Circle the object again looking down at ~45° elevation (another 12–18 photos).
  - **Top & Details (Optional):** Take 3–5 shots looking directly from above or close-ups of complex geometry.

```
       [Top Down: 3-5 shots]
              \
   [Ring 2: 45° angle, 12-18 shots]
              \
 [Ring 1: Eye-level, 18-24 shots] ---> [OBJECT ON TABLE]
```

### B. The 70–80% Overlap Rule
- Step, take a picture, step, take a picture.
- Every photo must share at least **70% to 80% visual surface area** with the previous photo. This ensures SIFT feature matching can link keypoints across views.

### C. Lighting & Surface Texture
- **Lighting:** Ordinary diffuse room light or daylight near a window works best. Avoid direct harsh flashlights or single spotlighting that casts rapidly moving hard shadows when you move.
- **Surfaces:**
  - **Great Objects:** Shoes, pottery, toys, wood carvings, backpacks, electronic enclosures, rocks, statues, cardboard packages.
  - **Hard Surfaces:** Completely transparent glass, pure chrome/mirrors, or featureless glossy white plastic. (If scanning a featureless object, place a patterned sheet of paper or sticky note underneath it).

### D. Ground Truth Scale Reference
- Place a small ruler, coin, or credit card next to the object for at least 2–3 photos.
- Measure the distance between two distinct points (e.g., ruler markings = `0.150` m or credit card width = `0.0856` m).
- Enter this number into `manifests/scale_reference.json`.

---

## 3. Simple Step-by-Step Execution Workflow

### Step 1: Copy Raw Photos
Transfer your raw smartphone photos from your phone to:
```
data/00_raw_master/
```

### Step 2: Record Scale Measurement
Open `manifests/scale_reference.json` and set your real-world measurement:
```json
{
  "ground_truth_distance": 0.150,
  "units": "meters",
  "method": "Ruler measurement between calibration markings"
}
```

### Step 3: Run the Automated Pipeline
Open your terminal in the project directory and run:
```bash
python scripts/run_pipeline.py
```
This single command automatically:
1. Audits your dataset and calculates image sharpness checksums (`Phase 0`).
2. Transposes rotations, culls blurry photos, downscales oversized images, and partitions 85/15 splits (`Phase 2 Preprocessing`).
3. Verifies SfM pre-flight parameters (`Phase 2 SfM`).
4. Calibrates true metric physical scale (`Phase 3`).
5. Reconstructs dense point clouds and surface meshes (`Phase 4`).
6. Cleans, decimates, unwraps UVs, and bakes textures (`Phase 5`).
7. Validates the candidate 3D mesh against unseen held-out angles (`Phase 6`).
8. Exports a production-ready `.glb` and `.obj` package (`Phase 7`).

### Step 4: Import into Blender or Game Engine
- In **Blender**:
  - Open Blender.
  - Go to `File > Import > glTF 2.0 (.glb/.gltf)` (or `File > Import > Wavefront (.obj)`).
  - Select `outputs/phase_7_export/asset.glb`.
  - Press `Z` and choose **Material Preview** to view the textured 3D asset in full color.
- In **Unity / Unreal**:
  - Drag `outputs/phase_7_export/asset.glb` directly into your Project Assets folder.

