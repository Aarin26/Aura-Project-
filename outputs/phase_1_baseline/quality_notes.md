# Phase 1 Baseline — Quality Inspection Notes

## Baseline Run ID: `baseline_001`

---

## Camera Registration

| Metric | Value |
| :--- | :--- |
| Total input images | *(fill in)* |
| Cameras registered | *(fill in)* |
| Cameras failed to register | *(fill in)* |
| Registration rate | *(fill in)*% |

**Failed image list:**
*(List any images that failed to register and the suspected reason)*

---

## Sparse Point Cloud Inspection

- [ ] Point cloud represents the overall shape of the object
- [ ] No major disconnected clusters visible
- [ ] Notable defects/gaps: *(describe)*

---

## Dense Cloud Inspection

- [ ] Dense cloud covers all intended surfaces
- [ ] Holes/artifacts noted: *(describe)*

---

## Mesh Inspection

- [ ] Mesh captures all visible surfaces
- [ ] Triangle count: *(fill in)*
- [ ] Obvious geometry errors: *(describe)*

---

## Texture Inspection

- [ ] Texture applied successfully
- [ ] Seams or ghosting observed: *(describe)*
- [ ] Overall texture quality: *(Good / Acceptable / Poor)*

---

## Failure Regions

*(List surfaces or areas that reconstructed poorly, with the suspected cause)*

| Region | Issue | Suspected Cause |
| :--- | :--- | :--- |
| | | |

---

## Resource Usage

| Metric | Value |
| :--- | :--- |
| Total runtime | *(fill in)* min |
| Peak RAM usage | *(fill in)* GB |
| Peak VRAM usage | *(fill in)* GB |
| Output disk footprint | *(fill in)* MB |

---

## Overall Baseline Decision

- [ ] **M1 gate PASSED** — Proceed to Phase 2
- [ ] **M1 gate FAILED** — Address the issue noted below before proceeding

**Notes:**
*(Any additional observations, warnings from tool logs, or recommendations before Phase 2)*

