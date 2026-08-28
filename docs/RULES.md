# LUMEN Project Rules & Conventions

**Project:** LUMEN - Lunar Multi-modal Engagement Network
**Description:** Multi-modal image registration for Chandrayaan-2 (OHRC, TMC-2, IIRS)

This document defines the engineering rules, coding standards, and project conventions that ALL contributors and AI models **MUST** follow when building the LUMEN project. The keywords "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

---

## 1. Code Style & Standards

*   **Python Version:** Follow PEP 8. Use Python 3.10+ syntax for type hints everywhere (e.g., `X | None` instead of `Optional[X]`).
*   **Linting & Formatting:** Use `ruff` for linting and formatting. Line length MUST be strictly 100 characters.
*   **Docstrings:** Google style docstrings are MANDATORY for all public functions, classes, and methods.
*   **Exports:** All modules MUST have `__all__` exports defined to explicitly state the public API.
*   **Paths:** Use `pathlib.Path` exclusively. `os.path` MUST NOT be used.
*   **Logging:** Use the standard `logging` module. `print()` MUST NOT be used in library code.
*   **Data Structures:** Use `dataclasses` or `pydantic` models for structured data.
*   **Async Operations:** Use `async`/`await` for all I/O-bound operations within the API layer.

### Example
```python
from pathlib import Path
from dataclasses import dataclass
import logging

__all__ = ["load_image_metadata"]

logger = logging.getLogger(__name__)

@dataclass
class ImageMetadata:
    path: Path
    width: int
    height: int

def load_image_metadata(file_path: Path | None = None) -> ImageMetadata | None:
    """Loads metadata for a given image file.

    Args:
        file_path: The absolute path to the image file.

    Returns:
        The extracted metadata or None if the file is invalid.
    """
    if not file_path or not file_path.exists():
        logger.error(f"File not found: %s", file_path)
        return None
    # Implementation...
    return ImageMetadata(path=file_path, width=1024, height=1024)
```

## 2. Project Structure Rules

*   **Modularity:** Each module (e.g., `ingest`, `preprocess`, `features`, `geometry`) MUST be independently importable.
*   **Public API:** Each module MUST have its own `__init__.py` exposing a clean public API.
*   **Configuration:** Configuration MUST be handled via environment variables and YAML config files. Hardcoded configuration values are FORBIDDEN.
*   **Path Resolution:** All paths MUST be relative to the project root. Use the `lumen.config.PATHS` constants for consistent path resolution.
*   **Test Structure:** The `tests/` directory MUST mirror the source structure exactly (e.g., `tests/test_<module>.py`).

## 3. Data Handling Rules

*   **Immutability:** You MUST NEVER modify raw data files. The `data/raw/` directory is strictly read-only.
*   **Intermediate Results:** All intermediate and processed results MUST be written to `data/processed/`.
*   **Lazy Loading:** Use lazy loading for large images. Memory-mapped arrays SHOULD be used when possible.
*   **Metadata Preservation:** Metadata MUST be preserved throughout the entire processing pipeline.
*   **Coordinate Systems:** Always use selenographic coordinates internally.
*   **Image Arrays:** Image arrays MUST always be converted to `float32` and normalized to the range `[0, 1]` for processing.
*   **Validation:** You MUST always validate PDS4 labels against the schema before any processing begins.

## 4. Algorithm Rules

*   **Feature Matching:** You MUST always resample images to a common Ground Sample Distance (GSD) before attempting feature matching.
*   **Geometric Estimation:** A minimum of 4 match points is REQUIRED before attempting geometric estimation.
*   **Outlier Rejection:** You MUST run MAGSAC++ (not RANSAC) for outlier rejection.
*   **Refinement:** Sub-pixel refinement is MANDATORY for the final output.
*   **Grid Sampling:** Grid sampling SHOULD ensure ≥1 match per grid cell when possible.
*   **Photometry:** Photometric normalization MUST be applied BEFORE feature extraction.
*   **Orthorectification:** DEM orthorectification SHOULD be attempted when a valid DEM is available.

## 5. API Rules

