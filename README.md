# Tomasulo-Based Instruction Scheduling for Image Processing

## Overview
This mini-project combines a real image-processing interface with an educational
Tomasulo-style instruction scheduling simulator.

The image pipeline performs grayscale conversion, brightness adjustment, edge
detection, or sharpening. A separate instruction generator creates representative
floating-point arithmetic instructions for a configurable number of image tiles.
The scheduler models in-order issue, register renaming, reservation stations,
functional-unit availability, out-of-order execution, and one CDB broadcast per
cycle.

## Important scope note
The arithmetic instruction trace is representative and tile-level; it is not
captured from the native machine instructions executed by Pillow or NumPy. The
cycle comparison is against a deliberately serial baseline and is not a measured
CPU speedup.

## Files
- `app.py`: Streamlit user interface and result visualizations
- `image_processor.py`: real image-processing operations
- `instruction_generator.py`: tile-level instruction trace and input registers
- `tomasulo.py`: Tomasulo-style scheduling model
- `baseline.py`: serial baseline for the same instruction trace
- `requirements.txt`: Python dependencies

## Installation
Use Python 3.10 or later. In a terminal, navigate to this folder and run:

```bash
python -m venv .venv
```

Activate the environment.

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Launch:
```bash
streamlit run app.py
```

## How to use
1. Upload a PNG, JPG, JPEG, or BMP image.
2. Select an image operation.
3. Choose the number of representative tiles.
4. Click **Run scheduling experiment**.
5. Compare cycle counts and inspect the instruction timeline, station table,
   event log, and downloadable CSV.

## Limitations
This is a teaching model, not a full processor implementation. It does not model
branch prediction, reorder buffers, precise exceptions, memory hierarchy, cache
misses, vector/SIMD instructions, or native CPU timing. Functional-unit
latencies and counts are configurable in `TomasuloSimulator`.
