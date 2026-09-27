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

/** Individual problem record from a scan or recent problems. */
export interface ProblemRecord {
  file_path: string;
  rel_path: string;
  filename?: string;
  title: string;
  language: string;
  platform: string;
  category: string;
  folder_category?: string;
  status: "complete" | "incomplete" | "unreadable";
  is_complete?: boolean;
  missing_fields?: string[];
  category_mismatch?: boolean;
  metadata?: Record<string, unknown>;
  added_date?: string;
  parsed_date?: string | null;
  formatted_date?: string;
}

/** Single day data point inside a 12-week activity heatmap. */
export interface HeatmapDay {
  date: string;
  formatted_date: string;
  day_name: string;
  day_number: number;
  month_name: string;
  count: number;
  level: number; // 0 (empty) to 4 (high activity)
  is_today: boolean;
  is_future: boolean;
}

/** Comprehensive dashboard statistics returned by get_dashboard_stats. */
export interface DashboardStats {
  success: boolean;
  repo_path?: string;
  total_problems: number;
  this_week: number;
  this_month: number;
  current_streak: number;
  longest_streak: number;
  category_counts: Record<string, number>;
  most_practiced_categories: [string, number][];
  least_practiced_categories: [string, number][];
  recent_problems: ProblemRecord[];
  activity_by_date: Record<string, number>;
  heatmap_weeks: HeatmapDay[][];
  problems?: ProblemRecord[];
  error?: string;
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
 * Generate mock heatmap weeks for browser preview.
 */
function generateMockHeatmapWeeks(): HeatmapDay[][] {
  const weeks: HeatmapDay[][] = [];
  const today = new Date();
  // Generate 84 days (12 weeks)
  const days: HeatmapDay[] = [];
  for (let i = 83; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const dateStr = d.toISOString().split("T")[0];
    const isToday = i === 0;
    // Simulate some realistic activity
    const rand = (i * 17 + 3) % 10;
    const count = rand > 6 ? (rand - 6) * 2 : 0;
    const level = count === 0 ? 0 : count <= 1 ? 1 : count <= 2 ? 2 : count <= 4 ? 3 : 4;
    days.push({
      date: dateStr,
      formatted_date: d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
      day_name: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()],
      day_number: d.getDay(),
      month_name: d.toLocaleDateString("en-US", { month: "short" }),
      count,
      level,
      is_today: isToday,
      is_future: false,
    });
  }
  for (let w = 0; w < 12; w++) {
    weeks.push(days.slice(w * 7, (w + 1) * 7));
  }
  return weeks;
}

/**
 * Send a command to the Python bridge through Tauri.
 * In a browser development environment outside Tauri, provides a fallback.
 */
async function callBridge<T = unknown>(
  cmd: string,
  args: Record<string, unknown> = {}
): Promise<BridgeResponse<T>> {
  const id = nextId(cmd);

  // If running in browser dev mode outside Tauri webview
  if (typeof window !== "undefined" && !(window as any).__TAURI_INTERNALS__) {
    console.info(`[Browser Dev Fallback] Bridge call: ${cmd}`, args);
    if (cmd === "load_config") {
      return {
        id,
        ok: true,
        data: {
          success: true,
          error: null,
          config: {
            repository: "C:\\Users\\jonna\\OneDrive\\Documents\\DSAORGANIZER\\repo",
            default_language: "C++",
          },
        } as unknown as T,
        error: null,
      };
    }
    if (cmd === "get_dashboard_stats") {
      const heatmap = generateMockHeatmapWeeks();
      const stats: DashboardStats = {
        success: true,
        repo_path: "C:\\Users\\jonna\\OneDrive\\Documents\\DSAORGANIZER\\repo",
        total_problems: 18,
        this_week: 4,
        this_month: 12,
        current_streak: 3,
        longest_streak: 7,
        category_counts: {
          Arrays: 6,
          "Dynamic Programming": 4,
          Trees: 3,
          Strings: 3,
          Graphs: 2,
        },
        most_practiced_categories: [
          ["Arrays", 6],
          ["Dynamic Programming", 4],
          ["Trees", 3],
        ],
        least_practiced_categories: [
          ["Graphs", 2],
          ["Strings", 3],
          ["Trees", 3],
        ],
        recent_problems: [
          {
            file_path: "Arrays/TwoSum.cpp",
            rel_path: "Arrays/TwoSum.cpp",
            title: "Two Sum",
            language: "C++",
            platform: "LeetCode",
            category: "Arrays",
            status: "complete",
            added_date: "2026-09-27",
            formatted_date: "Sep 27, 2026",
          },
          {
            file_path: "Dynamic Programming/CoinChange.py",
            rel_path: "Dynamic Programming/CoinChange.py",
            title: "Coin Change",
            language: "Python",
            platform: "LeetCode",
            category: "Dynamic Programming",
            status: "complete",
            added_date: "2026-09-26",
            formatted_date: "Sep 26, 2026",
          },
          {
            file_path: "Trees/InvertBinaryTree.java",
            rel_path: "Trees/InvertBinaryTree.java",
            title: "Invert Binary Tree",
            language: "Java",
            platform: "LeetCode",
            category: "Trees",
            status: "complete",
            added_date: "2026-09-25",
            formatted_date: "Sep 25, 2026",
          },
          {
            file_path: "Graphs/NumberOfIslands.cpp",
            rel_path: "Graphs/NumberOfIslands.cpp",
            title: "Number of Islands",
            language: "C++",
            platform: "LeetCode",
            category: "Graphs",
            status: "complete",
            added_date: "2026-09-22",
            formatted_date: "Sep 22, 2026",
          },
          {
            file_path: "Strings/LongestSubstring.py",
            rel_path: "Strings/LongestSubstring.py",
            title: "Longest Substring Without Repeating Characters",
            language: "Python",
            platform: "LeetCode",
            category: "Strings",
            status: "complete",
            added_date: "2026-09-20",
            formatted_date: "Sep 20, 2026",
          },
        ],
        activity_by_date: {},
        heatmap_weeks: heatmap,
      };
      return { id, ok: true, data: stats as unknown as T, error: null };
    }
    if (cmd === "scan_repository") {
      return {
        id,
        ok: true,
        data: {
          success: true,
          total_problems: 18,
          complete_count: 18,
          incomplete_count: 0,
          unreadable_count: 0,
          mismatch_count: 0,
          problems: [],
        } as unknown as T,
        error: null,
      };
    }
    return { id, ok: true, data: {} as unknown as T, error: null };
  }

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
): Promise<BridgeResponse<DashboardStats>> {
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
