# Phase 1: Environment Setup and Baseline Reconstruction

| Brief | Details |
| :--- | :--- |
| **Goal** | Set up a reproducible toolchain and prove that the accepted image set can pass through a complete reconstruction workflow before building custom stage-by-stage automation |
| **Status** | 🔄 In Progress |
| **Depends on** | Phase 0 accepted dataset (M0 gate) |
| **Exit milestone** | M1 — Baseline 3D model produced; tool versions and run settings recorded |

---

## Task 1.1 — Choose the Initial Pipeline

### Decision Record
| Tool | Role | Status |
| :--- | :--- | :--- |
| **Meshroom** | First all-in-one baseline — runs full pipeline from images to textured mesh | Primary |
| **COLMAP** | Controlled SfM path when detailed control, logs, or scriptable stages are required | Secondary / Fallback |
| **OpenMVS** | Dense reconstruction and texturing when more control is needed | Optional |
| **Open3D** | Python-based point-cloud scripting and visualization | Optional |
| **MeshLab** | Mesh repair, decimation, normals | Asset prep |
| **Blender** | Final asset work, UVs, export | Asset prep |

> [!NOTE]
> Do not commit to a paid tool by default. Begin with free/open-source tooling throughout this phase.

---

## Task 1.2 — Verify Machine and Dependencies

Fill in this record before running the baseline:

```
OS:               
CPU:              
RAM (GB):         
GPU:              
GPU VRAM (GB):    
GPU Driver:       
CUDA version:     
Disk space available (GB):

Tool versions:
  Meshroom:         
  COLMAP:           
  Python:           
  Open3D:           
  MeshLab:          
  Blender:          
```

**Test run checklist:**
- [ ] Image loading succeeds (test with 5–10 images from `data/01_reconstruction/`)
- [ ] Feature extraction completes without crash
- [ ] Expected runtime estimated for full reconstruction subset
- [ ] Peak RAM/VRAM usage noted

---

## Task 1.3 — Project Folders and Run Manifests

Folder structure is pre-created. For **each pipeline run**, save a run manifest JSON:

```json
{
  "run_id": "baseline_001",
  "phase": "1",
  "tool": "Meshroom",
  "tool_version": "",
  "input_manifest": "manifests/dataset_split.json",
  "reconstruction_image_dir": "data/01_reconstruction/",
  "config": {},
  "start_time": "",
  "end_time": "",
  "warnings": [],
  "output_paths": {
    "camera_poses": "",
    "sparse_cloud": "",
    "dense_cloud": "",
    "mesh": "",
    "texture": ""
  },
  "notes": ""
}
```

> [!IMPORTANT]
> Keep intermediate outputs at every stage. Never overwrite a completed reconstruction run.

---

## Task 1.4 — Run and Inspect the Baseline

**Steps:**
1. Open Meshroom and load all images from `data/01_reconstruction/`
2. Run the full default pipeline (do not change parameters for the first baseline)
3. After completion, inspect:
   - **Camera registration** — Are all/most cameras registered? How many failed?
   - **Sparse point cloud** — Does it represent the overall shape of the object?
   - **Dense cloud** — Are there obvious holes or artifacts?
   - **Mesh completeness** — Does the mesh capture all visible surfaces?
   - **Texture quality** — Are there seams, blur, ghosting?
4. Save screenshots/renders to `outputs/phase_1_baseline/`
5. Note all failure regions — **do not optimize parameters before a baseline exists**

---

## Verification / Acceptance Gate (M1)

- [ ] Toolchain completes a baseline run without unexplained crash
- [ ] Camera-registration summary saved (number registered / total)
- [ ] Sparse point cloud, mesh, and at least one textured result saved in `outputs/phase_1_baseline/`
- [ ] Run can be repeated from `run_manifest.json` and the environment setup guide
- [ ] Known limitations and runtime/resource measurements recorded

---

## Deliverables

| Deliverable | Path | Status |
| :--- | :--- | :--- |
| Environment/setup guide | `outputs/phase_1_baseline/environment_setup.md` | 🔄 Pending |
| Baseline reconstruction artifacts | `outputs/phase_1_baseline/` | ⏳ Pending |
| Run manifest | `outputs/phase_1_baseline/run_manifest.json` | ⏳ Pending |
| Initial quality notes | `outputs/phase_1_baseline/quality_notes.md` | ⏳ Pending |

---

## Risks and Handling

| Risk | Handling |
| :--- | :--- |
| Large image sets exceed available RAM/VRAM/disk | Pilot on a representative 20–30 image subset; estimate full-run needs before scaling |
| Paid tool commitment | Begin with free tooling; evaluate commercial tools only if blockers arise |
| Meshroom fails silently or crashes mid-pipeline | Check node logs per Meshroom node; switch to COLMAP for the failing stage |

