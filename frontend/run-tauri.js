import { fileURLToPath } from "node:url";
import path from "node:path";
import os from "node:os";
import { spawn } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Ensure Cargo and MinGW compiler are present on PATH in any terminal session
const cargoBin = path.join(os.homedir(), ".cargo", "bin");
const mingwBin = path.join(
  os.homedir(),
  "AppData",
  "Local",
  "Microsoft",
  "WinGet",
  "Packages",
  "BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe",
  "mingw64",
  "bin"
);

const currentPath = process.env.PATH || "";
const pathParts = [cargoBin, mingwBin, currentPath].filter(Boolean);
const combinedPath = pathParts.join(path.delimiter);

const args = process.argv.slice(2);
const tauriBin = path.join(__dirname, "node_modules", "@tauri-apps", "cli", "tauri.js");

const child = spawn(process.execPath, [tauriBin, ...args], {
  cwd: __dirname,
  stdio: "inherit",
  env: {
    ...process.env,
    PATH: combinedPath,
  },
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
