# Desktop Architecture & Packaging Requirements

## 1. Product Format & Distribution
* **Target Platform**: Windows Desktop (native 64-bit application).
* **Delivery Artifact**: Standalone `.exe` (and optionally an MSI/NSIS installer).
* **Execution Model**: Self-contained desktop application.
  * Must **NOT** require an external web browser.
  * Must **NOT** require `localhost` or dev servers in production.
  * Must **NOT** require `Vite`, `Node.js`, `npm`, or developer tooling on end-user machines.

## 2. Frontend Build & Asset Embedding
* **Vite & Localhost**: Strictly development-mode mechanisms (`tauri dev`).
* **Production Packaging**: Tauri builds embed the compiled static HTML/CSS/JS (`frontend/dist/`) directly into the application executable.
* **Dependencies**:
  * `frontend/node_modules/` is strictly a build-time dependency cache.
  * `node_modules` must never be committed to Git (enforced in `.gitignore`) and must never be shipped in application distributions.
  * `package.json` and `package-lock.json` are tracked in source control to ensure deterministic frontend builds.

## 3. Python Backend & Sidecar Requirements (Future Packaging Phase)
* **Current Development State**: Tauri invokes `python` via the development environment to run `bridge/bridge_server.py`.
* **Hardcoded Paths Prohibited**: The current developer's Python path or virtual environment path must never become a production dependency.
* **Future Packaging Task (Required)**:
  * Provide a bundled, self-contained Python runtime or standalone sidecar (e.g., PyInstaller standalone sidecar executable, PyEmbed portable runtime, or compiled binary).
  * Ensure the standalone desktop executable runs on a clean Windows machine without requiring the user to install Python, virtual environments, or pip dependencies.
  * The Tauri bridge must detect and spawn the bundled sidecar runtime when running in packaged mode, falling back to development python discovery only during dev mode.
