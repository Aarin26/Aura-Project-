#!/usr/bin/env python3
"""
Generates a representative COLMAP sparse model (TXT format) for testing and pipeline validation.
Simulates a pilot object with 8 camera positions and feature points forming a 3D bounding geometry
with known reference markers.
"""

import math
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_2_sparse" / "sparse" / "0"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Write cameras.txt
cameras_content = """# Camera list with one line of data per camera:
#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
# Number of cameras: 1
1 RADIAL 4032 3024 3200 2016 1512 -0.01 0.005
"""

# 2. Generate points3D.txt (in arbitrary SfM units)
# Point 1 and Point 2 are the known reference endpoints (e.g. ruler ends or marker points)
# Point 1: (-0.50, -0.30, -0.20)
# Point 2: (+0.50, -0.30, -0.20) -> Distance in SfM units = 1.0000
points = [
    (1, -0.50, -0.30, -0.20, 255, 0, 0, 0.42),    # Reference Point 1 (Marker A)
    (2, 0.50, -0.30, -0.20, 255, 0, 0, 0.45),     # Reference Point 2 (Marker B)
    (3, -0.50, 0.30, -0.20, 200, 200, 200, 0.38), # Sanity Check Point 3 (Corner C)
    (4, 0.50, 0.30, -0.20, 200, 200, 200, 0.41),  # Sanity Check Point 4 (Corner D)
    (5, -0.50, -0.30, 0.20, 180, 180, 180, 0.49),
    (6, 0.50, -0.30, 0.20, 180, 180, 180, 0.47),
    (7, -0.50, 0.30, 0.20, 190, 190, 190, 0.44),
    (8, 0.50, 0.30, 0.20, 190, 190, 190, 0.43),
]

# Add additional surface feature points
pt_id = 9
for ix in range(-4, 5):
    for iy in range(-3, 4):
        for iz in range(-2, 3, 2):
            x = ix * 0.12 + 0.01 * (iy % 2)
            y = iy * 0.09
            z = iz * 0.10
            points.append((pt_id, x, y, z, 150 + ix * 10, 150 + iy * 10, 160, 0.50))
            pt_id += 1

points_lines = [
    "# 3D point list with one line of data per point:",
    "#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)",
    f"# Number of points: {len(points)}"
]

for p in points:
    pid, x, y, z, r, g, b, err = p
    points_lines.append(f"{pid} {x:.6f} {y:.6f} {z:.6f} {r} {g} {b} {err:.4f} 1 0 2 0 3 0 4 0")

points_content = "\n".join(points_lines) + "\n"

# 3. Generate images.txt (8 circular camera viewpoints looking inward)
images_lines = [
    "# Image list with two lines of data per image:",
    "#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME",
    "#   POINTS2D[] as (X, Y, POINT3D_ID)",
    "# Number of images: 8"
]

radius = 2.2
num_cams = 8
for i in range(num_cams):
    img_id = i + 1
    angle = (2 * math.pi * i) / num_cams
    tx = -radius * math.sin(angle)
    ty = 0.4
    tz = radius * math.cos(angle)
    # Simple approximate rotation quaternion facing origin
    qw = math.cos(angle / 2)
    qy = math.sin(angle / 2)
    qx = 0.0
    qz = 0.0
    name = f"DSC_{img_id:04d}.JPG"
    images_lines.append(f"{img_id} {qw:.6f} {qx:.6f} {qy:.6f} {qz:.6f} {tx:.6f} {ty:.6f} {tz:.6f} 1 {name}")
    images_lines.append("100.0 150.0 1 200.0 250.0 2")

images_content = "\n".join(images_lines) + "\n"

# Write out files
(OUTPUT_DIR / "cameras.txt").write_text(cameras_content, encoding="utf-8")
(OUTPUT_DIR / "points3D.txt").write_text(points_content, encoding="utf-8")
(OUTPUT_DIR / "images.txt").write_text(images_content, encoding="utf-8")

print(f"[OK] Generated reference sparse model in: {OUTPUT_DIR}")
print(f"     Cameras: 1, Images: {num_cams}, Points: {len(points)}")
print("     Reference endpoints: Point 1 and Point 2 (Distance in SfM units = 1.0000)")

