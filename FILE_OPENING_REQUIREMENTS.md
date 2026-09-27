# File Opening Requirements for Future UI Migration

This document records the UX and architectural requirements for source file opening during future migration phases.

## 1. Core Principles
* **Controlled In-App Interaction**:
  * The application must provide a controlled in-app interaction when selecting or viewing a problem/source file (e.g., viewing problem details, previewing metadata/code, and offering explicit file actions).
  * Do **NOT** immediately force the Windows "Open With" chooser upon clicking or selecting a problem file.
* **Security & Validation**:
  * Retain all path safety validations (`validate_file_for_open`):
    * File must exist within the configured repository boundaries (no directory traversal).
    * File must have a supported source code extension (`.cpp`, `.java`, `.py`).
* **Phase Boundary**:
  * Do **NOT** modify existing file-opening behavior in the current phase.
  * This interaction design will be implemented and refined during the Search / Problem Detail UI migration phase.
