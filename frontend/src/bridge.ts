/**
 * bridge.ts — Typed wrappers for calling the Python engine through Tauri.
 *
 * All frontend code should use these functions instead of invoking
 * Tauri commands directly. This provides a single place for:
 * - Type definitions
 * - Request ID generation
 * - Error handling
 */

import { invoke } from "@tauri-apps/api/core";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Standard bridge response envelope from the Python bridge server. */
export interface BridgeResponse<T = unknown> {
  id: string;
  ok: boolean;
  data: T | null;
  error: string | null;
}

/** Project configuration from project.json. */
export interface ProjectConfig {
  repository?: string;
  repository_path?: string;
  default_language?: string;
  platforms?: { custom: string[] };
  categories?: { custom: string[] };
  tags?: { custom: string[] };
  git?: { remote_name: string; remote_url: string };
}

/** Repository validation result. */
export interface ValidateResult {
  valid: boolean;
  message: string;
}

/** Repository scan result. */
export interface ScanResult {
  success: boolean;
  repo_path?: string;
  total_problems: number;
  complete_count: number;
  incomplete_count: number;
  unreadable_count: number;
  mismatch_count: number;
  problems: ProblemRecord[];
  error?: string;
}

/** Individual problem record from a scan. */
export interface ProblemRecord {
  file_path: string;
  rel_path: string;
  filename: string;
  title: string;
  language: string;
  platform: string;
  category: string;
  folder_category: string;
  status: "complete" | "incomplete" | "unreadable";
  is_complete: boolean;
  missing_fields: string[];
  category_mismatch: boolean;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Request ID generation
// ---------------------------------------------------------------------------

let _reqCounter = 0;

function nextId(prefix: string): string {
  _reqCounter += 1;
  return `${prefix}-${_reqCounter}-${Date.now()}`;
}

// ---------------------------------------------------------------------------
// Core bridge call
// ---------------------------------------------------------------------------

/**
 * Send a command to the Python bridge through Tauri.
 * Returns the parsed response or throws on communication errors.
 */
async function callBridge<T = unknown>(
  cmd: string,
  args: Record<string, unknown> = {}
): Promise<BridgeResponse<T>> {
  const id = nextId(cmd);

  const response = await invoke<BridgeResponse<T>>("bridge_command", {
    cmd,
    args,
    id,
  });

  return response;
}

// ---------------------------------------------------------------------------
// Domain-level API functions
// ---------------------------------------------------------------------------

/** Health check — verify the bridge is alive. */
export async function ping(): Promise<BridgeResponse<{ status: string; message: string }>> {
  return callBridge("ping");
}

/** Load project.json configuration. */
export async function loadConfig(): Promise<
  BridgeResponse<{ success: boolean; error: string | null; config: ProjectConfig | null }>
> {
  return callBridge("load_config");
}

/** Validate whether the repository path is accessible. */
export async function validateRepository(
  repoPath?: string
): Promise<BridgeResponse<ValidateResult>> {
  return callBridge("validate_repository", repoPath ? { repo_path: repoPath } : {});
}

/** Scan the repository for all problem files and metadata. */
export async function scanRepository(repoPath?: string): Promise<BridgeResponse<ScanResult>> {
  return callBridge("scan_repository", repoPath ? { repo_path: repoPath } : {});
}

/** Get dashboard statistics. */
export async function getDashboardStats(
  repoPath?: string
): Promise<BridgeResponse<Record<string, unknown>>> {
  return callBridge("get_dashboard_stats", repoPath ? { repo_path: repoPath } : {});
}

/** Get all available categories. */
export async function getCategories(): Promise<
  BridgeResponse<{ categories: string[] }>
> {
  return callBridge("get_categories");
}

/** Get all available platforms. */
export async function getAllPlatforms(): Promise<
  BridgeResponse<{ platforms: string[] }>
> {
  return callBridge("get_all_platforms");
}

/** Get all available tags. */
export async function getAllTags(): Promise<
  BridgeResponse<{ tags: string[] }>
> {
  return callBridge("get_all_tags");
}

/** Ensure core project directories exist. */
export async function ensureDirectories(): Promise<
  BridgeResponse<{ success: boolean; message: string }>
> {
  return callBridge("ensure_directories");
}

/** Verify Git availability and configuration. */
export async function verifyGit(
  repoPath?: string
): Promise<BridgeResponse<Record<string, unknown>>> {
  return callBridge("verify_git", repoPath ? { repo_path: repoPath } : {});
}
