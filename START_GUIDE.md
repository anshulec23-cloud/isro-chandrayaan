# LUMEN 1.0 Release - Quick Start Guide

Welcome to the **Lunar Mission Control** v1.0 release! This application provides a full-stack, end-to-end pipeline for registering multi-modal lunar images from Chandrayaan-2 (OHRC, TMC-2, and IIRS) using novel photometric normalization and phase-correlation geometry.

## 1. What's Included
* **Core Pipeline**: PDS4 Parsing, Lommel-Seeliger Normalization, SuperPoint+LightGlue, RIFT2, and MAGSAC++.
* **FastAPI Backend**: WebSocket-enabled job processing API.
* **Mission Control UI**: A highly-styled, interactive HUD built with Tailwind and Javascript.

## 2. Setup

`ash
# Make sure you are in the project directory
cd isro-chandrayaan

# Install the package and all dependencies (including AI/CV tools)
pip install -e ".[dev]"
`

## 3. Launching the Application

Start the FastAPI server. This will also automatically serve the Mission Control UI!

`ash
python -m lumen.cli serve --port 8000
`

## 4. Using the Dashboard
1. Open your browser and navigate to: **http://localhost:8000/dashboard**
2. You will see the **Lunar Mission Control - Geometry** panel.
3. Because you have already placed the PRADAN files in data/raw/, simply click the **INITIATE ALIGNMENT** button in the bottom right.
4. The dashboard will connect via WebSocket to the Python backend, initiate the pipeline on the real OHRC and TMC-2 files, and stream the progress back to the HUD.

## 5. Command Line Usage
If you prefer running the pipeline headlessly on the massive .img and .qub files you downloaded, you can run:

`ash
python -m lumen.cli register \
    --source data/raw/ch2_ohr_ncp_20260130T1309574436_d_img_d18/calibrated/20260130/ch2_ohr_ncp_20260130T1309574436_d_img_d18.xml \
    --reference data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml \
    --source-sensor OHRC \
    --ref-sensor TMC2
`

Enjoy your lunar exploration!