*   **Routing:** All endpoints MUST be placed under the `/api/v1/` prefix.
*   **Validation:** Use Pydantic v2 models for all request and response validation.
*   **Status Codes:** Return proper HTTP status codes (e.g., `201 Created` for creation, `202 Accepted` for async jobs).
*   **Long-Running Jobs:** Long-running operations MUST be asynchronous with job status polling mechanisms.
*   **Tracing:** All API responses MUST include a `request_id` header or field for tracing.
*   **Rate Limiting:** A rate limit of 10 requests/minute MUST be enforced for registration jobs.
*   **Uploads:** File uploads MUST validate both file type and size before any processing occurs.

## 6. Frontend Rules

*   **Design System:** Follow the 'Lunar Operations Command' design system strictly.
*   **Grid System:** All measurements MUST align on a 4px grid.
*   **Typography:**
    *   Use **JetBrains Mono** for ALL numerical and telemetry data.
    *   Use **Space Grotesk** for headlines only.
    *   Use **Geist** for body text.
*   **Styling:**
    *   No `border-radius` on primary containers (use 0px sharp corners).
    *   The primary accent color is ONLY `#ffc174` (Telemetry Amber).
    *   All panels MUST have a Module ID in the top-right corner.
*   **Theme:** The application MUST be dark theme only. Light mode is NOT supported.

## 7. Testing Rules

*   **Coverage:** A minimum of 80% code coverage is REQUIRED.
*   **Unit Tests:** Unit tests MUST be written for all pure functions.
*   **Integration Tests:** Integration tests MUST be written for all pipeline stages.
*   **Test Data:** Use `pytest` fixtures for managing test data.
*   **Mocking:** External services (e.g., PRADAN downloads) MUST be mocked during testing.
*   **Performance:** Core algorithms SHOULD have automated performance benchmarks.
*   **Regression:** Regression tests MUST be included for accuracy metrics.

## 8. Git Rules

*   **Branch Naming:** Branches MUST follow the naming convention: `feature/<name>`, `fix/<name>`, or `docs/<name>`.
*   **Commit Messages:** Commit messages MUST follow the Conventional Commits format (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).
*   **Pull Requests:** The PR template MUST be filled out completely, including: What, Why, How, Testing, and Screenshots.
*   **History:** Force pushes to the `main` branch are strictly FORBIDDEN.
*   **Merging:** Only squash merges are allowed into the `main` branch.

## 9. Documentation Rules

*   **README:** A comprehensive `README.md` with Quick Start, Installation, and Usage instructions is REQUIRED.
*   **Location:** All documentation MUST reside in the `docs/` directory.
*   **API Docs:** API documentation MUST be auto-generated from the FastAPI OpenAPI schema.
*   **Notebooks:** Jupyter notebooks MUST be executable and fully documented.
*   **ADRs:** Architecture Decision Records (ADRs) MUST be created for all major architectural decisions.

## 10. Performance Rules

*   **Profiling:** You MUST profile the application before attempting to optimize it.
*   **Multi-scale Processing:** Use image pyramids for multi-scale processing.
*   **GPU Batching:** GPU operations SHOULD be batched where possible.
*   **Caching:** Preprocessed images SHOULD be cached to avoid redundant computation.
*   **Weights:** Lazy load model weights to reduce initial memory overhead.

## 11. Security Rules

*   **Credentials:** There MUST be NO credentials stored in code or configuration files.
*   **Secrets:** Use environment variables for all secrets.
*   **Validation:** All user inputs MUST be strictly validated.
*   **Path Traversal:** File paths MUST be sanitized to prevent directory traversal attacks.
*   **Docker:** Docker containers MUST run as a non-root user.

---

## Rules Compliance Checklist

- [ ] I have read and understood the LUMEN Rules document.
- [ ] My code follows Python PEP 8, uses type hints, and passes `ruff` with a 100 character line limit.
- [ ] All my functions and classes have Google style docstrings.
- [ ] I am using `pathlib.Path` for all file operations.
- [ ] I have not used `print()` in any library code.
- [ ] Raw data files in `data/raw/` are completely unmodified by my code.
- [ ] My API endpoints are under `/api/v1/` and use Pydantic models.
- [ ] My frontend code strictly adheres to the 'Lunar Operations Command' design system (fonts, colors, corners).
- [ ] I have written tests achieving at least 80% coverage for my new code.
- [ ] My branch name and commit messages follow the required conventions.
- [ ] I have not committed any credentials or secrets.
