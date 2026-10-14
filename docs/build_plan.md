# 3D Model Reconstruction Build Plan
Multi-view photogrammetry: real-world photos → validated, textured 3D asset → Unity / Unreal

| Plan basis | Project boundary | Recommended approach |
| :--- | :--- | :--- |
| Project brief supplied in DOC-20260918-WA0009.pdf; phase-document structure adapted from supplied reference project | Offline, per-object reconstruction. Outputs a 3D asset file — **not** live recognition, AR tracking, or a point-match JSON | Start with Meshroom for end-to-end baseline; use COLMAP + OpenMVS/Open3D + MeshLab + Blender where more control is needed. Free/open-source tooling is sufficient |

---

> [!NOTE]
> Work through phases **in order** unless a task is explicitly independent. Close a phase only when its acceptance gate has evidence — not merely because a tool run completed.
> Keep reconstruction inputs, intermediate outputs, final exports, and validation evidence separate and versioned.
> Use the first representative object as the pilot. Once its pipeline is repeatable, reuse the workflow for additional objects.

---

## Project Outcome and Scope

**Goal:** Build a repeatable offline pipeline that accepts a set of overlapping photographs of a real object, estimates camera poses and sparse geometry, establishes real-world scale, reconstructs a dense surface, creates a cleaned and textured mesh, validates it against photographs withheld from reconstruction, and exports a Unity/Unreal-ready asset.

| In Scope | Out of Scope |
| :--- | :--- |
| Dataset audit; camera metadata and distortion handling; feature matching; SfM; bundle adjustment; scale calibration; MVS; meshing; mesh cleanup/decimation; UVs and texture baking; held-out validation; FBX/glTF export and handoff | Live object recognition; real-time camera processing; AR tracking/runtime; rendering or interaction inside the final AR/VR application; training a conventional image classifier; outputting only matched points |

---

## End-to-End Workflow

| Step | Input → Output | Suggested Tool(s) |
| :--- | :--- | :--- |
| **Phase 0** — Dataset audit | Photos + known measurement → accepted image set and held-out split | Manual review, image metadata tools |
| **Phase 1** — Environment and baseline | Accepted image set → reproducible baseline run | Meshroom; Python; COLMAP as needed |
| **Phase 2** — Preprocess and SfM | Images → calibrated cameras + sparse point cloud | COLMAP or Meshroom; OpenCV optional |
| **Phase 3** — Scale and sparse QA | Sparse model + reference measurement → real-scale sparse reconstruction | COLMAP, Open3D or Python utility |
| **Phase 4** — Dense reconstruction and mesh | Calibrated cameras + images → dense cloud and triangle mesh | COLMAP / OpenMVS / Open3D / MeshLab |
| **Phase 5** — Cleanup and texturing | Raw mesh + source images → optimized, textured mesh | MeshLab, Blender, xatlas/OpenMVS |
| **Phase 6** — Held-out validation | Final candidate + unseen photos → measured validation report | Blender/Open3D + OpenCV |
| **Phase 7** — Export and handoff | Validated asset → FBX/glTF package and handoff note | Blender; Unity/Unreal import check |

---

## Milestone Summary

| Milestone | Evidence Required to Close |
| :--- | :--- |
| **M0 — Dataset ready** | Audited image manifest, coverage checklist, measured scale reference, held-out split |
| **M1 — Baseline reproduced** | End-to-end baseline artifacts, setup notes, tool versions and run manifest |
| **M2 — Sparse model accepted** | Camera registration summary, sparse cloud, camera poses, reprojection/quality notes |
| **M3 — Real scale accepted** | Documented scale factor, units, reference-distance error and coordinate convention |
| **M4 — Dense geometry accepted** | Dense cloud, raw mesh, geometry inspection and known-defect list |
| **M5 — Textured candidate ready** | Cleaned optimized mesh, UVs, texture maps and preview |
| **M6 — Validation passed** | Held-out renders/comparisons, measurements, review decision and defect report |
| **M7 — Handoff complete** | FBX/glTF package, engine import check, dimensions/origin note and reproducibility record |

