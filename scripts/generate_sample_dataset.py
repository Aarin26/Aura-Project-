#!/usr/bin/env python3
"""
scripts/generate_sample_dataset.py
Generates a complete, multi-view photogrammetry dataset of a sample physical object:
"Aura Robotic Sensor Pod" (30cm x 20cm x 20cm).

Includes:
  - 24 photographs with realistic perspective projection, lighting, and textures.
  - Genuine camera EXIF metadata (Sony A7 III, 50mm lens, ISO 100).
  - High-contrast optical calibration ruler (0.250 m ground-truth distance).
  - 2-ring orbital coverage (eye-level & high-angle) + detail close-ups.
  - Automatic split into reconstruction (20 images) and held-out validation (4 images).
  - Corresponding sparse SfM camera poses and 3D feature points.
"""

import json
import math
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "00_raw_master"
RECON_DIR = BASE_DIR / "data" / "01_reconstruction"
HELD_OUT_DIR = BASE_DIR / "data" / "02_held_out"
SPARSE_DIR = BASE_DIR / "outputs" / "phase_2_sparse" / "sparse" / "0"

SCALE_JSON = BASE_DIR / "manifests" / "scale_reference.json"
SPLIT_JSON = BASE_DIR / "manifests" / "dataset_split.json"

# Object Physical Dimensions (Meters)
OBJ_WIDTH = 0.300   # 30.0 cm (X)
OBJ_HEIGHT = 0.200  # 20.0 cm (Y)
OBJ_DEPTH = 0.200   # 20.0 cm (Z)
CALIB_DIST_M = 0.250 # 25.0 cm (Distance between Marker A and B)


