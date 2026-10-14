# Environment Setup Guide — Phase 1

## Machine Specifications

| Component | Details |
| :--- | :--- |
| OS | *(fill in)* |
| CPU | *(fill in)* |
| RAM | *(fill in)* GB |
| GPU | *(fill in)* |
| GPU VRAM | *(fill in)* GB |
| GPU Driver version | *(fill in)* |
| CUDA version | *(fill in)* |
| Disk space available | *(fill in)* GB |

---

## Tool Versions

| Tool | Version | Installation Path / Notes |
| :--- | :--- | :--- |
| Meshroom | *(fill in)* | *(fill in)* |
| COLMAP | *(fill in)* | *(fill in)* |
| Python | *(fill in)* | *(fill in)* |
| Open3D | *(fill in)* | *(fill in)* |
| MeshLab | *(fill in)* | *(fill in)* |
| Blender | *(fill in)* | *(fill in)* |
| Pillow (PIL) | *(fill in)* | `pip install Pillow` |

---

## Setup Instructions

### Meshroom
1. Download Meshroom from [AliceVision/Meshroom releases](https://github.com/alicevision/Meshroom/releases)
2. Extract to a local directory; no installation required (portable)
3. Launch `Meshroom.exe` (Windows) or `./Meshroom` (Linux/macOS)
4. Verify GPU-accelerated node support: check CUDA availability in the Meshroom log on startup

### COLMAP
1. Download from [colmap.github.io](https://colmap.github.io/install.html)
2. Verify with: `colmap -h`

### Python Environment
```bash
# Create a virtual environment for pipeline scripts
python -m venv venv
.\venv\Scripts\activate   # Windows

pip install Pillow open3d numpy tqdm
```

---

## Test Run Verification

- [ ] Loaded 5–10 test images from `data/01_reconstruction/` into Meshroom
- [ ] Feature extraction (FeatureExtraction node) completed without error
- [ ] Confirmed Meshroom is using GPU (check Meshroom node progress bar color — yellow = CPU fallback, green = GPU)
- [ ] Estimated runtime for full reconstruction image set: *(fill in)* minutes

---

## Notes

*(Any deviations from standard setup, known issues, or environment-specific workarounds)*