---

## Phase 0 — Dataset Audit and Ground Truth

| Brief | Details |
| :--- | :--- |
| **Goal** | Establish that the photo set contains enough visual overlap, angle/distance variety, stable appearance, and a known real-world measurement to support a reliable reconstruction |
| **Initial status** | ✅ In Progress |
| **Depends on** | None |
| **Exit milestone** | M0 — Image set accepted, reference measurement documented, held-out test subset reserved |

### Tasks
- **Task 0.1** — Create a read-only master copy of all original photographs; record filenames, dimensions, file sizes, and SHA-256 checksums. Keep originals separate from any processed copies. Record the capture device/lens; flag mixed cameras or lenses.
- **Task 0.2** — Check that each important surface appears in at least 2–3 overlapping images. Confirm 360° multi-height coverage. Check that the object fills ~50–80% of the frame. Flag blur, exposure shifts, moving objects, reflective/transparent surfaces.
- **Task 0.3** — Identify a known physical distance visible in the scene. Record the real-world distance, units, measurement method, and reference image(s). Document camera/lens uncertainty if EXIF is absent.
- **Task 0.4** — Reserve ~10–15% of clear photos from different viewpoints as held-out test images. Never use these for matching, reconstruction, meshing, or texturing. Record the split in a manifest.

### Verification / Acceptance Gate (M0)
- [ ] Every source image is catalogued and checksummed; originals remain unchanged
- [ ] Coverage review identifies no critical surface with zero/single-view coverage, or documents the known limitation
- [ ] A real-world reference distance and units are recorded
- [ ] Held-out images are selected and excluded from the reconstruction input manifest
- [ ] A short dataset-readiness report lists accepted images, excluded images, and known capture limitations

### Deliverables
- `manifests/source_manifest.csv` — Image manifest and checksums
- `reports/phase_0_dataset_audit.md` — Dataset audit checklist and limitations
- `manifests/scale_reference.json` — Scale-reference record
- `manifests/dataset_split.json` — Train/reconstruction vs. held-out image manifest

### Risks
| Risk | Handling |
| :--- | :--- |
| Insufficient overlap or unobserved surfaces | Cannot be repaired downstream; recapture before continuing where possible |
| Reflective, transparent, textureless, or moving surfaces | Record as object-specific risks rather than promising full geometry |

---

## Phase 1 — Environment Setup and Baseline Reconstruction

| Brief | Details |
| :--- | :--- |
| **Goal** | Set up a reproducible toolchain and prove the image set can pass through a complete reconstruction workflow before building custom stage-by-stage automation |
| **Initial status** | 🔄 In Progress |
| **Depends on** | Phase 0 accepted dataset |
| **Exit milestone** | M1 — Baseline 3D model produced; tool versions and run settings recorded |

### Tasks
- **Task 1.1** — Choose the initial pipeline: Meshroom as the first all-in-one baseline; COLMAP as the controlled SfM path when detailed control or logs are required; OpenMVS for dense reconstruction/texturing if needed; Open3D for scripting; MeshLab for mesh repair; Blender for final asset work.
- **Task 1.2** — Record OS, CPU, RAM, GPU, driver/CUDA availability, disk space, and tool versions. Run a small test job to confirm image loading, feature extraction, and reconstruction succeed. Record expected runtime and peak resource usage.
- **Task 1.3** — Create consistent project folders for source images, reconstruction inputs, held-out images, logs, sparse/dense outputs, meshes, textures, exports, and reports. For each run, save the input manifest, configuration, tool versions, start/end time, warnings, and output paths.
- **Task 1.4** — Run the full default Meshroom pipeline on the reconstruction subset. Inspect camera registration, sparse cloud, dense cloud, mesh completeness, and texture quality. Capture screenshots and note failure regions — do not optimize before a baseline exists.