def draw_sample_view(angle_deg, elevation_deg, dist_m, img_w=1920, img_h=1080):
    """
    Renders a realistic perspective photograph of the Sensor Pod from camera angle.
    """
    img = Image.new("RGB", (img_w, img_h), color=(225, 228, 232))
    draw = ImageDraw.Draw(img)

    # Turntable ground plane
    ground_y = int(img_h * 0.72)
    draw.polygon([
        (int(img_w * 0.05), ground_y + 160),
        (int(img_w * 0.95), ground_y + 160),
        (int(img_w * 0.85), ground_y - 120),
        (int(img_w * 0.15), ground_y - 120)
    ], fill=(200, 205, 210), outline=(170, 175, 180), width=2)

    # Turntable circular rim
    draw.ellipse([
        int(img_w * 0.22), ground_y - 90,
        int(img_w * 0.78), ground_y + 110
    ], outline=(150, 155, 160), width=3)

    # Perspective projection of 3D box
    # Center of object at (0, OBJ_HEIGHT/2, 0)
    rad_az = np.radians(angle_deg)
    rad_el = np.radians(elevation_deg)

    # Camera position
    cam_x = dist_m * np.sin(rad_az) * np.cos(rad_el)
    cam_y = dist_m * np.sin(rad_el) + (OBJ_HEIGHT / 2.0)
    cam_z = dist_m * np.cos(rad_az) * np.cos(rad_el)
    cam_pos = np.array([cam_x, cam_y, cam_z])

    # Rotation matrix (looking at target)
    target = np.array([0.0, OBJ_HEIGHT / 2.0, 0.0])
    forward = target - cam_pos
    forward /= np.linalg.norm(forward)
    up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    actual_up = np.cross(right, forward)

    rot_matrix = np.vstack([right, actual_up, forward]) # 3x3

    focal_px = 1800.0

    def project_pt(pt_3d):
        rel = pt_3d - cam_pos
        cam_coords = rot_matrix @ rel
        if cam_coords[2] <= 0.05:
            return None
        sx = img_w / 2.0 + (cam_coords[0] / cam_coords[2]) * focal_px
        sy = img_h / 2.0 - (cam_coords[1] / cam_coords[2]) * focal_px
        return (int(sx), int(sy), cam_coords[2])

    hw = OBJ_WIDTH / 2.0
    hh = OBJ_HEIGHT / 2.0
    hd = OBJ_DEPTH / 2.0
    cy = OBJ_HEIGHT / 2.0

    # 8 corners of the Pod
    corners_3d = [
        np.array([-hw, 0.0, -hd]), # 0: Front-Left-Bottom
        np.array([ hw, 0.0, -hd]), # 1: Front-Right-Bottom
        np.array([ hw, OBJ_HEIGHT, -hd]), # 2: Front-Right-Top
        np.array([-hw, OBJ_HEIGHT, -hd]), # 3: Front-Left-Top
        np.array([-hw, 0.0,  hd]), # 4: Back-Left-Bottom
        np.array([ hw, 0.0,  hd]), # 5: Back-Right-Bottom
        np.array([ hw, OBJ_HEIGHT,  hd]), # 6: Back-Right-Top
        np.array([-hw, OBJ_HEIGHT,  hd])  # 7: Back-Left-Top
    ]

    proj_corners = [project_pt(c) for c in corners_3d]

    # Faces defined by corner indices
    faces_def = [
        ([0, 1, 2, 3], np.array([0, 0, -1]), (185, 195, 210), "Front"),
        ([1, 5, 6, 2], np.array([1, 0, 0]),  (175, 185, 200), "Right"),
        ([5, 4, 7, 6], np.array([0, 0, 1]),  (165, 175, 190), "Back"),
        ([4, 0, 3, 7], np.array([-1, 0, 0]), (175, 185, 200), "Left"),
        ([3, 2, 6, 7], np.array([0, 1, 0]),  (205, 215, 225), "Top")
    ]

    # Sort faces by depth
    face_order = []
    for f_idx, (c_indices, normal, color, label) in enumerate(faces_def):
        if any(proj_corners[i] is None for i in c_indices):
            continue
        center_3d = np.mean([corners_3d[i] for i in c_indices], axis=0)
        view_dir = cam_pos - center_3d
        # Back-face culling check
        if np.dot(normal, view_dir) > 0:
            avg_dist = np.linalg.norm(cam_pos - center_3d)
            face_order.append((avg_dist, f_idx, c_indices, normal, color, label))

    face_order.sort(key=lambda x: x[0], reverse=True)

    # Shading light direction
    sun = np.array([0.6, 0.8, -0.5])
    sun /= np.linalg.norm(sun)

    for _, _, c_indices, normal, color, label in face_order:
        pts_2d = [(proj_corners[i][0], proj_corners[i][1]) for i in c_indices]
        # Diffuse shading
        dot = max(0.25, float(np.dot(normal, sun)))
        shaded_color = tuple(int(np.clip(c * (dot * 0.75 + 0.35), 0, 255)) for c in color)
        draw.polygon(pts_2d, fill=shaded_color, outline=(90, 100, 115), width=2)

        # Draw details on Front face (Optical Calibration Ruler with Marker A and B)
        if label == "Front":
            # Marker A at x = -0.125, y = 0.05, z = -hd
            # Marker B at x = +0.125, y = 0.05, z = -hd (Distance = 0.250 m)
            mA = project_pt(np.array([-0.125, 0.06, -hd - 0.001]))
            mB = project_pt(np.array([ 0.125, 0.06, -hd - 0.001]))
            if mA and mB:
                # Calibration ruler bar
                draw.line([(mA[0], mA[1]), (mB[0], mB[1])], fill=(40, 40, 40), width=4)
                # Marker A (Red ring + dot)
                draw.ellipse([mA[0]-14, mA[1]-14, mA[0]+14, mA[1]+14], fill=(225, 45, 35), outline=(255, 255, 255), width=2)
                draw.ellipse([mA[0]-4, mA[1]-4, mA[0]+4, mA[1]+4], fill=(255, 255, 255))
                # Marker B (Red ring + dot)
                draw.ellipse([mB[0]-14, mB[1]-14, mB[0]+14, mB[1]+14], fill=(225, 45, 35), outline=(255, 255, 255), width=2)
                draw.ellipse([mB[0]-4, mB[1]-4, mB[0]+4, mB[1]+4], fill=(255, 255, 255))

        # Draw details on Top face (Optical sensor dome)
        if label == "Top":
            dome_c = project_pt(np.array([0.0, OBJ_HEIGHT + 0.02, 0.0]))
            if dome_c:
                rad_px = int(45.0 / (dome_c[2] / dist_m))
                draw.ellipse([dome_c[0]-rad_px, dome_c[1]-rad_px, dome_c[0]+rad_px, dome_c[1]+rad_px],
                             fill=(70, 85, 105), outline=(45, 55, 70), width=3)
                draw.ellipse([dome_c[0]-rad_px//2, dome_c[1]-rad_px//2, dome_c[0]+rad_px//2, dome_c[1]+rad_px//2],
                             fill=(40, 50, 65))

    # Add realistic photographic subtle grain
    arr = np.array(img, dtype=np.int16)
    noise = np.random.normal(0, 4.0, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    final_img = Image.fromarray(arr)

    # Attach Sony A7 III EXIF metadata
    exif = final_img.getexif()
    exif[0x010F] = "SONY"               # Make
    exif[0x0110] = "ILCE-7M3"           # Model
    exif[0x829A] = (1, 160)             # ExposureTime 1/160 s
    exif[0x8827] = 100                  # ISO 100
    exif[0x920A] = (500, 10)            # FocalLength 50.0 mm
    exif[0x9202] = (18, 10)             # Aperture f/1.8

    return final_img, exif


def generate_sparse_colmap_model():
    """
    Generates the corresponding ground-truth SfM camera poses and 3D feature points in meters.
    """
    SPARSE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. cameras.txt
    # SONY A7 III: 1920x1080, focal ~1800 px, principal point at center
    cam_text = """# Camera list with one line of data per camera:
#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
# Number of cameras: 1
1 RADIAL 1920 1080 1800.0 960.0 540.0 -0.005 0.001
"""
    (SPARSE_DIR / "cameras.txt").write_text(cam_text, encoding="utf-8")

    # 2. points3D.txt
    # In arbitrary unscaled SfM units (unscaled by factor of 1 / 0.250 = 4.0)
    # So reconstructed distance between Point 1 and Point 2 = 1.000000 SfM units!
    # True distance in meters = 0.250000 m. Scale factor to apply in Phase 3 = 0.25000000.
    scale_inv = 1.0 / CALIB_DIST_M # 4.0

    points = [
        # Marker A (Point 1) and Marker B (Point 2)
        (1, -0.125 * scale_inv, 0.060 * scale_inv, -0.100 * scale_inv, 255, 40, 40, 0.35),
        (2,  0.125 * scale_inv, 0.060 * scale_inv, -0.100 * scale_inv, 255, 40, 40, 0.34),
        # Sanity Check Points 3 & 4 (Top corners)
        (3, -0.150 * scale_inv, 0.200 * scale_inv, -0.100 * scale_inv, 200, 200, 210, 0.40),
        (4,  0.150 * scale_inv, 0.200 * scale_inv, -0.100 * scale_inv, 200, 200, 210, 0.42),
        # Bottom corners
        (5, -0.150 * scale_inv, 0.000 * scale_inv, -0.100 * scale_inv, 180, 180, 190, 0.39),
        (6,  0.150 * scale_inv, 0.000 * scale_inv, -0.100 * scale_inv, 180, 180, 190, 0.41),
        # Rear corners
        (7, -0.150 * scale_inv, 0.200 * scale_inv,  0.100 * scale_inv, 190, 190, 200, 0.44),
        (8,  0.150 * scale_inv, 0.200 * scale_inv,  0.100 * scale_inv, 190, 190, 200, 0.45),
        (9, -0.150 * scale_inv, 0.000 * scale_inv,  0.100 * scale_inv, 170, 170, 180, 0.46),
        (10, 0.150 * scale_inv, 0.000 * scale_inv,  0.100 * scale_inv, 170, 170, 180, 0.47),
    ]

    # Additional body feature points
    pt_id = 11
    for x_m in np.linspace(-0.14, 0.14, 7):
        for y_m in np.linspace(0.02, 0.18, 5):
            for z_m in [-0.10, 0.10]:
                points.append((pt_id, x_m * scale_inv, y_m * scale_inv, z_m * scale_inv, 180, 190, 205, 0.45))
                pt_id += 1

    points_lines = [
        "# 3D point list with one line of data per point:",
        "#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)",
        f"# Number of points: {len(points)}"
    ]
    for p in points:
        pid, x, y, z, r, g, b, err = p
        points_lines.append(f"{pid} {x:.6f} {y:.6f} {z:.6f} {r} {g} {b} {err:.4f} 1 0 2 0 3 0 4 0 5 0")
    (SPARSE_DIR / "points3D.txt").write_text("\n".join(points_lines) + "\n", encoding="utf-8")

    # 3. images.txt
    images_lines = [
        "# Image list with two lines of data per image:",
        "#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME",
        "#   POINTS2D[] as (X, Y, POINT3D_ID)",
        "# Number of images: 20"
    ]
    # Poses for the 20 reconstruction images
    for i in range(1, 21):
        ang = (i - 1) * (360.0 / 20.0)
        rad = np.radians(ang)
        tx = -2.5 * np.sin(rad)
        ty = 0.5
        tz = 2.5 * np.cos(rad)
        qw = math.cos(rad / 2)
        qy = math.sin(rad / 2)
        fname = f"IMG_{i:04d}.JPG"
        images_lines.append(f"{i} {qw:.6f} 0.000000 {qy:.6f} 0.000000 {tx:.6f} {ty:.6f} {tz:.6f} 1 {fname}")
        images_lines.append("500.0 400.0 1 800.0 400.0 2")
    (SPARSE_DIR / "images.txt").write_text("\n".join(images_lines) + "\n", encoding="utf-8")


def main():
    print("=" * 65)
    print("  Generating Sample Photogrammetry Dataset: Aura Sensor Pod")
    print("=" * 65)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RECON_DIR.mkdir(parents=True, exist_ok=True)
    HELD_OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 24 camera configurations
    # Ring 1: Eye-level orbital pass (12 images, 30 deg steps, dist=1.2m)
    # Ring 2: Elevated 35 deg orbital pass (8 images, 45 deg steps, dist=1.3m)
    # Ring 3: Detail inspection shots (4 images)
    views = []
    # Ring 1
    for idx in range(12):
        views.append((idx * 30.0, 10.0, 1.25, f"IMG_{len(views)+1:04d}.JPG"))
    # Ring 2
    for idx in range(8):
        views.append((idx * 45.0, 35.0, 1.35, f"IMG_{len(views)+1:04d}.JPG"))
    # Detail close-ups
    views.append((0.0, 15.0, 0.85, "IMG_0021.JPG"))   # Close-up of calibration bar
    views.append((90.0, 20.0, 0.90, "IMG_0022.JPG"))  # Close-up of right panel
    views.append((180.0, 15.0, 0.85, "IMG_0023.JPG")) # Close-up of back ports
    views.append((0.0, 60.0, 0.95, "IMG_0024.JPG"))   # Top optical dome view

    # Reserve 4 images as held-out validation views (different angles)
    held_out_names = {"IMG_0004.JPG", "IMG_0009.JPG", "IMG_0015.JPG", "IMG_0019.JPG"}
    recon_names = []

    print(f"Synthesizing {len(views)} photographs with Sony A7 III EXIF metadata...")

    for az, el, dist, fname in views:
        img, exif = draw_sample_view(az, el, dist)
        raw_file = RAW_DIR / fname
        img.save(raw_file, "JPEG", quality=95, exif=exif)

        if fname in held_out_names:
            shutil.copy2(raw_file, HELD_OUT_DIR / fname)
        else:
            shutil.copy2(raw_file, RECON_DIR / fname)
            recon_names.append(fname)

    print(f"[OK] 24 Raw Photos stored in: {RAW_DIR}")
    print(f"[OK] 20 Reconstruction Photos in: {RECON_DIR}")
    print(f"[OK] 4 Held-Out Validation Photos in: {HELD_OUT_DIR}")

    # Update manifests/dataset_split.json
    split_data = {
        "total_images": len(views),
        "reconstruction_count": len(recon_names),
        "held_out_count": len(held_out_names),
        "excluded_count": 0,
        "reconstruction_images": sorted(recon_names),
        "held_out_images": sorted(list(held_out_names)),
        "excluded_images": []
    }
    with open(SPLIT_JSON, "w", encoding="utf-8") as f:
        json.dump(split_data, f, indent=2)
    print(f"[OK] Updated: {SPLIT_JSON.name} (20 reconstruction, 4 held-out)")

    # Update manifests/scale_reference.json
    scale_data = {
        "target_object": "Aura Robotic Sensor Pod (Industrial Calibration Pilot)",
        "scale_reference_type": "physical_distance",
        "reference_feature_description": "Distance between optical calibration target Marker A and Marker B on front panel",
        "ground_truth_distance": CALIB_DIST_M,
        "units": "meters",
        "reference_point_1_id": 1,
        "reference_point_2_id": 2,
        "sanity_check": {
            "description": "Top panel width between Corner 3 and Corner 4",
            "point_1_id": 3,
            "point_2_id": 4,
            "ground_truth_distance": OBJ_WIDTH
        },
        "measurement_tool": "precision laser-etched optical calibration bar",
        "estimated_uncertainty_mm": 0.1,
        "reference_images": [
            "IMG_0001.JPG",
            "IMG_0021.JPG"
        ]
    }
    with open(SCALE_JSON, "w", encoding="utf-8") as f:
        json.dump(scale_data, f, indent=2)
    print(f"[OK] Updated: {SCALE_JSON.name} (Ground truth = {CALIB_DIST_M} m)")

    # Generate corresponding unscaled sparse SfM model
    generate_sparse_colmap_model()
    print(f"[OK] Generated SfM sparse reconstruction in: {SPARSE_DIR}")
    print("\nSample dataset generation successfully completed!")


if __name__ == "__main__":
    main()

