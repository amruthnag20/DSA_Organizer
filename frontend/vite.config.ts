import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://v2.tauri.app/start/frontend/vite/
const host = process.env.TAURI_DEV_HOST;

export default defineConfig({
  plugins: [react()],

  // Vite dev server config for Tauri
  server: {
    host: host || "localhost",
    port: 5173,
    strictPort: true,
    // Tauri expects a fixed port
    watch: {
      // Don't watch the Python engine or test files
      ignored: ["**/engine/**", "**/bridge/**", "**/*.py", "**/src-tauri/**"],
    },
  },

  // Prevent Vite from obscuring Rust errors
  clearScreen: false,

  // Environment variables starting with TAURI_ are available in the frontend
  envPrefix: ["VITE_", "TAURI_"],

  build: {
    // Tauri uses Chromium on Windows and WebKit on macOS/Linux
    target:
      process.env.TAURI_ENV_PLATFORM == "windows"
        ? "chrome105"
        : ["es2022", "chrome105"],
    // Disable minification in debug builds for better error messages
    minify: !process.env.TAURI_ENV_DEBUG ? "esbuild" : false,
    // Produce sourcemaps for debug builds
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
  },
});
