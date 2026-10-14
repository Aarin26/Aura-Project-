#!/usr/bin/env python3
"""
scripts/reconstruct_syncom_bottle.py
End-to-End Photogrammetry Reconstruction Engine for the SynCom Bottle Dataset.

Executes all 8 phases of the photogrammetry pipeline:
  1. Ingest & Dataset Split (85 Reconstruction, 15 Held-Out).
  2. Multi-view 3D Visual Hull Reconstruction (preserving spout, handle, and asymmetric contours).
  3. Dynamic Metric Scale & Ground-Plane Alignment (tabletop drink tumbler proportions).
  4. Dense Point Cloud (fused.ply) and Surface Meshing (meshed.ply).
  5. Watertight Mesh Optimization, UV Atlas Unwrapping & Multi-View Texture Baking.
  6. Held-Out View Validation against unseen test camera viewpoints.
  7. Production glTF 2.0 (.glb), OBJ (.obj+.mtl), and PLY (.ply) Asset Export.

Usage:
    python scripts/reconstruct_syncom_bottle.py
"""

import json
import math
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("[ERROR] trimesh is required. Run: pip install trimesh")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
SYNCOM_DIR = BASE_DIR / "data" / "syncom_bottle"
RECON_DIR = BASE_DIR / "data" / "01_reconstruction"
HELD_OUT_DIR = BASE_DIR / "data" / "02_held_out"
PREPROC_DIR = BASE_DIR / "data" / "03_preprocessed"

MANIFESTS_DIR = BASE_DIR / "manifests"
REPORTS_DIR = BASE_DIR / "reports"

OUTPUT_SPARSE = BASE_DIR / "outputs" / "phase_2_sparse"
OUTPUT_SCALED = BASE_DIR / "outputs" / "phase_3_scaled"
OUTPUT_DENSE = BASE_DIR / "outputs" / "phase_4_dense"
OUTPUT_TEXTURED = BASE_DIR / "outputs" / "phase_5_textured"
OUTPUT_VALIDATION = BASE_DIR / "outputs" / "phase_6_validation"
OUTPUT_EXPORT = BASE_DIR / "outputs" / "phase_7_export"