### Verification / Acceptance Gate (M1)
- [ ] Toolchain completes a baseline run without unexplained crash
- [ ] Camera-registration summary, sparse cloud, mesh, and at least one textured result are saved
- [ ] The run can be repeated from the manifest and documented setup instructions
- [ ] Known limitations and runtime/resource measurements are recorded

### Deliverables
- `outputs/phase_1_baseline/environment_setup.md` — Environment/setup guide
- `outputs/phase_1_baseline/` — Baseline reconstruction artifacts
- `outputs/phase_1_baseline/run_manifest.json` — Run manifest and initial quality notes

### Risks
| Risk | Handling |
| :--- | :--- |
| Large image sets exceed RAM/VRAM/disk | Pilot on a representative subset; estimate full-run needs before scaling |
| Paid tool commitment | Begin with free tooling as recommended; evaluate commercial tools only if blockers arise |

---

## Phase 2 — Image Preprocessing, Feature Matching, and SfM

| Brief | Details |
| :--- | :--- |
| **Goal** | Turn accepted photographs into a sparse reconstruction with estimated camera intrinsics/poses and 3D feature points |
| **Initial status** | ⏳ Not started |
| **Depends on** | Phase 1 baseline; Phase 0 dataset accepted |
| **Exit milestone** | M2 — Most usable images register into one coherent sparse model; camera poses and bundle-adjustment results saved |

### Tasks
- **Task 2.1** — Load images and inspect EXIF metadata (focal length, camera model). Apply the chosen tool's lens-distortion handling. If images come from different cameras/lenses, ensure the tool does not force one shared intrinsic model.
- **Task 2.2** — Run feature detection and cross-image matching (SIFT is a suitable offline choice). Inspect the image-match graph for disconnected clusters or false matches. If matching fails, investigate image quality, overlap, and camera grouping first.
- **Task 2.3** — Build the initial reconstruction from a strong overlapping image pair, then incrementally register additional images. Run bundle adjustment. Save the sparse cloud, camera intrinsics/extrinsics, registered-image list, reprojection-error statistics, and logs.
- **Task 2.4** — Identify images that did not register; determine whether each is redundant, low quality, or critical for a missing surface. If a failed image is the only view of an important region, revisit Phase 0 or rerun with documented settings.

### Verification / Acceptance Gate (M2)
- [ ] A coherent reconstruction rather than disconnected components (unless geometry warrants it)
- [ ] Registered-image list and unregistered-image list reviewed and explained
- [ ] Camera poses and sparse geometry saved and re-openable
- [ ] Reprojection-error and registration summaries retained for comparison between runs

### Deliverables
- `outputs/phase_2_sparse/` — Sparse reconstruction
- Camera model and pose data
- Registration/matching report
- Documented run settings

### Risks
| Risk | Handling |
| :--- | :--- |
| Repeated patterns, textureless regions, blur, reflections, weak overlap | Can cause incorrect matches or disconnected components; improve capture before pipeline changes |
| Missing EXIF data | Not an automatic blocker; if self-calibration is unstable, consider explicit calibration |

---

## Phase 3 — Scale Calibration and Sparse-Model Quality Gate

| Brief | Details |
| :--- | :--- |
| **Goal** | Resolve SfM scale ambiguity and confirm the sparse model is coherent enough to justify the cost of dense reconstruction |
| **Initial status** | ✅ Completed (Pilot Baseline) |
| **Depends on** | Phase 2 sparse reconstruction |
| **Exit milestone** | M3 — Reconstruction expressed in documented real-world units; scale and sparse geometry pass review |

