# LUMEN - Lunar Multi-modal Engagement Network
## Architecture Document

## 1. System Context Diagram (C4 Level 1)
```mermaid
C4Context
    title System Context diagram for LUMEN System

    Person(user, "Scientist / Analyst", "Uses LUMEN to register Chandrayaan-2 images")
    System(lumen, "LUMEN System", "Multi-modal, Sun angle and scale invariant image correspondence pipeline")

    System_Ext(pradan, "PRADAN Portal (ISRO)", "Provides raw PDS4 image data (OHRC, TMC, IIRS)")
    System_Ext(dem_sources, "DEM Data Sources", "Provides Digital Elevation Models for orthorectification")

    Rel(user, lumen, "Uploads/Selects images, views results", "HTTPS/REST")
    Rel(lumen, pradan, "Downloads raw PDS4 data", "HTTPS")
    Rel(lumen, dem_sources, "Fetches elevation data", "HTTPS/API")
```

## 2. Container Diagram (C4 Level 2)
```mermaid
C4Container
    title Container diagram for LUMEN System

    Person(user, "Scientist / Analyst", "Uses LUMEN to register Chandrayaan-2 images")

    Container(frontend, "Frontend Dashboard", "React, Tailwind CSS", "Web-based Lunar Mission Control theme dashboard for user interaction")
    Container(api, "Backend API", "Python, FastAPI", "RESTful API handling requests, routing, and job management")
    Container(pipeline, "Processing Pipeline (Lumen Core)", "Python, PyTorch, OpenCV", "Executes the core image registration logic (preprocessing, feature matching, geometry)")
    ContainerDb(datastore, "Data Store", "File System", "Stores raw, processed, and DEM data")
    Container(gpu, "GPU Compute Node", "CUDA, PyTorch", "Hardware acceleration for Deep Learning models (SuperPoint/LightGlue)")

    Rel(user, frontend, "Interacts with", "HTTPS")
    Rel(frontend, api, "Makes API calls", "JSON/HTTPS")
    Rel(api, pipeline, "Orchestrates jobs", "In-process / Async")
    Rel(pipeline, datastore, "Reads/Writes data", "File I/O")
    Rel(pipeline, gpu, "Offloads tensor ops", "CUDA")
    Rel(datastore, gpu, "Loads model weights", "File I/O")
```

## 3. Component Diagram (C4 Level 3)
```mermaid
C4Component
    title Component diagram for LUMEN Processing Pipeline

    Container(api, "Backend API", "Python, FastAPI", "RESTful API handling requests")

    Boundary(pipeline, "Lumen Core Modules") {
        Component(orchestrator, "Orchestrator", "Python", "Manages the end-to-end pipeline execution")
        Component(ingest, "Ingest Module", "Python", "Parses PDS4 labels, extracts sun/orbit metadata")
        Component(preprocess, "Preprocess Module", "Python, OpenCV", "Radiometric/Photometric normalization, Orthorectification")
        Component(features, "Feature Module", "Python, PyTorch", "Deep matching (SuperPoint+LightGlue), RIFT2, Grid Sampling")
        Component(geometry, "Geometry Module", "Python, OpenCV", "MAGSAC++ outlier rejection, Phase correlation sub-pixel refinement")
        Component(registration, "Registration Module", "Python", "Applies transforms, generates registered output")
        Component(eval, "Evaluation Module", "Python", "Calculates RMSE, SSIM, inlier ratio")
    }

    Rel(api, orchestrator, "Triggers workflow")
    Rel(orchestrator, ingest, "Calls")
    Rel(orchestrator, preprocess, "Calls")
    Rel(orchestrator, features, "Calls")
    Rel(orchestrator, geometry, "Calls")
    Rel(orchestrator, registration, "Calls")
    Rel(orchestrator, eval, "Calls")

    Rel(ingest, preprocess, "Passes metadata/images")
    Rel(preprocess, features, "Passes normalized images")
    Rel(features, geometry, "Passes raw matches")
    Rel(geometry, registration, "Passes refined transform")
    Rel(registration, eval, "Passes registered pairs")
```

## 4. Data Flow Architecture
```mermaid
flowchart TD
    subgraph Input
        A[Raw PDS4 Files] --> B
        DEM[DEM Data] --> B
    end

    subgraph Pipeline [LUMEN Core Pipeline]
        B[Ingest: Parse Labels & Metadata] --> C(Preprocess: Radiometric & Photometric)
        C --> D(Preprocess: Orthorectification)
        D --> E{Feature Extraction}
        
        E -->|Optical/Similar| F[SuperPoint + LightGlue]
        E -->|Cross-Modal| G[RIFT2 Descriptor]
        
        F --> H[Match Grid Sampling]
        G --> H
        
        H --> I(Geometry: MAGSAC++ Outlier Rejection)
        I --> J(Geometry: Sub-pixel Refinement)
        
        J --> K(Registration: Warp & Blending)
    end

    subgraph Output
        K --> L[Registered Image]
        K --> M[Evaluation Metrics: RMSE, SSIM, Checkerboard]
    end
```

