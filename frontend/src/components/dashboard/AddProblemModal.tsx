import React, { useState, useEffect } from "react";
import {
  addProblem,
  analyzeComplexity,
  getMetadataOptions,
  saveCustomCategory,
  type AddProblemPayload,
  type ComplexityResult,
} from "../../bridge";

interface AddProblemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (filePath: string, title: string, category: string) => void;
  repoPath?: string;
}

export const AddProblemModal: React.FC<AddProblemModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  repoPath,
}) => {
  // Form State
  const [title, setTitle] = useState("");
  const [platform, setPlatform] = useState("LeetCode");
  const [customPlatform, setCustomPlatform] = useState("");
  const [language, setLanguage] = useState("C++");
  const [category, setCategory] = useState("Arrays");
  const [newCustomCategory, setNewCustomCategory] = useState("");
  const [showAddCategory, setShowAddCategory] = useState(false);
  const [description, setDescription] = useState("");
  const [solutionCode, setSolutionCode] = useState("");
  const [concepts, setConcepts] = useState("");
  const [dataStructures, setDataStructures] = useState("");
  const [tags, setTags] = useState("");
  const [importance, setImportance] = useState<number>(3);

  // Dynamic Options from Backend
  const [platformsList, setPlatformsList] = useState<string[]>([
    "LeetCode",
    "CodeChef",
    "HackerRank",
    "Codeforces",
    "GeeksForGeeks",
    "Other",
  ]);
  const [categoriesList, setCategoriesList] = useState<string[]>([
    "Arrays",
    "Strings",
    "LinkedLists",
    "Stacks",
    "Queues",
    "Hashing",
    "Trees",
    "Graphs",
    "Heaps",
    "Recursion",
    "Backtracking",
    "Sorting",
    "Searching",
    "Greedy",
    "DynamicProgramming",
    "Uncategorized",
  ]);
  const [builtinTagsList, setBuiltinTagsList] = useState<string[]>([
    "Interview",
    "Important",
    "Revision",
    "Tricky",
    "Must-Do",
    "Pattern",
  ]);
  const [builtinConceptsList, setBuiltinConceptsList] = useState<string[]>([]);
  const [builtinDsList, setBuiltinDsList] = useState<string[]>([]);

  // Complexity Preview
  const [complexity, setComplexity] = useState<ComplexityResult | null>(null);
  const [analyzingComplexity, setAnalyzingComplexity] = useState(false);

  // Submission State
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Load available options from backend when modal opens
  useEffect(() => {
    if (!isOpen) return;

    // Reset error / success
    setError(null);
    setSuccessMsg(null);

    async function loadOptions() {
      try {
        const resp = await getMetadataOptions();
        if (resp.ok && resp.data) {
          const d = resp.data;
          if (d.platforms?.length) setPlatformsList(d.platforms);
          if (d.categories?.length) setCategoriesList(d.categories);
          if (d.tags?.length) setBuiltinTagsList(d.tags);
          if (d.concepts?.length) setBuiltinConceptsList(d.concepts);
          if (d.data_structures?.length) setBuiltinDsList(d.data_structures);
        }
      } catch (err) {
        console.warn("Could not load backend metadata options:", err);
      }
    }
    loadOptions();
  }, [isOpen]);

  if (!isOpen) return null;

  // Append token to comma-separated list
  const addToken = (
    current: string,
    setFunc: React.Dispatch<React.SetStateAction<string>>,
    token: string
  ) => {
    const tokens = current
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    if (!tokens.some((t) => t.toLowerCase() === token.toLowerCase())) {
      tokens.push(token);
      setFunc(tokens.join(", "));
    }
  };

  // Preview Complexity
  const handlePreviewComplexity = async () => {
    if (!solutionCode.trim()) {
      setError("Please enter solution code first to preview complexity.");
      return;
    }
    setError(null);
    setAnalyzingComplexity(true);
    try {
      const resp = await analyzeComplexity(language, solutionCode);
      if (resp.ok && resp.data) {
        setComplexity(resp.data);
      } else {
        setError(resp.error || "Complexity analysis failed.");
      }
    } catch (err: unknown) {
      setError(`Complexity analysis error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setAnalyzingComplexity(false);
    }
  };

  // Save new custom category
  const handleCreateCustomCategory = async () => {
    const cleanName = newCustomCategory.trim();
    if (!cleanName) return;

    try {
      const resp = await saveCustomCategory(cleanName);
      if (resp.ok && resp.data?.success) {
        setCategoriesList((prev) => [...prev, cleanName]);
        setCategory(cleanName);
        setNewCustomCategory("");
        setShowAddCategory(false);
      } else {
        setError(resp.error || resp.data?.message || "Failed to save custom category.");
      }
    } catch (err: unknown) {
      setError(`Error saving custom category: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  // Submit Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    // Front-end validations matching backend requirements
    const cleanTitle = title.trim();
    if (!cleanTitle) {
      setError("Problem title is required.");
      return;
    }
    if (cleanTitle.includes("..")) {
      setError("Unsafe problem title: path traversal ('..') is not permitted.");
      return;
    }

    if (platform === "Other" && !customPlatform.trim()) {
      setError("Please specify the custom platform name.");
      return;
    }

    if (!description.trim()) {
      setError("Problem description is required.");
      return;
    }

    if (!solutionCode.trim()) {
      setError("Solution code is required.");
      return;
    }

    setSubmitting(true);

    const payload: AddProblemPayload = {
      title: cleanTitle,
      platform,
      custom_platform: platform === "Other" ? customPlatform.trim() : undefined,
      language,
      category,
      description: description.trim(),
      solution_code: solutionCode,
      concepts: concepts.trim() || undefined,
      data_structures: dataStructures.trim() || undefined,
      tags: tags.trim() || undefined,
      importance,
      repo_path: repoPath,
    };

    try {
      const resp = await addProblem(payload);
      if (resp.ok && resp.data && resp.data.success) {
        setSuccessMsg(resp.data.message || "Problem created successfully.");
        const createdFile = resp.data.file_path || "";
        setTimeout(() => {
          onSuccess(createdFile, cleanTitle, category);
          onClose();
        }, 800);
      } else {
        setError(resp.error || resp.data?.message || "Failed to create problem file.");
      }
    } catch (err: unknown) {
      setError(`Failed to create problem: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container add-problem-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-box">
            <h2 className="modal-title">Add New Problem</h2>
            <span className="modal-subtitle">
              Standardized metadata generation & physical verification
            </span>
          </div>
          <button className="modal-close-btn" onClick={onClose} disabled={submitting}>
            ✕
          </button>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="modal-notice notice-error">
            <span className="notice-icon">⚠️</span>
            <span className="notice-text">{error}</span>
          </div>
        )}
        {successMsg && (
          <div className="modal-notice notice-success">
            <span className="notice-icon">✓</span>
            <span className="notice-text">{successMsg}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="add-problem-form">
          <div className="modal-scrollable-body">
            <div className="form-grid">
              {/* ── Left Column: Metadata & Classification ── */}
              <div className="form-col left-col">
                {/* Title */}
                <div className="form-group">
                  <label className="form-label" htmlFor="prob-title">
                    Problem Title <span className="required-star">*</span>
                  </label>
                  <input
                    id="prob-title"
                    type="text"
                    className="form-input"
                    placeholder="e.g. Two Sum"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    disabled={submitting}
                    autoFocus
                  />
                </div>

                {/* Platform & Language Row */}
                <div className="form-row-2">
                  <div className="form-group">
                    <label className="form-label" htmlFor="prob-platform">
                      Platform <span className="required-star">*</span>
                    </label>
                    <select
                      id="prob-platform"
                      className="form-select"
                      value={platform}
                      onChange={(e) => setPlatform(e.target.value)}
                      disabled={submitting}
                    >
                      {platformsList.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="prob-lang">
                      Language <span className="required-star">*</span>
                    </label>
                    <select
                      id="prob-lang"
                      className="form-select"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      disabled={submitting}
                    >
                      <option value="C++">C++ (.cpp)</option>
                      <option value="Java">Java (.java)</option>
                      <option value="Python">Python (.py)</option>
                    </select>
                  </div>
                </div>

                {/* Custom Platform Input (if Other) */}
                {platform === "Other" && (
                  <div className="form-group">
                    <label className="form-label" htmlFor="prob-custom-plat">
                      Custom Platform Name <span className="required-star">*</span>
                    </label>
                    <input
                      id="prob-custom-plat"
                      type="text"
                      className="form-input"
                      placeholder="e.g. Codeforces Gym"
                      value={customPlatform}
                      onChange={(e) => setCustomPlatform(e.target.value)}
                      disabled={submitting}
                    />
                  </div>
                )}

                {/* Category Selection */}
                <div className="form-group">
                  <div className="label-with-action">
                    <label className="form-label" htmlFor="prob-category">
                      Primary Category <span className="required-star">*</span>
                    </label>
                    <button
                      type="button"
                      className="text-action-btn"
                      onClick={() => setShowAddCategory(!showAddCategory)}
                    >
                      {showAddCategory ? "Cancel" : "+ New Category"}
                    </button>
                  </div>

                  {showAddCategory ? (
                    <div className="inline-add-box">
                      <input
                        type="text"
                        className="form-input"
                        placeholder="New category name"
                        value={newCustomCategory}
                        onChange={(e) => setNewCustomCategory(e.target.value)}
                      />
                      <button
                        type="button"
                        className="action-btn primary-action-btn btn-sm"
                        onClick={handleCreateCustomCategory}
                      >
                        Add
                      </button>
                    </div>
                  ) : (
                    <select
                      id="prob-category"
                      className="form-select"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      disabled={submitting}
                    >
                      {categoriesList.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                {/* Importance (1 to 5) */}
                <div className="form-group">
                  <label className="form-label">
                    Importance Level (1 = Low, 5 = High)
                  </label>
                  <div className="importance-selector">
                    {[1, 2, 3, 4, 5].map((lvl) => (
                      <button
                        key={lvl}
                        type="button"
                        className={`importance-btn ${importance === lvl ? "selected" : ""}`}
                        onClick={() => setImportance(lvl)}
                        disabled={submitting}
                      >
                        {lvl}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Tags (User-Provided) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="prob-tags">
                    Tags (Comma-separated)
                  </label>
                  <input
                    id="prob-tags"
                    type="text"
                    className="form-input"
                    placeholder="e.g. Interview, Tricky, Revision"
                    value={tags}
                    onChange={(e) => setTags(e.target.value)}
                    disabled={submitting}
                  />
                  <div className="token-pills-row">
                    {builtinTagsList.map((t) => (
                      <button
                        key={t}
                        type="button"
                        className="token-pill"
                        onClick={() => addToken(tags, setTags, t)}
                        disabled={submitting}
                      >
                        + {t}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Concepts / Techniques */}
                <div className="form-group">
                  <label className="form-label" htmlFor="prob-concepts">
                    Concepts / Techniques
                  </label>
                  <input
                    id="prob-concepts"
                    type="text"
                    className="form-input"
                    placeholder="e.g. Two Pointer, Sliding Window"
                    value={concepts}
                    onChange={(e) => setConcepts(e.target.value)}
                    disabled={submitting}
                  />
                  {builtinConceptsList.length > 0 && (
                    <div className="token-pills-row scrollable-tokens">
                      {builtinConceptsList.slice(0, 6).map((c) => (
                        <button
                          key={c}
                          type="button"
                          className="token-pill"
                          onClick={() => addToken(concepts, setConcepts, c)}
                          disabled={submitting}
                        >
                          + {c}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Data Structures */}
                <div className="form-group">
                  <label className="form-label" htmlFor="prob-ds">
                    Data Structures
                  </label>
                  <input
                    id="prob-ds"
                    type="text"
                    className="form-input"
                    placeholder="e.g. Array, HashMap"
                    value={dataStructures}
                    onChange={(e) => setDataStructures(e.target.value)}
                    disabled={submitting}
                  />
                  {builtinDsList.length > 0 && (
                    <div className="token-pills-row scrollable-tokens">
                      {builtinDsList.slice(0, 6).map((ds) => (
                        <button
                          key={ds}
                          type="button"
                          className="token-pill"
                          onClick={() => addToken(dataStructures, setDataStructures, ds)}
                          disabled={submitting}
                        >
                          + {ds}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* ── Right Column: Description & Solution Code ── */}
              <div className="form-col right-col">
                {/* Description */}
                <div className="form-group">
                  <label className="form-label" htmlFor="prob-desc">
                    Problem Description <span className="required-star">*</span>
                  </label>
                  <textarea
                    id="prob-desc"
                    className="form-textarea desc-textarea"
                    rows={4}
                    placeholder="Paste the problem statement or summary..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    disabled={submitting}
                  />
                </div>

                {/* Solution Code */}
                <div className="form-group solution-group">
                  <div className="label-with-action">
                    <label className="form-label" htmlFor="prob-code">
                      Solution Code <span className="required-star">*</span>
                    </label>
                    <button
                      type="button"
                      className="text-action-btn"
                      onClick={handlePreviewComplexity}
                      disabled={analyzingComplexity || submitting}
                    >
                      {analyzingComplexity ? "Analyzing..." : "⚡ Preview Complexity"}
                    </button>
                  </div>
                  <textarea
                    id="prob-code"
                    className="form-textarea code-textarea font-mono"
                    rows={12}
                    placeholder={`// Paste your ${language} solution here...`}
                    value={solutionCode}
                    onChange={(e) => setSolutionCode(e.target.value)}
                    disabled={submitting}
                    spellCheck={false}
                  />
                </div>

                {/* Complexity Preview Box */}
                <div className="complexity-preview-box">
                  <div className="complexity-box-header">
                    <span className="complexity-badge-label">ENGINE COMPLEXITY</span>
                    <span className="complexity-tagline">
                      Estimated automatically by Python engine
                    </span>
                  </div>
                  <div className="complexity-values">
                    <span className="complexity-metric">
                      Time: <strong>{complexity ? complexity.time_complexity : "O(?) (on create)"}</strong>
                    </span>
                    <span className="complexity-separator">•</span>
                    <span className="complexity-metric">
                      Space: <strong>{complexity ? complexity.space_complexity : "O(?) (on create)"}</strong>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="modal-footer">
            <button
              type="button"
              className="action-btn secondary-action-btn"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="action-btn primary-action-btn"
              disabled={submitting}
              id="btn-submit-problem"
            >
              {submitting ? "Creating & Verifying..." : "+ Create Problem"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