### Tasks
- **Task 3.1** — Locate the two reconstructed 3D points corresponding to the known physical reference distance. Measure their separation and compute scale factor = `known_real_distance / reconstructed_distance`. Apply consistently to point cloud and camera positions. Record source points, original reconstructed distance, target distance, units, scale factor, and uncertainty.
- **Task 3.2** — Choose and document the unit system (meters recommended). Define a provisional origin and orientation convention. Check that camera and point coordinates remain mutually consistent after scaling.
- **Task 3.3** — Inspect the sparse model from multiple viewpoints for drift, warped geometry, disconnected components, and outlier points. If scale or geometry is implausible, return to Phase 0 or Phase 2 rather than densifying a faulty model.

### Verification / Acceptance Gate (M3)
- [ ] Saved model uses explicit real-world units with a recorded scale factor
- [ ] Known reference distance reproduced within agreed tolerance; if no tolerance defined, document measured error and obtain sign-off
- [ ] Sparse model has no unexplained large-scale warping or disconnected reconstruction
- [ ] Coordinate-system and origin decisions documented

### Deliverables
- `outputs/phase_3_scaled/` — Scaled sparse model
- Scale-calibration record
- Sparse-model QA checklist
- Coordinate/origin convention note

### Risks
| Risk | Handling |
| :--- | :--- |
| Scale calibration cannot correct a warped or incorrectly reconstructed model | Only fixes global scale ambiguity; a bad sparse model must be rebuilt |
| Poorly visible or inaccurately measured reference distance | Prefer a clearly identifiable, accurately measured reference |

---

## Phase 4 — Dense Reconstruction and Surface Meshing

| Brief | Details |
| :--- | :--- |
| **Goal** | Convert the calibrated camera solution and images into a dense point cloud and a connected triangle mesh approximating the object's visible surface |
| **Initial status** | ✅ Completed (Pilot Baseline) |
| **Depends on** | Phase 3 quality gate passed |
| **Exit milestone** | M4 — Dense cloud and raw mesh cover intended surfaces; known holes documented |

### Tasks
- **Task 4.1** — Run the selected MVS stage using registered cameras and reconstruction images (COLMAP dense or COLMAP-to-OpenMVS). Inspect depth-map failures, noisy areas, holes, and regions lacking multi-view support.
- **Task 4.2** — Generate a triangle mesh from the dense cloud (OpenMVS, Open3D Poisson, or MeshLab). Review surface normals, disconnected fragments, and whether the surface follows the object's actual silhouette. Keep the raw dense cloud and raw mesh before cleanup.
- **Task 4.3** — Record resolution, depth-map settings, filtering parameters, meshing method, and manual exclusions. Compare dense cloud and mesh with sparse model and original photos for scale drift. If a major surface is missing, decide to recapture or adjust settings rather than hiding the gap.

### Verification / Acceptance Gate (M4)
- [ ] Dense point cloud and raw mesh saved and re-openable
- [ ] Mesh has expected overall silhouette and dimensions; major defects and uncovered regions identified
- [ ] Raw outputs preserved separately from any repaired version
- [ ] Processing settings and known limitations recorded

### Deliverables
- `outputs/phase_4_dense/` — Dense point cloud; raw triangle mesh
- MVS/meshing run manifest
- Geometry defect report

### Risks
| Risk | Handling |
| :--- | :--- |
| MVS is computationally expensive | Monitor memory, GPU/CPU load, and disk usage; pilot on representative subset |
| Hole filling can create invented surfaces | Only auto-repair small, well-bounded holes; large missing regions should trigger recapture |

---

## Phase 5 — Mesh Cleanup, Optimization, UVs, and Texturing

| Brief | Details |
| :--- | :--- |
| **Goal** | Prepare a clean, efficient, textured asset that preserves recognizable shape and surface detail while meeting downstream runtime constraints |
| **Initial status** | ✅ Completed (Pilot Baseline) |
| **Depends on** | Phase 4 raw mesh and dense cloud |
| **Exit milestone** | M5 — Cleaned, scaled, UV-mapped, textured candidate asset ready for validation and engine import |

