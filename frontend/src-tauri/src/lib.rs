use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::State;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

/// Holds the long-lived Python bridge subprocess.
struct BridgeState {
    process: Mutex<Option<Child>>,
}

/// Spawn the Python bridge server as a long-lived child process.
/// Returns the readiness signal or an error message.
fn spawn_bridge() -> Result<Child, String> {
    // Find the bridge script relative to the executable or project root.
    // In dev mode, the exe is in frontend/src-tauri/target/debug/
    // The bridge is at DSAORGANIZER/bridge/bridge_server.py
    // We walk up from the executable to find the project root.
    let bridge_script = find_bridge_script()?;

    log::info!("Spawning Python bridge: python {}", bridge_script.display());

    let mut cmd = Command::new("python");
    cmd.arg(&bridge_script)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .current_dir(bridge_script.parent().unwrap().parent().unwrap()); // project root

    // Hide console window on Windows
    #[cfg(windows)]
    cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Failed to spawn Python bridge: {}", e))?;

    // Read the readiness signal from the bridge
    {
        let stdout = child.stdout.as_mut().ok_or("No stdout from bridge")?;
        let mut reader = BufReader::new(stdout);
        let mut init_line = String::new();
        reader
            .read_line(&mut init_line)
            .map_err(|e| format!("Failed to read bridge init signal: {}", e))?;

        let init_resp: Value = serde_json::from_str(&init_line)
            .map_err(|e| format!("Invalid bridge init response: {} (got: {})", e, init_line))?;

        if init_resp["ok"].as_bool() != Some(true) {
            return Err(format!("Bridge init failed: {}", init_resp));
        }

        log::info!("Python bridge ready: {}", init_resp);
    }

    Ok(child)
}

/// Locate the bridge_server.py script by walking up from the executable.
fn find_bridge_script() -> Result<std::path::PathBuf, String> {
    // Strategy: try common locations relative to the current exe
    let exe_path = std::env::current_exe().map_err(|e| format!("Cannot find exe path: {}", e))?;
    let exe_dir = exe_path.parent().unwrap();

    // In dev mode: exe is at frontend/src-tauri/target/debug/app.exe
    // Project root is 4 levels up: debug -> target -> src-tauri -> frontend -> DSAORGANIZER
    let candidates = [
        // Dev mode: walk up from target/debug
        exe_dir
            .join("..")
            .join("..")
            .join("..")
            .join("..")
            .join("bridge")
            .join("bridge_server.py"),
        // Alternative: from src-tauri parent
        exe_dir
            .join("..")
            .join("..")
            .join("..")
            .join("bridge")
            .join("bridge_server.py"),
        // From exe_dir itself (bundled)
        exe_dir.join("bridge").join("bridge_server.py"),
        // Env var override
        std::env::var("DSA_BRIDGE_SCRIPT")
            .map(std::path::PathBuf::from)
            .unwrap_or_default(),
    ];

    for candidate in &candidates {
        let resolved = candidate.canonicalize().unwrap_or_default();
        if resolved.exists() && resolved.is_file() {
            log::info!("Found bridge script at: {}", resolved.display());
            return Ok(resolved);
        }
    }

    Err(format!(
        "Could not find bridge/bridge_server.py. Searched from: {}. \
         Set DSA_BRIDGE_SCRIPT env var to override.",
        exe_dir.display()
    ))
}

/// Send a JSON command to the Python bridge and return the JSON response.
#[tauri::command]
fn bridge_command(
    state: State<BridgeState>,
    cmd: String,
    args: Value,
    id: String,
) -> Result<Value, String> {
    let mut guard = state
        .process
        .lock()
        .map_err(|e| format!("Lock error: {}", e))?;

    let child = guard
        .as_mut()
        .ok_or("Python bridge is not running")?;

    // Build request JSON
    let request = serde_json::json!({
        "id": id,
        "cmd": cmd,
        "args": args,
    });

    // Write to stdin
    {
        let stdin = child
            .stdin
            .as_mut()
            .ok_or("Bridge stdin not available")?;
        let line = request.to_string() + "\n";
        stdin
            .write_all(line.as_bytes())
            .map_err(|e| format!("Failed to write to bridge: {}", e))?;
        stdin
            .flush()
            .map_err(|e| format!("Failed to flush bridge stdin: {}", e))?;
    }

    // Read response from stdout
    let response_line = {
        let stdout = child
            .stdout
            .as_mut()
            .ok_or("Bridge stdout not available")?;
        let mut reader = BufReader::new(stdout);
        let mut line = String::new();
        reader
            .read_line(&mut line)
            .map_err(|e| format!("Failed to read bridge response: {}", e))?;
        line
    };

    let response: Value = serde_json::from_str(&response_line)
        .map_err(|e| format!("Invalid bridge response JSON: {} (got: {})", e, response_line))?;

    Ok(response)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Spawn the bridge process before building the Tauri app
    let bridge_child = match spawn_bridge() {
        Ok(child) => {
            log::info!("Python bridge spawned successfully (PID: {:?})", child.id());
            Some(child)
        }
        Err(e) => {
            log::error!("Failed to spawn Python bridge: {}", e);
            eprintln!("[tauri] WARNING: Python bridge failed to start: {}", e);
            None
        }
    };

    tauri::Builder::default()
        .manage(BridgeState {
            process: Mutex::new(bridge_child),
        })
        .invoke_handler(tauri::generate_handler![bridge_command])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