## 5. Key Design Decisions

*   **SuperPoint + LightGlue over SIFT/ORB**: Traditional handcrafted features struggle with the extreme illumination variations and lack of distinct texture in lunar regolith. SuperPoint extracts learned, robust features, while LightGlue performs attention-based matching that excels under extreme viewpoint and lighting changes.
*   **RIFT2 for Cross-Modal Registration**: RIFT2 (Radiation-variation Insensitive Feature Transform) uses phase congruency instead of image intensity, making it highly robust to non-linear radiometric differences (e.g., matching optical OHRC with different sensor modalities).
*   **MAGSAC++ over RANSAC**: MAGSAC++ eliminates the need to fine-tune inlier threshold parameters and utilizes marginal scoring, resulting in far more robust and accurate geometric model estimation under high outlier ratios common in lunar imagery.
*   **Phase Correlation for Sub-pixel Refinement**: Operates in the frequency domain, providing highly accurate sub-pixel translation estimation without relying on local feature point stability, which is crucial for the high-resolution OHRC images (0.25m GSD).
*   **Lommel-Seeliger Photometric Normalization**: Specifically chosen as it models the scattering properties of the lunar surface (particulate regolith) far better than Lambertian models, effectively normalizing extreme sun angle variations.
*   **FastAPI Backend**: Chosen for its high performance (async support), automatic OpenAPI (Swagger) documentation generation, and type safety using Pydantic, making pipeline integration and frontend communication robust.

## 6. Technology Stack

*   **Language:** Python 3.11+
*   **Deep Learning / Tensors:** PyTorch (SuperPoint, LightGlue)
*   **Image Processing:** OpenCV 4.x, scikit-image
*   **Geospatial / I/O:** GDAL, Rasterio
*   **Numerical:** NumPy, SciPy
*   **Backend / API:** FastAPI, Uvicorn, Pydantic
*   **Frontend:** React, Tailwind CSS
*   **Infrastructure:** Docker, Docker Compose
*   **Testing:** pytest

## 7. API Design

The RESTful API provides endpoints for job submission, monitoring, and retrieval of results.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/register` | `POST` | Start a new image registration job. Accepts image identifiers/files and returns a Job ID. |
| `/api/v1/jobs/{id}` | `GET` | Get the status of a specific registration job (e.g., Pending, Processing, Completed, Failed). |
| `/api/v1/jobs/{id}/matches` | `GET` | Retrieve the geometric match points (inliers/outliers) for visualization. |
| `/api/v1/jobs/{id}/metrics` | `GET` | Get quantitative evaluation metrics (RMSE, SSIM, etc.). |
| `/api/v1/preprocess` | `POST` | Run standalone preprocessing (radiometric/photometric normalization) without full registration. |
| `/api/v1/sensors` | `GET` | List supported Chandrayaan-2 sensors (OHRC, TMC, IIRS) and capabilities. |

## 8. Deployment Architecture

```mermaid
graph LR
    User([User Browser]) -->|HTTP:80/443| Nginx[Nginx Reverse Proxy]
    Nginx -->|HTTP:3000| UI[React UI Container]
    Nginx -->|HTTP:8000| API[FastAPI Container]
    
    API -->|Shared Volume| Data[Data Volume]
    API -.->|Spawns| Worker[Pipeline Worker Process]
    Worker -->|CUDA| GPU[GPU Device]
    Worker -->|Mount| Data
```

## 9. Performance Considerations

*   **GPU Acceleration**: Essential deep learning models (SuperPoint, LightGlue) and intensive matrix operations are offloaded to CUDA-enabled GPUs to drastically reduce processing time.
*   **Image Pyramid Strategy (Coarse-to-Fine)**: To handle massive high-resolution imagery (like OHRC), the system performs initial matching on down-sampled image pyramids, then refines the transform matrix on native resolution patches.
*   **Batch Processing**: The feature extraction and matching modules are vectorized and support batch processing to maximize GPU utilization.
*   **Grid Sampling**: Prevents localized dense matching and ensures a uniform spatial distribution of keypoints across the image, reducing computational load in MAGSAC++ while improving global transformation accuracy.

## 10. Security & Data Handling

*   **PDS4 Data Integrity**: Checksum validation and strict PDS4 schema compliance checks are enforced during the ingest phase to ensure raw data isn't corrupted.
*   **Audit Logging**: All API requests, job status changes, and pipeline errors are logged centrally for debugging and audit purposes.
*   **Ephemeral Processing Storage**: Intermediate artifacts generated during preprocessing and matching are stored in ephemeral volumes and routinely garbage-collected to prevent storage exhaustion.
*   **Input Validation**: Strict Pydantic schemas validate all inbound API payloads to prevent injection attacks and ensure robust type handling.