### Tasks
- **Task 5.1** — Remove isolated floating fragments and reconstruction noise while preserving legitimate thin parts. Repair small holes where surrounding geometry supports reliable repair. Recalculate/check normals; remove accidental duplicate or degenerate geometry.
- **Task 5.2** — Measure raw triangle count and set a target based on the intended Unity/Unreal use case. Apply controlled decimation in MeshLab or Blender, checking silhouette and fine details after each reduction. Evaluate retopology if clean quad topology is required.
- **Task 5.3** — Generate UV layout using Blender and/or xatlas; inspect overlaps, stretching, seams, and wasted texture space. Choose texture resolution based on object size and expected viewing distance.
- **Task 5.4** — Project real image color and detail onto the UV-mapped mesh (OpenMVS texturing or Blender workflows). Inspect seams, ghosting, color mismatches, blur, and texture bleeding. Save texture maps as external files; confirm material references resolve.
- **Task 5.5** — Set object scale and origin per the documented convention. Name mesh, materials, and texture files consistently. Create a preview render/turntable for human inspection (separate from formal held-out validation).

### Verification / Acceptance Gate (M5)
- [ ] No obvious floating fragments or accidental holes; accepted defects listed
- [ ] Decimation preserves overall silhouette and important details at target viewing distance
- [ ] UVs and material references are valid; texture seams and ghosting reviewed
- [ ] Candidate remains in documented real-world scale and coordinate convention
- [ ] Optimized mesh and texture files re-openable in Blender without missing assets

### Deliverables
- `outputs/phase_5_textured/` — Cleaned/optimized mesh; UV layout; texture maps and material; candidate asset preview
- Optimization settings and known-defect list

### Risks
| Risk | Handling |
| :--- | :--- |
| Aggressive decimation erases thin parts or surface detail | Compare against the raw mesh at each optimization step |
| Texture quality constrained by photo coverage and exposure | Texturing cannot recover detail never captured |

---

## Phase 6 — Validation Against Held-Out Photos

| Brief | Details |
| :--- | :--- |
| **Goal** | Evaluate geometric and visual quality using photos deliberately excluded from reconstruction, measuring generalization to unseen viewpoints |
| **Initial status** | ✅ Completed (Pilot Baseline) |
| **Depends on** | Phase 5 candidate asset; Phase 0 held-out set |
| **Exit milestone** | M6 — Validation report records objective comparisons, visual findings, acceptance decisions, and required iterations |

### Tasks
- **Task 6.1** — Estimate viewpoint for each held-out photo by matching against the established reconstruction without adding the photo to the reconstruction. Record any held-out image that cannot be localized reliably.
- **Task 6.2** — Render the candidate mesh from the estimated held-out camera viewpoint. Compare silhouette, proportions, visible features, and texture alignment against the real photograph. Use SSIM as a supporting metric, not the only quality decision.
- **Task 6.3** — Compare known dimensions against real measurements where available. Record per-view observations, failed regions, and repeatable metrics. Separate geometry defects from texture-only defects.
- **Task 6.4** — Map each failed criterion to the earliest likely cause: capture coverage, SfM, scale, dense reconstruction, meshing, or texturing. Change one meaningful factor at a time. Do not move held-out photos into the reconstruction set just to improve scores.

### Verification / Acceptance Gate (M6)
- [ ] Every held-out image has a recorded result: localized and compared, or marked unscorable with a reason
- [ ] Rendered-versus-real comparisons saved for representative views
- [ ] Known physical dimensions and scale checked where ground truth exists
- [ ] Project owner accepts the documented quality, or asset returns to responsible phase
- [ ] Report distinguishes measured evidence from subjective visual review

### Deliverables
- `outputs/phase_6_validation/` — Validation script/configuration; rendered comparison images; metrics and human review; pass/fail report with defect traceability