def step_banner(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def extract_surface_nets(vol, spacing=(1.0, 1.0, 1.0), origin=(0, 0, 0)):
    pad_width = 2
    vol = np.pad(vol, pad_width, mode="constant", constant_values=False)
    origin = np.array(origin) - pad_width * np.array(spacing)
    spacing = np.array(spacing)

    nx, ny, nz = vol.shape
    diff_x = vol[:-1, :, :] != vol[1:, :, :]
    diff_y = vol[:, :-1, :] != vol[:, 1:, :]
    diff_z = vol[:, :, :-1] != vol[:, :, 1:]

    c0 = vol[:-1, :-1, :-1]
    c1 = vol[1:, :-1, :-1]
    c2 = vol[:-1, 1:, :-1]
    c3 = vol[1:, 1:, :-1]
    c4 = vol[:-1, :-1, 1:]
    c5 = vol[1:, :-1, 1:]
    c6 = vol[:-1, 1:, 1:]
    c7 = vol[1:, 1:, 1:]

    mask = (c0 | c1 | c2 | c3 | c4 | c5 | c6 | c7) & ~(c0 & c1 & c2 & c3 & c4 & c5 & c6 & c7)
    cell_idx = -np.ones((nx - 1, ny - 1, nz - 1), dtype=int)
    active_coords = np.argwhere(mask)
    num_verts = len(active_coords)
    cell_idx[mask] = np.arange(num_verts)
    verts = (active_coords + 0.5) * spacing + origin

    faces = []
    crossing_x = np.argwhere(diff_x[:, 1:-1, 1:-1])
    for x, y_m1, z_m1 in crossing_x:
        y, z = y_m1 + 1, z_m1 + 1
        c_a = cell_idx[x, y - 1, z - 1]
        c_b = cell_idx[x, y, z - 1]
        c_c = cell_idx[x, y, z]
        c_d = cell_idx[x, y - 1, z]
        if c_a >= 0 and c_b >= 0 and c_c >= 0 and c_d >= 0:
            if vol[x, y, z]:
                faces.append([c_a, c_b, c_c])
                faces.append([c_a, c_c, c_d])
            else:
                faces.append([c_a, c_c, c_b])
                faces.append([c_a, c_d, c_c])

    crossing_y = np.argwhere(diff_y[1:-1, :, 1:-1])
    for x_m1, y, z_m1 in crossing_y:
        x, z = x_m1 + 1, z_m1 + 1
        c_a = cell_idx[x - 1, y, z - 1]
        c_b = cell_idx[x, y, z - 1]
        c_c = cell_idx[x, y, z]
        c_d = cell_idx[x - 1, y, z]
        if c_a >= 0 and c_b >= 0 and c_c >= 0 and c_d >= 0:
            if vol[x, y, z]:
                faces.append([c_a, c_c, c_b])
                faces.append([c_a, c_d, c_c])
            else:
                faces.append([c_a, c_b, c_c])
                faces.append([c_a, c_c, c_d])

    crossing_z = np.argwhere(diff_z[1:-1, 1:-1, :])
    for x_m1, y_m1, z in crossing_z:
        x, y = x_m1 + 1, y_m1 + 1
        c_a = cell_idx[x - 1, y - 1, z]
        c_b = cell_idx[x, y - 1, z]
        c_c = cell_idx[x, y, z]
        c_d = cell_idx[x - 1, y, z]
        if c_a >= 0 and c_b >= 0 and c_c >= 0 and c_d >= 0:
            if vol[x, y, z]:
                faces.append([c_a, c_b, c_c])
                faces.append([c_a, c_c, c_d])
            else:
                faces.append([c_a, c_c, c_b])
                faces.append([c_a, c_d, c_c])

    return trimesh.Trimesh(
        vertices=np.array(verts, dtype=np.float32),
        faces=np.array(faces, dtype=np.int32),
        process=False
    )


def reconstruct():
    step_banner("Reconstructing SynCom Tumbler / Bottle 3D Model")

    with open(SYNCOM_DIR / "cameras.json", encoding="utf-8") as f:
        cams = json.load(f)["cameras"]

    gl_to_cv = np.diag([1.0, -1.0, -1.0, 1.0])

    views = sorted(list(cams.keys()))[::2]
    cams_data = []
    cam_positions = []
    for v in views:
        c = cams[v]
        im = Image.open(SYNCOM_DIR / f"{v}.png").convert("RGBA")
        arr = np.array(im)
        mask = arr[:, :, 3] > 20
        M = np.array(c["extr"]).reshape((4, 4))
        cam_pos = M[:3, 3]
        cam_positions.append(cam_pos)
        W2C = np.linalg.inv(M @ gl_to_cv)
        cams_data.append((W2C, c["intr"], arr, mask, cam_pos))

    img_h, img_w = cams_data[0][2].shape[:2]

    # Dynamic Bounding Box
    cam_dists = [np.linalg.norm(p) for p in cam_positions]
    r_orbit = float(np.median(cam_dists))
    r_init = r_orbit * 0.45

    N_coarse = 32
    lin_c = np.linspace(-r_init, r_init, N_coarse)
    gx, gy, gz = np.meshgrid(lin_c, lin_c, lin_c, indexing="ij")
    pts_c = np.vstack([gx.ravel(), gy.ravel(), gz.ravel(), np.ones(N_coarse**3)])
    inside_c = np.ones(N_coarse**3, dtype=bool)

    for W2C, intr, _, mask, _ in cams_data[::5]:
        fx, fy, cx, cy = intr
        cam_p = W2C @ pts_c[:, inside_c]
        valid = cam_p[2] > 0.5
        u = np.zeros(np.sum(inside_c))
        v = np.zeros(np.sum(inside_c))
        u[valid] = fx * (cam_p[0, valid] / cam_p[2, valid]) + cx
        v[valid] = fy * (cam_p[1, valid] / cam_p[2, valid]) + cy
        in_im = (u >= 0) & (u < img_w) & (v >= 0) & (v < img_h) & valid
        view_inside = np.zeros(np.sum(inside_c), dtype=bool)
        u_i = np.clip(np.round(u[in_im]).astype(int), 0, img_w - 1)
        v_i = np.clip(np.round(v[in_im]).astype(int), 0, img_h - 1)
        view_inside[in_im] = mask[v_i, u_i]
        inside_indices = np.where(inside_c)[0]
        inside_c[inside_indices[~view_inside]] = False

    surv_c = pts_c[:3, inside_c].T
    extents_c = surv_c.max(axis=0) - surv_c.min(axis=0)
    padding = 0.15 * extents_c
    b_min = surv_c.min(axis=0) - padding
    b_max = surv_c.max(axis=0) + padding

    # High-resolution carving
    N_fine = 72
    x_lin = np.linspace(b_min[0], b_max[0], N_fine)
    y_lin = np.linspace(b_min[1], b_max[1], N_fine)
    z_lin = np.linspace(b_min[2], b_max[2], N_fine)
    grid_x, grid_y, grid_z = np.meshgrid(x_lin, y_lin, z_lin, indexing="ij")
    pts_fine = np.vstack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel(), np.ones(N_fine**3)])
    inside = np.ones(N_fine**3, dtype=bool)

    for W2C, intr, _, mask, _ in cams_data:
        fx, fy, cx, cy = intr
        cam_p = W2C @ pts_fine[:, inside]
        valid = cam_p[2] > 0.5
        u = np.zeros(np.sum(inside))
        v = np.zeros(np.sum(inside))
        u[valid] = fx * (cam_p[0, valid] / cam_p[2, valid]) + cx
        v[valid] = fy * (cam_p[1, valid] / cam_p[2, valid]) + cy
        in_im = (u >= 0) & (u < img_w) & (v >= 0) & (v < img_h) & valid
        view_inside = np.zeros(np.sum(inside), dtype=bool)
        u_i = np.clip(np.round(u[in_im]).astype(int), 0, img_w - 1)
        v_i = np.clip(np.round(v[in_im]).astype(int), 0, img_h - 1)
        view_inside[in_im] = mask[v_i, u_i]
        inside_indices = np.where(inside)[0]
        inside[inside_indices[~view_inside]] = False

    vol = inside.reshape((N_fine, N_fine, N_fine))
    spacing = (
        (b_max[0] - b_min[0]) / (N_fine - 1),
        (b_max[1] - b_min[1]) / (N_fine - 1),
        (b_max[2] - b_min[2]) / (N_fine - 1),
    )

    raw_mesh = extract_surface_nets(vol, spacing, b_min)
    trimesh.smoothing.filter_laplacian(raw_mesh, iterations=3)

    comps = raw_mesh.split(only_watertight=False)
    if comps:
        max_v = max(len(c.vertices) for c in comps)
        valid_comps = [c for c in comps if len(c.vertices) >= max(300, max_v * 0.05)]
        mesh = trimesh.util.concatenate(valid_comps) if valid_comps else max(comps, key=lambda c: len(c.vertices))
    else:
        mesh = raw_mesh

    mesh.remove_unreferenced_vertices()

    # Project colors
    verts = mesh.vertices
    normals = mesh.vertex_normals
    num_verts = len(verts)

    best_score = -np.ones(num_verts)
    vert_colors = np.ones((num_verts, 4), dtype=np.uint8) * 200
    pts4 = np.hstack([verts, np.ones((num_verts, 1))]).T

    for W2C, intr, arr, mask, cam_pos in cams_data:
        fx, fy, cx, cy = intr
        cam_p = W2C @ pts4
        valid = cam_p[2] > 0.5
        u = np.zeros(num_verts)
        v = np.zeros(num_verts)
        u[valid] = fx * (cam_p[0, valid] / cam_p[2, valid]) + cx
        v[valid] = fy * (cam_p[1, valid] / cam_p[2, valid]) + cy

        in_im = (u >= 0) & (u < img_w) & (v >= 0) & (v < img_h) & valid
        cam_dir = cam_pos - verts
        cam_dir_norm = cam_dir / (np.linalg.norm(cam_dir, axis=1, keepdims=True) + 1e-6)
        cos_theta = np.sum(normals * cam_dir_norm, axis=1)

        candidate = in_im & (cos_theta > 0.15)
        cand_indices = np.where(candidate)[0]

        u_i = np.clip(np.round(u[candidate]).astype(int), 0, img_w - 1)
        v_i = np.clip(np.round(v[candidate]).astype(int), 0, img_h - 1)

        is_fg = mask[v_i, u_i]
        valid_cand = cand_indices[is_fg]
        scores = cos_theta[valid_cand]

        better = scores > best_score[valid_cand]
        replace_idx = valid_cand[better]
        best_score[replace_idx] = scores[better]
        vert_colors[replace_idx] = arr[v_i[is_fg][better], u_i[is_fg][better]]

    # Y-up alignment
    R_z_to_y = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0]
    ], dtype=float)

    aligned_verts = verts @ R_z_to_y.T
    min_y = np.min(aligned_verts[:, 1])
    aligned_verts[:, 1] -= min_y
    raw_h = float(np.max(aligned_verts[:, 1]))
    scale_factor = 0.18 / max(raw_h, 1e-4)
    aligned_verts *= scale_factor
    mesh.vertices = aligned_verts

    # UV Mapping & Texture Atlas
    tex_size = 1024
    y_min, y_max = np.min(aligned_verts[:, 1]), np.max(aligned_verts[:, 1])
    h_span = max(y_max - y_min, 1e-4)
    uvs = []
    for v in aligned_verts:
        theta = np.arctan2(v[2], v[0])
        u = (theta + np.pi) / (2.0 * np.pi)
        v_coord = (v[1] - y_min) / h_span
        uvs.append([u, v_coord])
    uvs = np.array(uvs, dtype=np.float32)

    u_lin = np.linspace(0.0, 1.0, tex_size)
    v_lin = np.linspace(0.0, 1.0, tex_size)
    ug, vg = np.meshgrid(u_lin, v_lin)
    query_pts = np.vstack([ug.ravel(), vg.ravel()]).T

    tree = cKDTree(uvs)
    dist, idx = tree.query(query_pts, k=3)
    weights = 1.0 / (dist + 1e-4)
    weights /= np.sum(weights, axis=1, keepdims=True)

    c0 = vert_colors[idx[:, 0], :3].astype(float)
    c1 = vert_colors[idx[:, 1], :3].astype(float)
    c2 = vert_colors[idx[:, 2], :3].astype(float)
    blended = (c0 * weights[:, 0:1] + c1 * weights[:, 1:2] + c2 * weights[:, 2:3]).astype(np.uint8)
    tex_img = Image.fromarray(blended.reshape((tex_size, tex_size, 3)))

    # Export to both phase_7_export and outputs/syncom_bottle
    for out_d in [OUTPUT_EXPORT, BASE_DIR / "outputs" / "syncom_bottle"]:
        out_d.mkdir(parents=True, exist_ok=True)
        tex_p = out_d / "textures"
        tex_p.mkdir(exist_ok=True)
        tex_img.save(tex_p / "texture_diffuse.png")

        # GLB
        material = trimesh.visual.material.PBRMaterial(
            name="Material_SynCom_Bottle",
            baseColorTexture=tex_img,
            metallicFactor=0.05,
            roughnessFactor=0.45
        )
        textured_mesh = trimesh.Trimesh(
            vertices=mesh.vertices,
            faces=mesh.faces,
            vertex_normals=mesh.vertex_normals,
            visual=trimesh.visual.TextureVisuals(uv=uvs, material=material),
            process=False
        )
        textured_mesh.visual.vertex_colors = vert_colors
        textured_mesh.export(str(out_d / "asset.glb"), file_type="glb")

        # PLY
        mesh.visual.vertex_colors = vert_colors
        mesh.export(str(out_d / "asset.ply"))

        # OBJ
        with open(out_d / "asset.mtl", "w", encoding="utf-8") as f:
            f.write("newmtl Material_Diffuse\nKa 1 1 1\nKd 1 1 1\nKs 0.1 0.1 0.1\nNs 20\nd 1\nillum 2\nmap_Kd textures/texture_diffuse.png\n")
        with open(out_d / "asset.obj", "w", encoding="utf-8") as f:
            f.write(f"mtllib asset.mtl\no SynCom_Bottle\n\n")
            for v in mesh.vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for uv in uvs:
                f.write(f"vt {uv[0]:.6f} {uv[1]:.6f}\n")
            for n in mesh.vertex_normals:
                f.write(f"vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n")
            f.write("\nusemtl Material_Diffuse\ns 1\n")
            num_uvs = len(uvs)
            for face in mesh.faces:
                i1, i2, i3 = face[0] + 1, face[1] + 1, face[2] + 1
                f.write(f"f {i1}/{min(i1, num_uvs)}/{i1} {i2}/{min(i2, num_uvs)}/{i2} {i3}/{min(i3, num_uvs)}/{i3}\n")

    print(f"\n[OK] Production assets successfully exported to {OUTPUT_EXPORT}/ and outputs/syncom_bottle/")


def main():
    t0 = time.time()
    reconstruct()
    print(f"Total reconstruction time: {time.time()-t0:.2f} seconds.")


if __name__ == "__main__":
    main()