### Risks
| Risk | Handling |
| :--- | :--- |
| SSIM/pixel metrics affected by lighting and exposure differences | Pair metrics with silhouette and geometry review |
| Repeated use of held-out photos to tune settings makes them non-independent | Preserve a fresh validation subset if tuning occurs |

---

## Phase 7 — Export, Engine Import, and Handoff

| Brief | Details |
| :--- | :--- |
| **Goal** | Package the validated asset in a standard format with textures, real-world dimensions, and coordinate/origin metadata for Unity/Unreal import |
| **Initial status** | ⏳ Not started |
| **Depends on** | Phase 6 accepted validation report |
| **Exit milestone** | M7 — Asset imports into the target engine at expected size and appearance; handoff package complete |

### Tasks
- **Task 7.1** — Export from Blender as **glTF** (preferred) or FBX. Use OBJ+MTL only as a fallback. Ensure mesh, UVs, materials, texture maps, and scale are included/referenced correctly.
- **Task 7.2** — Open the exported file in a clean Blender session or fresh environment to catch broken paths and missing textures. Check dimensions in meters, origin, orientation, normals, material appearance, and polygon count. Include texture files and a README/handoff note; avoid absolute file paths.
- **Task 7.3** — Import the asset into the target engine and verify scale, orientation, material/texture appearance, and visual quality. Check whether axis conversion or specific import settings are needed; record the agreed convention. Capture an import screenshot as evidence.
- **Task 7.4** — Version the final mesh, texture maps, export file, source image manifest, pipeline configuration, and validation report together. Label the final deliverable clearly; keep intermediate/raw files available for future repairs. Document known limitations and what would require recapture.

### Verification / Acceptance Gate (M7)
- [ ] Exported FBX/glTF opens without missing geometry, material, or texture references
- [ ] Real-world dimensions, origin point, units, and orientation explicitly documented
- [ ] Target Unity/Unreal import verified by inspection (not assumed from export success)
- [ ] Final package contains the asset, textures/materials, handoff note, and validation report
- [ ] Reproducible record links the final export to its source images and reconstruction settings

### Deliverables
- `outputs/phase_7_export/` — Final FBX or glTF asset; texture/material package; dimensions and origin note; Unity/Unreal import verification; validation report and reproducibility manifest

### Risks
| Risk | Handling |
| :--- | :--- |
| Axis, unit, and origin mismatches make a correct model unusable downstream | Agree on target convention and test in-engine |
| Broken texture links on another machine | Keep export self-contained or use relative texture paths |

---

## Cross-Phase Engineering Rules

> [!IMPORTANT]
> - **Preserve raw inputs and intermediate artifacts.** Never overwrite source photographs or the first successful reconstruction.
> - **Every run should be traceable** to an input manifest, tool versions, settings, and logs.
> - **Keep reconstruction images and held-out test images strictly separated.**
> - **Treat real-world scale as a measured calibration step**, not an assumption inferred from the mesh viewer.
> - **Do not hide missing geometry with aggressive hole filling**; report capture gaps and recapture where practical.
> - **When a gate fails, return to the earliest responsible stage** instead of adding compensating edits downstream.
> - The project is offline and per-object: optimize for **repeatability, quality, and clean handoff** rather than real-time throughput.

---

## Open Decisions to Resolve Before Implementation

- [ ] **Target object(s) and quality definition** — Define what counts as a successful reconstruction for the pilot.
- [ ] **Target runtime use** — Expected viewing distance, polygon budget, texture resolution, retopology needed?
- [ ] **Reference measurement and tolerance** — Select measurement source and agree on allowable dimensional error.
- [ ] **Receiving engine and format** — Unity or Unreal, glTF or FBX, axis convention, units, and origin point.
- [ ] **Compute environment** — Available RAM/VRAM/disk; will dense reconstruction run on CPU, GPU, or a separate workstation?
- [ ] **Validation thresholds** — Agree on objective dimensional/silhouette criteria plus human visual sign-off before Phase 6.
