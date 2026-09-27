"""
main.py - Phase 0, Phase 1, Phase 1.5 & Phase 2 Desktop Application for DSA Organizer.

Built with Python Tkinter.
Communicates strictly through engine/backend.py.

Phase 2 UI additions:
- Git Integration panel (always visible below the repo card)
- Displays git availability and repository git status
- Stage last-created file (user-triggered only)
- Commit with user-supplied message (user-triggered only)
- Push to configured remote (user-triggered only)
- Scrollable dark git activity log
"""

from pathlib import Path
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Dict, List, Optional, Tuple

# Ensure engine package is importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine import backend


class AddProblemDialog(tk.Toplevel):
    """Modal dialog for creating a new DSA problem source file."""

    def __init__(self, parent: tk.Tk, repo_path: str, initial_category: str = "", on_success_callback=None) -> None:
        super().__init__(parent)
        self.parent = parent
        self.repo_path = repo_path
        self.initial_category = initial_category.strip()
        self.on_success_callback = on_success_callback

        self.title("Add New DSA Problem")
        self.geometry("740x840")
        self.minsize(640, 720)
        self.transient(parent)
        self.grab_set()

        self._init_variables()
        self._create_widgets()

    def _init_variables(self) -> None:
        # Load default language from config if present
        config, _ = backend.load_config()
        def_lang = (config or {}).get("default_language", "cpp").lower()
        if def_lang in ("python", "py"):
            initial_lang = "Python"
        elif def_lang == "java":
            initial_lang = "Java"
        else:
            initial_lang = "C++"

        self.lang_var = tk.StringVar(value=initial_lang)
        self.platform_var = tk.StringVar(value="LeetCode")
        self.custom_platform_var = tk.StringVar(value="")

        # Preselect initial category if provided
        configured_cats = backend.get_categories()
        default_cat = backend.DEFAULT_CATEGORIES[0]
        if self.initial_category:
            target_k = backend.normalize_metadata_key(self.initial_category)
            match = next((c for c in configured_cats if backend.normalize_metadata_key(c) == target_k), self.initial_category)
            default_cat = match

        self.category_var = tk.StringVar(value=default_cat)
        self.title_var = tk.StringVar(value="")
        self.concepts_var = tk.StringVar(value="")
        self.data_structures_var = tk.StringVar(value="")
        self.tags_var = tk.StringVar(value="")
        self.importance_var = tk.StringVar(value="5 - ★★★★★ (Critical / Must-Do)")
        self.complexity_preview_var = tk.StringVar(value="")

    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self, padding="20 16 20 16")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(main_frame, text="Add New DSA Problem", font=("Segoe UI", 14, "bold"))
        header.pack(anchor="w", pady=(0, 10))

        # Problem Title
        title_label = ttk.Label(main_frame, text="Problem Title *", font=("Segoe UI", 10, "bold"))
        title_label.pack(anchor="w", pady=(4, 2))
        self.title_entry = ttk.Entry(main_frame, textvariable=self.title_var, font=("Segoe UI", 10))
        self.title_entry.pack(fill=tk.X, pady=(0, 10))

        # Row 1: Language, Platform, Primary Category
        selectors_frame = ttk.Frame(main_frame)
        selectors_frame.pack(fill=tk.X, pady=(0, 10))

        # Language selection
        lang_group = ttk.LabelFrame(selectors_frame, text=" Language * ", padding="8 6 8 6")
        lang_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        for lang in list(backend.SUPPORTED_LANGUAGES.keys()):
            ttk.Radiobutton(lang_group, text=lang, value=lang, variable=self.lang_var).pack(anchor="w", pady=1)

        # Platform selection
        plat_group = ttk.LabelFrame(selectors_frame, text=" Platform * ", padding="8 6 8 6")
        plat_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        top_plat_row = ttk.Frame(plat_group)
        top_plat_row.pack(fill=tk.X, pady=(2, 4))

        self.plat_combo = ttk.Combobox(
            top_plat_row,
            textvariable=self.platform_var,
            values=backend.get_all_platforms(),
            state="readonly",
        )
        self.plat_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.plat_combo.bind("<<ComboboxSelected>>", self._on_platform_changed)

        manage_btn = ttk.Button(
            top_plat_row,
            text="Manage",
            width=7,
            command=self._on_manage_platforms,
        )
        manage_btn.pack(side=tk.RIGHT)

        self.custom_plat_frame = ttk.Frame(plat_group)
        self.custom_plat_label = ttk.Label(self.custom_plat_frame, text="Custom Platform:", font=("Segoe UI", 8))
        self.custom_plat_label.pack(anchor="w", pady=(2, 0))

        custom_input_row = ttk.Frame(self.custom_plat_frame)
        custom_input_row.pack(fill=tk.X, pady=(2, 2))

        self.custom_plat_entry = ttk.Entry(custom_input_row, textvariable=self.custom_platform_var)
        self.custom_plat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.save_plat_btn = ttk.Button(
            custom_input_row,
            text="Save Platform",
            command=self._on_save_platform,
        )
        self.save_plat_btn.pack(side=tk.RIGHT)

        self.custom_plat_hint = ttk.Label(self.custom_plat_frame, text="", font=("Segoe UI", 8, "italic"), foreground="#2563EB")
        self.custom_plat_hint.pack(anchor="w", pady=(1, 0))
        self.custom_platform_var.trace_add("write", self._on_custom_platform_typed)

        # Primary Category
        cat_group = ttk.LabelFrame(selectors_frame, text=" Primary Category * ", padding="8 6 8 6")
        cat_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        top_cat_row = ttk.Frame(cat_group)
        top_cat_row.pack(fill=tk.X, pady=(2, 4))

        categories = backend.get_categories()
        self.cat_combo = ttk.Combobox(
            top_cat_row,
            textvariable=self.category_var,
            values=categories,
            state="readonly",
        )
        self.cat_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        cat_manage_btn = ttk.Button(
            top_cat_row,
            text="Manage",
            width=7,
            command=self._on_manage_categories,
        )
        cat_manage_btn.pack(side=tk.RIGHT)

        # Row 2: Concepts / Techniques & Data Structures (User-provided metadata)
        meta_frame = ttk.Frame(main_frame)
        meta_frame.pack(fill=tk.X, pady=(0, 8))

        concepts_col = ttk.Frame(meta_frame)
        concepts_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Label(concepts_col, text="Concepts / Techniques (optional)", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.concepts_entry = ttk.Entry(concepts_col, textvariable=self.concepts_var, font=("Segoe UI", 9))
        self.concepts_entry.pack(fill=tk.X)
        ttk.Label(concepts_col, text="e.g. Hashing, Two Pointer", font=("Segoe UI", 8), foreground="#6B7280").pack(anchor="w")

        ds_col = ttk.Frame(meta_frame)
        ds_col.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))
        ttk.Label(ds_col, text="Data Structures (optional)", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.ds_entry = ttk.Entry(ds_col, textvariable=self.data_structures_var, font=("Segoe UI", 9))
        self.ds_entry.pack(fill=tk.X)
        ttk.Label(ds_col, text="e.g. Array, HashMap", font=("Segoe UI", 8), foreground="#6B7280").pack(anchor="w")

        # Row 3: Tags & Importance (User-provided metadata)
        row3_frame = ttk.Frame(main_frame)
        row3_frame.pack(fill=tk.X, pady=(0, 8))

        tags_col = ttk.Frame(row3_frame)
        tags_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Label(tags_col, text="Tags (optional)", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))

        tags_input_row = ttk.Frame(tags_col)
        tags_input_row.pack(fill=tk.X, pady=(0, 2))

        self.tags_entry = ttk.Entry(tags_input_row, textvariable=self.tags_var, font=("Segoe UI", 9))
        self.tags_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        manage_tags_btn = ttk.Button(
            tags_input_row,
            text="Manage",
            width=7,
            command=self._on_manage_tags,
        )
        manage_tags_btn.pack(side=tk.RIGHT)

        # Quick tag pill chips
        self.tag_pills_frame = ttk.Frame(tags_col)
        self.tag_pills_frame.pack(fill=tk.X, pady=(1, 0))
        self._refresh_tag_pills()

        imp_col = ttk.Frame(row3_frame)
        imp_col.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))
        ttk.Label(imp_col, text="Importance *", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))

        importance_options = [
            "5 - ★★★★★ (Critical / Must-Do)",
            "4 - ★★★★☆ (High)",
            "3 - ★★★☆☆ (Medium)",
            "2 - ★★☆☆☆ (Low)",
            "1 - ★☆☆☆☆ (Minimal)",
        ]
        self.imp_combo = ttk.Combobox(
            imp_col,
            textvariable=self.importance_var,
            values=importance_options,
            state="readonly",
            font=("Segoe UI", 9),
        )
        self.imp_combo.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(imp_col, text="Personal revision priority (1–5)", font=("Segoe UI", 8), foreground="#6B7280").pack(anchor="w")

        # Problem Description
        desc_label = ttk.Label(main_frame, text="Problem Description *", font=("Segoe UI", 10, "bold"))
        desc_label.pack(anchor="w", pady=(4, 2))
        self.desc_text = ScrolledText(main_frame, height=3, font=("Segoe UI", 9), wrap=tk.WORD)
        self.desc_text.pack(fill=tk.X, pady=(0, 8))

        # Solution Code
        code_label = ttk.Label(main_frame, text="Solution Code *", font=("Segoe UI", 10, "bold"))
        code_label.pack(anchor="w", pady=(4, 2))
        self.code_text = ScrolledText(
            main_frame,
            height=9,
            font=("Consolas", 10),
            wrap=tk.NONE,
            relief="solid",
            borderwidth=1,
        )
        self.code_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Engine Complexity Analysis Preview Bar
        complexity_bar = ttk.Frame(main_frame)
        complexity_bar.pack(fill=tk.X, pady=(0, 8))

        preview_btn = ttk.Button(
            complexity_bar,
            text="Estimate Complexity",
            command=self._on_preview_complexity,
        )
        preview_btn.pack(side=tk.LEFT)

        self.complexity_label = ttk.Label(
            complexity_bar,
            textvariable=self.complexity_preview_var,
            font=("Segoe UI", 9, "italic"),
            foreground="#2563EB",
        )
        self.complexity_label.pack(side=tk.LEFT, padx=(10, 0))

        # Action Buttons
        btn_bar = ttk.Frame(main_frame)
        btn_bar.pack(anchor="e", pady=(4, 0))

        cancel_btn = ttk.Button(btn_bar, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))

        create_btn = ttk.Button(btn_bar, text="Create Problem File", command=self._on_create)
        create_btn.pack(side=tk.RIGHT)

    def _on_toggle_tag_pill(self, tag_name: str) -> None:
        """Add or remove a tag from the tags entry field."""
        raw = self.tags_var.get()
        current_tags = [t.strip() for t in raw.split(",") if t.strip()]
        tag_lower = tag_name.lower()

        matched_idx = None
        for idx, t in enumerate(current_tags):
            if t.lower() == tag_lower:
                matched_idx = idx
                break

        if matched_idx is not None:
            current_tags.pop(matched_idx)
        else:
            current_tags.append(tag_name)

        self.tags_var.set(", ".join(current_tags))

    def _refresh_tag_pills(self) -> None:
        """Populate clickable quick-tag buttons from built-in and saved custom tags."""
        for widget in self.tag_pills_frame.winfo_children():
            widget.destroy()

        all_tags = backend.get_all_tags()
        for t in all_tags[:6]:
            btn = ttk.Button(
                self.tag_pills_frame,
                text=f"+ {t}",
                command=lambda tag=t: self._on_toggle_tag_pill(tag),
            )
            btn.pack(side=tk.LEFT, padx=(0, 4), pady=(1, 0))

    def _on_manage_tags(self) -> None:
        """Open the Manage Tags dialog."""
        ManageTagsDialog(self)

    def _refresh_tags_after_management(self) -> None:
        """Called by ManageTagsDialog after tags are saved or deleted."""
        self._refresh_tag_pills()

    def _on_platform_changed(self, event=None) -> None:
        if self.platform_var.get() == "Other":
            self.custom_plat_frame.pack(fill=tk.X, pady=(2, 0))
        else:
            self.custom_plat_frame.pack_forget()

    def _on_custom_platform_typed(self, *args) -> None:
        val = self.custom_platform_var.get().strip()
        if not val:
            self.custom_plat_hint.configure(text="")
            return
        norm_k = backend.normalize_metadata_key(val)
        all_plats = backend.get_all_platforms()
        matched = None
        for p in all_plats:
            if backend.normalize_metadata_key(p) == norm_k:
                matched = p
                break
        if matched:
            self.custom_plat_hint.configure(text=f"✓ Existing platform found: '{matched}' (will use canonical)")
        else:
            self.custom_plat_hint.configure(text=f"Create new: '{backend.normalize_metadata_display(val)}'")

    def _on_save_platform(self) -> None:
        """Validate and save a custom platform, update dropdown and select it."""
        raw_name = self.custom_platform_var.get().strip()
        if not raw_name:
            messagebox.showwarning("Platform Required", "Please enter a custom platform name before saving.", parent=self)
            return

        norm_k = backend.normalize_metadata_key(raw_name)
        all_plats = backend.get_all_platforms()
        for p in all_plats:
            if backend.normalize_metadata_key(p) == norm_k:
                self.platform_var.set(p)
                self.custom_platform_var.set("")
                self._on_platform_changed()
                messagebox.showinfo("Existing Platform", f"Selected existing canonical platform '{p}'.", parent=self)
                return

        ok, msg = backend.save_custom_platform(raw_name)
        if not ok:
            messagebox.showerror("Cannot Save Platform", msg, parent=self)
            return

        # Refresh dropdown with newly saved platforms
        all_plats = backend.get_all_platforms()
        self.plat_combo["values"] = all_plats
        clean_name = backend.normalize_metadata_display(raw_name)
        self.platform_var.set(clean_name)
        self.custom_platform_var.set("")
        self._on_platform_changed()
        messagebox.showinfo("Platform Saved", f"Custom platform '{clean_name}' saved successfully and added to dropdown!", parent=self)

    def _on_manage_platforms(self) -> None:
        """Open the Manage Platforms dialog."""
        ManagePlatformsDialog(self)

    def _refresh_platforms_after_management(self) -> None:
        """Called by ManagePlatformsDialog after platforms are added/deleted."""
        all_plats = backend.get_all_platforms()
        self.plat_combo["values"] = all_plats
        if self.platform_var.get() not in all_plats:
            self.platform_var.set("LeetCode")
            self._on_platform_changed()

    def _on_manage_categories(self) -> None:
        """Open the Manage Categories dialog."""
        ManageCategoriesDialog(self)

    def _refresh_categories_after_management(self, select_category: str | None = None) -> None:
        """Called by ManageCategoriesDialog after categories are added/deleted."""
        all_cats = backend.get_categories()
        self.cat_combo["values"] = all_cats
        if select_category and select_category in all_cats:
            self.category_var.set(select_category)
        elif self.category_var.get() not in all_cats:
            self.category_var.set(backend.DEFAULT_CATEGORIES[0])

    def _on_preview_complexity(self) -> None:
        """Request the engine to analyze the current solution code."""
        code = self.code_text.get("1.0", tk.END).strip()
        lang = self.lang_var.get()
        if not code:
            self.complexity_preview_var.set("Please enter solution code first.")
            return

        analysis = backend.analyze_complexity(lang, code)
        time_c = analysis.get("time_complexity", "Unable to determine")
        space_c = analysis.get("space_complexity", "Unable to determine")
        self.complexity_preview_var.set(f"Engine Complexity: Time: {time_c} | Space: {space_c}")

    def _on_create(self) -> None:
        title = self.title_var.get()
        platform = self.platform_var.get()
        custom_platform = self.custom_platform_var.get()
        language = self.lang_var.get()
        category = self.category_var.get()
        description = self.desc_text.get("1.0", tk.END).strip()
        solution = self.code_text.get("1.0", tk.END)
        concepts = self.concepts_var.get().strip()
        data_structures = self.data_structures_var.get().strip()
        tags = self.tags_var.get().strip()
        importance = self.importance_var.get().strip()

        # Call backend to create, analyze, write, and physically verify
        success, message, target_file = backend.create_problem_file(
            title=title,
            platform=platform,
            language=language,
            category=category,
            description=description,
            solution_code=solution,
            custom_platform=custom_platform,
            repo_path=self.repo_path,
            concepts=concepts,
            data_structures=data_structures,
            tags=tags,
            importance=importance,
        )

        if not success:
            messagebox.showerror("Error Creating Problem", message, parent=self)
            return

        messagebox.showinfo("Success", message, parent=self)
        if self.on_success_callback and target_file:
            self.on_success_callback(target_file, title, category)
        self.destroy()


class ManagePlatformsDialog(tk.Toplevel):
    """Modal dialog for viewing and deleting saved custom platforms."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.parent_dialog = parent
        self.title("Manage Custom Platforms")
        self.geometry("400x320")
        self.minsize(360, 260)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

    def _create_widgets(self) -> None:
        frame = ttk.Frame(self, padding="16 14 16 14")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Saved Custom Platforms", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(frame, text="Select a platform to delete it from the dropdown.", font=("Segoe UI", 9), foreground="#6B7280").pack(anchor="w", pady=(0, 8))

        self.listbox = tk.Listbox(frame, font=("Segoe UI", 10), height=8)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X)

        del_btn = ttk.Button(btn_row, text="Delete Selected", command=self._on_delete)
        del_btn.pack(side=tk.LEFT)

        close_btn = ttk.Button(btn_row, text="Close", command=self.destroy)
        close_btn.pack(side=tk.RIGHT)

        self._populate()

    def _populate(self) -> None:
        self.listbox.delete(0, tk.END)
        custom_plats = backend.get_custom_platforms()
        for p in custom_plats:
            self.listbox.insert(tk.END, p)

    def _on_delete(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Selection Required", "Please select a platform to delete.", parent=self)
            return
        name = self.listbox.get(sel[0])
        ok, msg = backend.delete_custom_platform(name)
        if ok:
            self._populate()
            if hasattr(self.parent_dialog, "_refresh_platforms_after_management"):
                self.parent_dialog._refresh_platforms_after_management()
            messagebox.showinfo("Deleted", msg, parent=self)
        else:
            messagebox.showerror("Error", msg, parent=self)


class ManageCategoriesDialog(tk.Toplevel):
    """Modal dialog for viewing, adding, and safely deleting primary categories."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.parent_dialog = parent
        self.title("Manage Primary Categories")
        self.geometry("450x440")
        self.minsize(400, 380)
        self.transient(parent)
        self.grab_set()

        self._new_cat_var = tk.StringVar(value="")
        self._create_widgets()

    def _create_widgets(self) -> None:
        frame = ttk.Frame(self, padding="16 14 16 14")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Available Primary Categories", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Label(
            frame,
            text="Custom categories become top-level directories in your DSA repository.",
            font=("Segoe UI", 8),
            foreground="#6B7280",
        ).pack(anchor="w", pady=(0, 8))

        # Listbox with categories
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.listbox = tk.Listbox(list_frame, font=("Segoe UI", 9), height=9)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Add new category section
        add_group = ttk.LabelFrame(frame, text=" Add Custom Category ", padding="8 6 8 6")
        add_group.pack(fill=tk.X, pady=(0, 8))

        add_row = ttk.Frame(add_group)
        add_row.pack(fill=tk.X, pady=(2, 2))

        ttk.Label(add_row, text="New Category:").pack(side=tk.LEFT, padx=(0, 4))
        self.new_cat_entry = ttk.Entry(add_row, textvariable=self._new_cat_var)
        self.new_cat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        save_btn = ttk.Button(add_row, text="Save Category", command=self._on_save_category)
        save_btn.pack(side=tk.RIGHT)

        # Actions bar
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(4, 0))

        del_btn = ttk.Button(btn_row, text="Delete Selected", command=self._on_delete_category)
        del_btn.pack(side=tk.LEFT)

        close_btn = ttk.Button(btn_row, text="Close", command=self.destroy)
        close_btn.pack(side=tk.RIGHT)

        self._populate()

    def _populate(self) -> None:
        self.listbox.delete(0, tk.END)
        custom_set = {c.lower(): c for c in backend.get_custom_categories()}
        all_cats = backend.get_categories()
        for c in all_cats:
            if c.lower() in custom_set:
                self.listbox.insert(tk.END, f"{c}  [Custom]")
            else:
                self.listbox.insert(tk.END, c)

    def _on_save_category(self) -> None:
        name = self._new_cat_var.get().strip()
        if not name:
            messagebox.showwarning("Category Required", "Please enter a category name.", parent=self)
            return

        ok, msg = backend.save_custom_category(name)
        if not ok:
            messagebox.showerror("Cannot Save Category", msg, parent=self)
            return

        self._new_cat_var.set("")
        self._populate()
        if hasattr(self.parent_dialog, "_refresh_categories_after_management"):
            self.parent_dialog._refresh_categories_after_management(select_category=name)
        messagebox.showinfo("Category Saved", f"Category '{name}' saved successfully and added to dropdown!", parent=self)

    def _on_delete_category(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Selection Required", "Please select a custom category to delete.", parent=self)
            return

        item_text = self.listbox.get(sel[0])
        cat_name = item_text.replace("  [Custom]", "").strip()

        builtin_names = {b.lower() for b in backend.DEFAULT_CATEGORIES}
        if cat_name.lower() in builtin_names:
            messagebox.showinfo("Built-in Category", f"'{cat_name}' is a built-in category and cannot be deleted.", parent=self)
            return

        repo_path = getattr(self.parent_dialog, "repo_path", None)
        ok, msg = backend.delete_custom_category(cat_name, repo_path=repo_path)
        if ok:
            self._populate()
            if hasattr(self.parent_dialog, "_refresh_categories_after_management"):
                self.parent_dialog._refresh_categories_after_management()
            messagebox.showinfo("Category Removed", msg, parent=self)
        else:
            messagebox.showerror("Error", msg, parent=self)


class ManageTagsDialog(tk.Toplevel):
    """Modal dialog for viewing, adding, and deleting custom tags."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.parent_dialog = parent
        self.title("Manage Tags")
        self.geometry("440x420")
        self.minsize(380, 360)
        self.transient(parent)
        self.grab_set()

        self._new_tag_var = tk.StringVar(value="")
        self._create_widgets()

    def _create_widgets(self) -> None:
        frame = ttk.Frame(self, padding="16 14 16 14")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Available Tags", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Label(
            frame,
            text="Tags are reusable metadata for organizing and revising problems.",
            font=("Segoe UI", 8),
            foreground="#6B7280",
        ).pack(anchor="w", pady=(0, 8))

        # Listbox with tags
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.listbox = tk.Listbox(list_frame, font=("Segoe UI", 9), height=8)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Add new tag section
        add_group = ttk.LabelFrame(frame, text=" Add Custom Tag ", padding="8 6 8 6")
        add_group.pack(fill=tk.X, pady=(0, 8))

        add_row = ttk.Frame(add_group)
        add_row.pack(fill=tk.X, pady=(2, 2))

        ttk.Label(add_row, text="New Tag:").pack(side=tk.LEFT, padx=(0, 4))
        self.new_tag_entry = ttk.Entry(add_row, textvariable=self._new_tag_var)
        self.new_tag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        save_btn = ttk.Button(add_row, text="Save Tag", command=self._on_save_tag)
        save_btn.pack(side=tk.RIGHT)

        # Actions bar
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(4, 0))

        del_btn = ttk.Button(btn_row, text="Delete Selected", command=self._on_delete_tag)
        del_btn.pack(side=tk.LEFT)

        close_btn = ttk.Button(btn_row, text="Close", command=self.destroy)
        close_btn.pack(side=tk.RIGHT)

        self._populate()

    def _populate(self) -> None:
        self.listbox.delete(0, tk.END)
        custom_set = {t.lower(): t for t in backend.get_custom_tags()}
        all_tags = backend.get_all_tags()
        for t in all_tags:
            if t.lower() in custom_set:
                self.listbox.insert(tk.END, f"{t}  [Custom]")
            else:
                self.listbox.insert(tk.END, f"{t}  [Built-in]")

    def _on_save_tag(self) -> None:
        name = self._new_tag_var.get().strip()
        if not name:
            messagebox.showwarning("Tag Required", "Please enter a tag name.", parent=self)
            return

        ok, msg = backend.save_custom_tag(name)
        if not ok:
            messagebox.showerror("Cannot Save Tag", msg, parent=self)
            return

        self._new_tag_var.set("")
        self._populate()
        if hasattr(self.parent_dialog, "_refresh_tags_after_management"):
            self.parent_dialog._refresh_tags_after_management()
        messagebox.showinfo("Tag Saved", f"Tag '{name}' saved successfully and available for suggestions!", parent=self)

    def _on_delete_tag(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Selection Required", "Please select a custom tag to delete.", parent=self)
            return

        item_text = self.listbox.get(sel[0])
        tag_name = item_text.replace("  [Custom]", "").replace("  [Built-in]", "").strip()

        builtin_names = {b.lower() for b in backend.BUILTIN_TAGS}
        if tag_name.lower() in builtin_names:
            messagebox.showinfo("Built-in Tag", f"'{tag_name}' is a built-in tag and cannot be deleted.", parent=self)
            return

        ok, msg = backend.delete_custom_tag(tag_name)
        if ok:
            self._populate()
            if hasattr(self.parent_dialog, "_refresh_tags_after_management"):
                self.parent_dialog._refresh_tags_after_management()
            messagebox.showinfo("Tag Removed", msg, parent=self)
        else:
            messagebox.showerror("Error", msg, parent=self)


class RepairMetadataDialog(tk.Toplevel):
    """Modal dialog for viewing, completing, and safely repairing metadata of an existing problem file."""

    def __init__(
        self,
        parent: tk.Widget,
        problem_data: Dict[str, Any],
        repo_path: str,
        on_success_callback=None,
    ) -> None:
        super().__init__(parent)
        self.parent_dialog = parent
        self.problem_data = problem_data
        self.repo_path = repo_path
        self.on_success_callback = on_success_callback

        self.file_path = problem_data.get("file_path", "")
        self.metadata = problem_data.get("metadata", {})

        filename = Path(self.file_path).name if self.file_path else "Problem"
        self.title(f"Complete / Repair Metadata — {filename}")
        self.geometry("760x880")
        self.minsize(640, 720)
        self.transient(parent)
        self.grab_set()

        self._init_variables()
        self._create_widgets()

    def _init_variables(self) -> None:
        meta = self.metadata
        prob = self.problem_data

        # Language
        lang = meta.get("language") or prob.get("language", "C++")
        self.lang_var = tk.StringVar(value=lang)

        # Platform
        plat = meta.get("platform") or prob.get("platform", "LeetCode")
        self.platform_var = tk.StringVar(value=plat if plat else "LeetCode")
        self.custom_platform_var = tk.StringVar(value="")

        # Primary Category
        cat = meta.get("category") or prob.get("category", "")
        if not cat:
            cat = prob.get("folder_category") or backend.DEFAULT_CATEGORIES[0]
        self.category_var = tk.StringVar(value=cat)

        # Title
        title = meta.get("title") or prob.get("title") or Path(self.file_path).stem
        self.title_var = tk.StringVar(value=title)

        # User metadata fields
        self.concepts_var = tk.StringVar(value=meta.get("concepts", ""))
        self.data_structures_var = tk.StringVar(value=meta.get("data_structures", ""))
        self.tags_var = tk.StringVar(value=meta.get("tags", ""))

        # Importance (1-5 numeric scale with stars)
        raw_imp = str(meta.get("importance", "3")).strip()
        dig = re.search(r"[1-5]", raw_imp)
        imp_digit = dig.group(0) if dig else "3"
        imp_map = {
            "5": "5 - ★★★★★ (Critical / Must-Do)",
            "4": "4 - ★★★★☆ (High)",
            "3": "3 - ★★★☆☆ (Medium)",
            "2": "2 - ★★☆☆☆ (Low)",
            "1": "1 - ★☆☆☆☆ (Minimal)",
        }
        self.importance_var = tk.StringVar(value=imp_map.get(imp_digit, "3 - ★★★☆☆ (Medium)"))

        # Complexity
        self.tc_var = tk.StringVar(value=meta.get("time_complexity", ""))
        self.sc_var = tk.StringVar(value=meta.get("space_complexity", ""))
        self.complexity_preview_var = tk.StringVar(value="")

        # Added date
        added = meta.get("added_date") or backend.date.today().strftime("%Y-%m-%d")
        self.added_date_var = tk.StringVar(value=added)

    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self, padding="20 16 20 16")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(main_frame, text="Complete & Repair Problem Metadata", font=("Segoe UI", 13, "bold"))
        header.pack(anchor="w", pady=(0, 4))

        file_label = ttk.Label(
            main_frame,
            text=f"File: {self.problem_data.get('rel_path', self.file_path)}",
            font=("Segoe UI", 9, "bold"),
            foreground="#4B5563",
        )
        file_label.pack(anchor="w", pady=(0, 8))

        # Category Relocation Warning Banner
        self.mismatch_frame = tk.Frame(main_frame, bg="#FEF3C7", relief="solid", borderwidth=1, padx=10, pady=6)
        self.mismatch_label = tk.Label(
            self.mismatch_frame,
            text="",
            bg="#FEF3C7",
            fg="#92400E",
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
        )
        self.mismatch_label.pack(fill=tk.X)
        self.mismatch_frame.pack(fill=tk.X, pady=(0, 8))

        # Missing Fields Notice
        missing = self.problem_data.get("missing_fields", [])
        if missing and missing != ["Unrecognized or missing metadata header"]:
            missing_frame = tk.Frame(main_frame, bg="#EFF6FF", relief="solid", borderwidth=1, padx=10, pady=5)
            missing_frame.pack(fill=tk.X, pady=(0, 8))
            missing_text = "⚠ Missing / Unstandardized Fields: " + ", ".join(missing)
            tk.Label(
                missing_frame,
                text=missing_text,
                bg="#EFF6FF",
                fg="#1D4ED8",
                font=("Segoe UI", 9, "bold"),
                justify="left",
                anchor="w",
            ).pack(fill=tk.X)

        # Problem Title
        title_label = ttk.Label(main_frame, text="Problem Title *", font=("Segoe UI", 9, "bold"))
        title_label.pack(anchor="w", pady=(2, 2))
        self.title_entry = ttk.Entry(main_frame, textvariable=self.title_var, font=("Segoe UI", 10))
        self.title_entry.pack(fill=tk.X, pady=(0, 8))

        # Row 1: Language, Platform, Primary Category
        selectors_frame = ttk.Frame(main_frame)
        selectors_frame.pack(fill=tk.X, pady=(0, 8))

        # Language selection
        lang_group = ttk.LabelFrame(selectors_frame, text=" Language * ", padding="8 6 8 6")
        lang_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        for lang in list(backend.SUPPORTED_LANGUAGES.keys()):
            ttk.Radiobutton(lang_group, text=lang, value=lang, variable=self.lang_var).pack(anchor="w", pady=1)

        # Platform selection
        plat_group = ttk.LabelFrame(selectors_frame, text=" Platform * ", padding="8 6 8 6")
        plat_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        top_plat_row = ttk.Frame(plat_group)
        top_plat_row.pack(fill=tk.X, pady=(2, 4))

        self.plat_combo = ttk.Combobox(
            top_plat_row,
            textvariable=self.platform_var,
            values=backend.get_all_platforms(),
            state="readonly",
        )
        self.plat_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.plat_combo.bind("<<ComboboxSelected>>", self._on_platform_changed)

        manage_btn = ttk.Button(top_plat_row, text="Manage", width=7, command=self._on_manage_platforms)
        manage_btn.pack(side=tk.RIGHT)

        self.custom_plat_frame = ttk.Frame(plat_group)
        self.custom_plat_label = ttk.Label(self.custom_plat_frame, text="Custom Platform:", font=("Segoe UI", 8))
        self.custom_plat_label.pack(anchor="w", pady=(2, 0))

        custom_input_row = ttk.Frame(self.custom_plat_frame)
        custom_input_row.pack(fill=tk.X, pady=(2, 2))

        self.custom_plat_entry = ttk.Entry(custom_input_row, textvariable=self.custom_platform_var)
        self.custom_plat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.save_plat_btn = ttk.Button(custom_input_row, text="Save Platform", command=self._on_save_platform)
        self.save_plat_btn.pack(side=tk.RIGHT)

        self.custom_plat_hint = ttk.Label(self.custom_plat_frame, text="", font=("Segoe UI", 8, "italic"), foreground="#2563EB")
        self.custom_plat_hint.pack(anchor="w", pady=(1, 0))
        self.custom_platform_var.trace_add("write", self._on_custom_platform_typed)

        # Primary Category
        cat_group = ttk.LabelFrame(selectors_frame, text=" Primary Category * ", padding="8 6 8 6")
        cat_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        top_cat_row = ttk.Frame(cat_group)
        top_cat_row.pack(fill=tk.X, pady=(2, 4))

        categories = backend.get_categories()
        self.cat_combo = ttk.Combobox(
            top_cat_row,
            textvariable=self.category_var,
            values=categories,
            state="readonly",
        )
        self.cat_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.cat_combo.bind("<<ComboboxSelected>>", self._on_category_selected)

        cat_manage_btn = ttk.Button(top_cat_row, text="Manage", width=7, command=self._on_manage_categories)
        cat_manage_btn.pack(side=tk.RIGHT)

        # Initialize category banner state
        self._update_category_banner()

        # Row 2: Concepts / Techniques & Data Structures
        meta_frame = ttk.Frame(main_frame)
        meta_frame.pack(fill=tk.X, pady=(0, 8))

        concepts_col = ttk.Frame(meta_frame)
        concepts_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Label(concepts_col, text="Concepts / Techniques (optional)", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.concepts_entry = ttk.Entry(concepts_col, textvariable=self.concepts_var, font=("Segoe UI", 9))
        self.concepts_entry.pack(fill=tk.X)

        ds_col = ttk.Frame(meta_frame)
        ds_col.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))
        ttk.Label(ds_col, text="Data Structures (optional)", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.ds_entry = ttk.Entry(ds_col, textvariable=self.data_structures_var, font=("Segoe UI", 9))
        self.ds_entry.pack(fill=tk.X)

        # Row 3: Tags & Importance
        row3_frame = ttk.Frame(main_frame)
        row3_frame.pack(fill=tk.X, pady=(0, 8))

        tags_col = ttk.Frame(row3_frame)
        tags_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Label(tags_col, text="Tags (optional)", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))

        tags_input_row = ttk.Frame(tags_col)
        tags_input_row.pack(fill=tk.X, pady=(0, 2))

        self.tags_entry = ttk.Entry(tags_input_row, textvariable=self.tags_var, font=("Segoe UI", 9))
        self.tags_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        manage_tags_btn = ttk.Button(tags_input_row, text="Manage", width=7, command=self._on_manage_tags)
        manage_tags_btn.pack(side=tk.RIGHT)

        self.tag_pills_frame = ttk.Frame(tags_col)
        self.tag_pills_frame.pack(fill=tk.X, pady=(1, 0))
        self._refresh_tag_pills()

        imp_col = ttk.Frame(row3_frame)
        imp_col.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))
        ttk.Label(imp_col, text="Importance *", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))

        importance_options = [
            "5 - ★★★★★ (Critical / Must-Do)",
            "4 - ★★★★☆ (High)",
            "3 - ★★★☆☆ (Medium)",
            "2 - ★★☆☆☆ (Low)",
            "1 - ★☆☆☆☆ (Minimal)",
        ]
        self.imp_combo = ttk.Combobox(
            imp_col,
            textvariable=self.importance_var,
            values=importance_options,
            state="readonly",
            font=("Segoe UI", 9),
        )
        self.imp_combo.pack(fill=tk.X, pady=(0, 2))

        # Row 4: Complexity and Added Date
        row4_frame = ttk.Frame(main_frame)
        row4_frame.pack(fill=tk.X, pady=(0, 8))

        tc_col = ttk.Frame(row4_frame)
        tc_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Label(tc_col, text="Time Complexity", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Entry(tc_col, textvariable=self.tc_var, font=("Segoe UI", 9)).pack(fill=tk.X)

        sc_col = ttk.Frame(row4_frame)
        sc_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        ttk.Label(sc_col, text="Space Complexity", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Entry(sc_col, textvariable=self.sc_var, font=("Segoe UI", 9)).pack(fill=tk.X)

        est_btn = ttk.Button(row4_frame, text="Auto-Estimate", command=self._on_estimate_complexity)
        est_btn.pack(side=tk.LEFT, padx=(4, 6), pady=(16, 0))

        date_col = ttk.Frame(row4_frame)
        date_col.pack(side=tk.RIGHT, fill=tk.X, expand=False, padx=(4, 0))
        ttk.Label(date_col, text="Added Date", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Entry(date_col, textvariable=self.added_date_var, font=("Segoe UI", 9), width=14).pack(fill=tk.X)

        # Problem Description
        desc_label = ttk.Label(main_frame, text="Problem Description", font=("Segoe UI", 9, "bold"))
        desc_label.pack(anchor="w", pady=(2, 2))
        self.desc_text = ScrolledText(main_frame, height=4, font=("Segoe UI", 9), wrap=tk.WORD)
        self.desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        initial_desc = self.metadata.get("description", "")
        if initial_desc:
            self.desc_text.insert("1.0", initial_desc)

        # Solution code notice
        notice = ttk.Label(
            main_frame,
            text="ℹ Solution code from the source file is preserved byte-for-byte and will not be altered.",
            font=("Segoe UI", 8, "italic"),
            foreground="#4B5563",
        )
        notice.pack(anchor="w", pady=(0, 8))

        # Action Buttons
        btn_bar = ttk.Frame(main_frame)
        btn_bar.pack(anchor="e", pady=(4, 0))

        cancel_btn = ttk.Button(btn_bar, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))

        save_btn = ttk.Button(btn_bar, text="Save Repaired Metadata", command=self._on_save)
        save_btn.pack(side=tk.RIGHT)

    def _on_toggle_tag_pill(self, tag_name: str) -> None:
        raw = self.tags_var.get()
        current_tags = [t.strip() for t in raw.split(",") if t.strip()]
        tag_lower = tag_name.lower()

        matched_idx = None
        for idx, t in enumerate(current_tags):
            if t.lower() == tag_lower:
                matched_idx = idx
                break

        if matched_idx is not None:
            current_tags.pop(matched_idx)
        else:
            current_tags.append(tag_name)

        self.tags_var.set(", ".join(current_tags))

    def _refresh_tag_pills(self) -> None:
        for widget in self.tag_pills_frame.winfo_children():
            widget.destroy()

        all_tags = backend.get_all_tags()
        for t in all_tags[:6]:
            btn = ttk.Button(
                self.tag_pills_frame,
                text=f"+ {t}",
                command=lambda tag=t: self._on_toggle_tag_pill(tag),
            )
            btn.pack(side=tk.LEFT, padx=(0, 4), pady=(1, 0))

    def _on_manage_tags(self) -> None:
        ManageTagsDialog(self)

    def _refresh_tags_after_management(self) -> None:
        self._refresh_tag_pills()

    def _on_platform_changed(self, event=None) -> None:
        if self.platform_var.get() == "Other":
            self.custom_plat_frame.pack(fill=tk.X, pady=(2, 0))
        else:
            self.custom_plat_frame.pack_forget()

    def _on_custom_platform_typed(self, *args) -> None:
        val = self.custom_platform_var.get().strip()
        if not val:
            self.custom_plat_hint.configure(text="")
            return
        norm_k = backend.normalize_metadata_key(val)
        all_plats = backend.get_all_platforms()
        matched = None
        for p in all_plats:
            if backend.normalize_metadata_key(p) == norm_k:
                matched = p
                break
        if matched:
            self.custom_plat_hint.configure(text=f"✓ Existing platform found: '{matched}' (will use canonical)")
        else:
            self.custom_plat_hint.configure(text=f"Create new: '{backend.normalize_metadata_display(val)}'")

    def _on_save_platform(self) -> None:
        raw_name = self.custom_platform_var.get().strip()
        if not raw_name:
            messagebox.showwarning("Platform Required", "Please enter a custom platform name before saving.", parent=self)
            return

        norm_k = backend.normalize_metadata_key(raw_name)
        all_plats = backend.get_all_platforms()
        for p in all_plats:
            if backend.normalize_metadata_key(p) == norm_k:
                self.platform_var.set(p)
                self.custom_platform_var.set("")
                self._on_platform_changed()
                messagebox.showinfo("Existing Platform", f"Selected existing canonical platform '{p}'.", parent=self)
                return

        ok, msg = backend.save_custom_platform(raw_name)
        if not ok:
            messagebox.showerror("Cannot Save Platform", msg, parent=self)
            return

        all_plats = backend.get_all_platforms()
        self.plat_combo["values"] = all_plats
        clean_name = backend.normalize_metadata_display(raw_name)
        self.platform_var.set(clean_name)
        self.custom_platform_var.set("")
        self._on_platform_changed()
        messagebox.showinfo("Platform Saved", f"Custom platform '{clean_name}' saved successfully and added to dropdown!", parent=self)

    def _on_manage_platforms(self) -> None:
        ManagePlatformsDialog(self)

    def _refresh_platforms_after_management(self) -> None:
        all_plats = backend.get_all_platforms()
        self.plat_combo["values"] = all_plats
        if self.platform_var.get() not in all_plats:
            self.platform_var.set("LeetCode")
            self._on_platform_changed()

    def _on_manage_categories(self) -> None:
        ManageCategoriesDialog(self)

    def _refresh_categories_after_management(self, select_category: str | None = None) -> None:
        all_cats = backend.get_categories()
        self.cat_combo["values"] = all_cats
        if select_category and select_category in all_cats:
            self.category_var.set(select_category)
        elif self.category_var.get() not in all_cats:
            self.category_var.set(backend.DEFAULT_CATEGORIES[0])
        self._update_category_banner()

    def _update_category_banner(self) -> None:
        folder_cat = self.problem_data.get("folder_category", "").strip()
        selected_cat = self.category_var.get().strip()

        if folder_cat and selected_cat and folder_cat.lower() != selected_cat.lower():
            warn_msg = (
                f"⚠ Category Mismatch Warning:\n"
                f"Physical Folder: '{folder_cat}'  |  New Primary Category: '{selected_cat}'\n\n"
                f"Saving this repair will update the metadata and move the file\n"
                f"to the '{selected_cat}' category folder."
            )
            self.mismatch_label.configure(text=warn_msg)
            self.mismatch_frame.pack(fill=tk.X, pady=(0, 8))
        else:
            self.mismatch_frame.pack_forget()

    def _on_category_selected(self, event=None) -> None:
        self._update_category_banner()

    def _on_estimate_complexity(self) -> None:
        sol_code = self.metadata.get("solution_code", "")
        lang = self.lang_var.get()
        if not sol_code:
            try:
                content = Path(self.file_path).read_text(encoding="utf-8")
                parsed = backend.parse_problem_content(content, Path(self.file_path).suffix)
                sol_code = parsed.get("solution_code", "")
            except Exception:
                pass

        analysis = backend.analyze_complexity(lang, sol_code)
        tc = analysis.get("time_complexity", "Unable to determine")
        sc = analysis.get("space_complexity", "Unable to determine")
        self.tc_var.set(tc)
        self.sc_var.set(sc)

    def _on_save(self) -> None:
        title = self.title_var.get().strip()
        platform = self.platform_var.get().strip()
        language = self.lang_var.get().strip()
        category = self.category_var.get().strip()
        concepts = self.concepts_var.get().strip()
        data_structures = self.data_structures_var.get().strip()
        tags = self.tags_var.get().strip()
        importance = self.importance_var.get().strip()
        tc = self.tc_var.get().strip()
        sc = self.sc_var.get().strip()
        added_date = self.added_date_var.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()

        if not title:
            messagebox.showerror("Title Required", "Problem title cannot be empty.", parent=self)
            return

        updated_fields = {
            "title": title,
            "platform": platform,
            "language": language,
            "category": category,
            "concepts": concepts,
            "data_structures": data_structures,
            "tags": tags,
            "importance": importance,
            "time_complexity": tc,
            "space_complexity": sc,
            "added_date": added_date,
            "description": description,
        }

        ok, msg = backend.update_problem_metadata(
            file_path=self.file_path,
            updated_fields=updated_fields,
            repo_path=self.repo_path,
        )

        if not ok:
            messagebox.showerror("Error Repairing Metadata", msg, parent=self)
            return

        messagebox.showinfo("Metadata Saved", "✓ Metadata updated and physically verified successfully.", parent=self)
        if self.on_success_callback:
            self.on_success_callback()
        self.destroy()


class RescanDialog(tk.Toplevel):
    """Modal dialog displaying repository rescan results, metadata warnings, and repair actions."""

    def __init__(
        self,
        parent: tk.Widget,
        repo_path: str,
        initial_scan: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.repo_path = repo_path
        self.scan_result = initial_scan or backend.scan_repository(repo_path)

        self.title("Repository Rescan & Metadata Status")
        self.geometry("900x680")
        self.minsize(740, 520)
        self.transient(parent)
        self.grab_set()

        self.filter_var = tk.StringVar(value="All Problems")
        self._create_widgets()
        self._update_summary_display()
        self._populate_tree()

    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self, padding="18 14 18 14")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header Title
        ttk.Label(main_frame, text="Repository Metadata Rescan", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Label(
            main_frame,
            text=f"Repository: {self.repo_path}",
            font=("Segoe UI", 9),
            foreground="#4B5563",
        ).pack(anchor="w", pady=(0, 10))

        # Metric Summary Bar
        self.summary_card = ttk.Frame(main_frame, relief="ridge", borderwidth=1, padding="10 8 10 8")
        self.summary_card.pack(fill=tk.X, pady=(0, 10))

        self.total_lbl = tk.Label(self.summary_card, text="Total: 0", font=("Segoe UI", 10, "bold"), fg="#1F2937")
        self.total_lbl.pack(side=tk.LEFT, padx=(4, 16))

        self.complete_lbl = tk.Label(self.summary_card, text="Complete: 0", font=("Segoe UI", 10, "bold"), fg="#16A34A")
        self.complete_lbl.pack(side=tk.LEFT, padx=(0, 16))

        self.incomplete_lbl = tk.Label(self.summary_card, text="Incomplete: 0", font=("Segoe UI", 10, "bold"), fg="#D97706")
        self.incomplete_lbl.pack(side=tk.LEFT, padx=(0, 16))

        self.mismatch_lbl = tk.Label(self.summary_card, text="Category Mismatches: 0", font=("Segoe UI", 10, "bold"), fg="#EA580C")
        self.mismatch_lbl.pack(side=tk.LEFT, padx=(0, 16))

        self.unreadable_lbl = tk.Label(self.summary_card, text="Unreadable: 0", font=("Segoe UI", 10, "bold"), fg="#DC2626")
        self.unreadable_lbl.pack(side=tk.LEFT)

        # Filter & Action toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(toolbar, text="Filter:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        filter_options = [
            "All Problems",
            "Incomplete / Missing Metadata",
            "Category Mismatches",
            "Complete Problems",
            "Unreadable / Unknown Headers",
        ]
        self.filter_combo = ttk.Combobox(
            toolbar,
            textvariable=self.filter_var,
            values=filter_options,
            state="readonly",
            width=28,
            font=("Segoe UI", 9),
        )
        self.filter_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_tree())

        rescan_btn = ttk.Button(toolbar, text="↺ Rescan Again", command=self._on_rescan_again)
        rescan_btn.pack(side=tk.RIGHT)

        repair_top_btn = ttk.Button(toolbar, text="Complete / Repair Metadata", command=self._on_repair_selected)
        repair_top_btn.pack(side=tk.RIGHT, padx=(0, 8))

        self.dup_btn = ttk.Button(
            toolbar,
            text="⚠ Review / Normalize Duplicates",
            command=self._on_review_duplicates,
        )
        # Packed dynamically when duplicates exist

        # Scrolled Treeview Table
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols = ("status", "title", "filename", "category", "folder", "issues")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("status", text="Status", anchor="w")
        self.tree.heading("title", text="Problem Title", anchor="w")
        self.tree.heading("filename", text="Filename", anchor="w")
        self.tree.heading("category", text="Primary Category", anchor="w")
        self.tree.heading("folder", text="Folder Location", anchor="w")
        self.tree.heading("issues", text="Missing Fields / Warnings", anchor="w")

        self.tree.column("status", width=110, stretch=False)
        self.tree.column("title", width=180, stretch=True)
        self.tree.column("filename", width=140, stretch=False)
        self.tree.column("category", width=130, stretch=False)
        self.tree.column("folder", width=120, stretch=False)
        self.tree.column("issues", width=260, stretch=True)

        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.bind("<Double-1>", lambda e: self._on_repair_selected())

        # Tag styles for tree rows
        self.tree.tag_configure("complete", foreground="#16A34A")
        self.tree.tag_configure("incomplete", foreground="#D97706")
        self.tree.tag_configure("mismatch", foreground="#EA580C")
        self.tree.tag_configure("unreadable", foreground="#DC2626")

        # Bottom Bar
        bottom_bar = ttk.Frame(main_frame)
        bottom_bar.pack(fill=tk.X, pady=(4, 0))

        help_lbl = ttk.Label(
            bottom_bar,
            text="Tip: Double-click a problem or select it and click 'Complete / Repair Metadata' to fill missing fields.",
            font=("Segoe UI", 8),
            foreground="#6B7280",
        )
        help_lbl.pack(side=tk.LEFT)

        close_btn = ttk.Button(bottom_bar, text="Close", command=self.destroy)
        close_btn.pack(side=tk.RIGHT)

    def _update_summary_display(self) -> None:
        tot = self.scan_result.get("total_problems", 0)
        comp = self.scan_result.get("complete_count", 0)
        incomp = self.scan_result.get("incomplete_count", 0)
        mism = self.scan_result.get("mismatch_count", 0)
        unread = self.scan_result.get("unreadable_count", 0)

        self.total_lbl.configure(text=f"Total: {tot}")
        self.complete_lbl.configure(text=f"✓ Complete: {comp}")
        self.incomplete_lbl.configure(text=f"⚠ Incomplete: {incomp}")
        self.mismatch_lbl.configure(text=f"⚠ Mismatches: {mism}")
        self.unreadable_lbl.configure(text=f"✗ Unreadable: {unread}")

        # Check for metadata duplicates
        self.dup_result = backend.detect_metadata_duplicates(self.repo_path)
        if self.dup_result.get("has_duplicates"):
            cnt = self.dup_result.get("total_duplicate_groups", 0)
            self.dup_btn.configure(text=f"⚠ Duplicates ({cnt})")
            self.dup_btn.pack(side=tk.RIGHT, padx=(0, 8))
        else:
            self.dup_btn.pack_forget()

    def _populate_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        filter_mode = self.filter_var.get()
        problems = self.scan_result.get("problems", [])

        for idx, prob in enumerate(problems):
            status = prob.get("status", "incomplete")
            is_mismatch = prob.get("category_mismatch", False)

            # Filtering
            if filter_mode == "Incomplete / Missing Metadata" and status != "incomplete":
                continue
            elif filter_mode == "Category Mismatches" and not is_mismatch:
                continue
            elif filter_mode == "Complete Problems" and status != "complete":
                continue
            elif filter_mode == "Unreadable / Unknown Headers" and status != "unreadable":
                continue

            if status == "complete":
                status_text = "✓ Complete"
                tag = "complete"
            elif status == "incomplete":
                status_text = "⚠ Incomplete"
                tag = "incomplete"
            else:
                status_text = "✗ Unreadable"
                tag = "unreadable"

            if is_mismatch:
                status_text += " [Mismatch]"
                tag = "mismatch"

            # Issues text
            issues_list = []
            missing = prob.get("missing_fields", [])
            if missing:
                issues_list.append("Missing: " + ", ".join(missing))
            if is_mismatch:
                issues_list.append(f"Folder '{prob.get('folder_category')}' != Category '{prob.get('category')}'")

            issues_text = "; ".join(issues_list) if issues_list else "None (Complete)"

            self.tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(
                    status_text,
                    prob.get("title", ""),
                    prob.get("filename", ""),
                    prob.get("category", ""),
                    prob.get("folder_category", ""),
                    issues_text,
                ),
                tags=(tag,),
            )

    def _on_rescan_again(self) -> None:
        self.scan_result = backend.scan_repository(self.repo_path)
        self._update_summary_display()
        self._populate_tree()

    def _on_repair_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Selection Required", "Please select a problem from the list to repair.", parent=self)
            return

        prob_idx = int(sel[0])
        problem_data = self.scan_result.get("problems", [])[prob_idx]

        RepairMetadataDialog(
            parent=self,
            problem_data=problem_data,
            repo_path=self.repo_path,
            on_success_callback=self._on_rescan_again,
        )

    def _on_review_duplicates(self) -> None:
        """Open the duplicate review & explicit normalization dialog."""
        MetadataDuplicatesDialog(
            parent=self,
            repo_path=self.repo_path,
            dup_result=self.dup_result,
            on_success_callback=self._on_rescan_again,
        )


class MetadataDuplicatesDialog(tk.Toplevel):
    """Modal dialog for reviewing detected metadata duplicate variants and explicitly normalizing them."""

    def __init__(
        self,
        parent: tk.Widget,
        repo_path: str,
        dup_result: Dict[str, Any],
        on_success_callback=None,
    ) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.repo_path = repo_path
        self.dup_result = dup_result
        self.on_success_callback = on_success_callback

        self.title("Review Duplicate Metadata Values")
        self.geometry("820x560")
        self.minsize(700, 440)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._populate_tree()

    def _create_widgets(self) -> None:
        frame = ttk.Frame(self, padding="18 14 18 14")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Metadata Value Normalization & Deduplication", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            frame,
            text="The following metadata fields have casing/whitespace variants in the repository.\n"
                 "When normalized, affected file headers will be updated to their canonical value.\n"
                 "Solution code and file structures remain 100% byte-for-byte untouched.",
            font=("Segoe UI", 9),
            foreground="#4B5563",
        ).pack(anchor="w", pady=(0, 10))

        # Folder duplicates warning if any
        folder_dups = self.dup_result.get("category_folder_duplicates", [])
        if folder_dups:
            warn_frame = tk.Frame(frame, bg="#FEF3C7", relief="solid", borderwidth=1, padx=10, pady=6)
            warn_frame.pack(fill=tk.X, pady=(0, 8))
            f_names = ", ".join([" / ".join(fd.get("folder_variants", [])) for fd in folder_dups])
            tk.Label(
                warn_frame,
                text=f"⚠ Duplicate category folders detected on disk: {f_names}\n"
                     "These represent the same normalized category. Review before merging folders.",
                bg="#FEF3C7",
                fg="#92400E",
                font=("Segoe UI", 9),
                justify="left",
                anchor="w",
            ).pack(fill=tk.X)

        # Table of duplicate groups
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        cols = ("field", "canonical", "variants", "affected")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("field", text="Metadata Field", anchor="w")
        self.tree.heading("canonical", text="Canonical Value", anchor="w")
        self.tree.heading("variants", text="Detected Variants in Files", anchor="w")
        self.tree.heading("affected", text="Affected Files", anchor="w")

        self.tree.column("field", width=140, stretch=False)
        self.tree.column("canonical", width=160, stretch=False)
        self.tree.column("variants", width=320, stretch=True)
        self.tree.column("affected", width=110, stretch=False)

        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Button Bar
        btn_bar = ttk.Frame(frame)
        btn_bar.pack(fill=tk.X, pady=(4, 0))

        close_btn = ttk.Button(btn_bar, text="Close", command=self.destroy)
        close_btn.pack(side=tk.RIGHT, padx=(8, 0))

        normalize_btn = ttk.Button(
            btn_bar,
            text="Normalize Metadata",
            command=self._on_normalize,
        )
        normalize_btn.pack(side=tk.RIGHT)

    def _populate_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        groups = self.dup_result.get("duplicate_groups", [])

        for idx, grp in enumerate(groups):
            field = grp.get("field", "")
            canon = grp.get("canonical_value", "")
            variants_info = grp.get("variants", [])
            var_strs = []
            for v in variants_info:
                v_str = f"'{v['variant']}' ({v['count']})"
                if v.get("is_canonical"):
                    v_str += " [Canonical]"
                var_strs.append(v_str)

            var_summary = ", ".join(var_strs)
            aff_count = len(grp.get("affected_files", []))
            aff_text = f"{aff_count} file(s)" if aff_count else "None (Aligned)"

            self.tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(field, canon, var_summary, aff_text),
            )

    def _on_normalize(self) -> None:
        groups = self.dup_result.get("duplicate_groups", [])
        if not groups:
            messagebox.showinfo("No Duplicates", "No metadata duplicates found to normalize.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirm Metadata Normalization",
            "This will update metadata header comments in affected files to their canonical representation.\n\n"
            "• Problem solution code will remain 100% byte-for-byte unchanged.\n"
            "• Descriptions and dates will be preserved.\n\n"
            "Do you want to proceed?",
            parent=self,
        )
        if not confirm:
            return

        res = backend.normalize_repository_metadata(self.repo_path)
        if res.get("success"):
            cnt = res.get("normalized_files_count", 0)
            messagebox.showinfo(
                "Normalization Complete",
                f"✓ Successfully normalized metadata in {cnt} problem file(s).\n\n"
                "All solution implementations remain byte-for-byte preserved.",
                parent=self,
            )
            if self.on_success_callback:
                self.on_success_callback()
            self.destroy()
        else:
            errs = "\n".join(res.get("errors", []))
            messagebox.showerror(
                "Normalization Failed",
                f"Failed to normalize all files:\n{errs}",
                parent=self,
            )




class OpenFileConfirmDialog(tk.Toplevel):
    """Confirmation modal dialog for opening a problem source file with Windows Open With / default application."""

    def __init__(self, parent: tk.Widget, problem_data: Dict[str, Any], repo_path: str) -> None:
        super().__init__(parent)
        self.problem_data = problem_data
        self.repo_path = repo_path
        filename = Path(problem_data.get("file_path", "file")).name
        self.title("Open File")
        self.geometry("480x230")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding="20 18 20 18")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"Open {filename}", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 4))

        rel_display = problem_data.get("rel_path") or problem_data.get("file_path", "")
        ttk.Label(
            main_frame,
            text=f"Problem: {problem_data.get('title', '')}\nCategory: {problem_data.get('category', '')}\nFile Path: {rel_display}",
            font=("Segoe UI", 9),
            foreground="#4B5563",
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(
            main_frame,
            text="Choose an application to open this file.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 14))

        btn_row = ttk.Frame(main_frame)
        btn_row.pack(fill=tk.X)

        cancel_btn = ttk.Button(btn_row, text="Cancel", style="Secondary.TButton", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT)

        open_btn = ttk.Button(
            btn_row,
            text="Open With...",
            style="Accent.TButton",
            command=self._on_confirm_open,
        )
        open_btn.pack(side=tk.RIGHT, padx=(0, 8))

    def _on_confirm_open(self) -> None:
        file_path = self.problem_data.get("file_path", "")
        ok, msg = backend.open_file_with_system(file_path, self.repo_path)
        self.destroy()
        if not ok:
            messagebox.showerror("Cannot Open File", msg, parent=self.master)


# Backward compatibility alias
OpenInVSCodeDialog = OpenFileConfirmDialog


class DSAOrganizerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DSA Organizer")
        self.geometry = "1060x800"
        self.root.geometry(self.geometry)
        self.root.minsize(920, 660)

        # Style configuration
        self._configure_styles()

        # State
        self.selected_path_var = tk.StringVar(value="")
        self.remote_url_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Checking repository...")
        self._current_view = "home"
        self._sidebar_repo_var = tk.StringVar(value="📂 (No Repo)")
        self._cached_heatmap_weeks: List[List[Dict[str, Any]]] = []

        # Home Dashboard Stat StringVars
        self.stat_total_var = tk.StringVar(value="0")
        self.stat_week_var = tk.StringVar(value="0")
        self.stat_month_var = tk.StringVar(value="0")
        self.stat_streak_var = tk.StringVar(value="0 days")
        self.stat_longest_streak_var = tk.StringVar(value="Longest: 0 days")
        self.heatmap_hover_var = tk.StringVar(value="Hover over any square to inspect activity.")

        # Search View State
        self.search_query_var = tk.StringVar(value="")
        self.search_category_var = tk.StringVar(value="All Categories")
        self.search_platform_var = tk.StringVar(value="All Platforms")
        self.search_language_var = tk.StringVar(value="All Languages")
        self.search_importance_var = tk.StringVar(value="All")
        self.search_tag_var = tk.StringVar(value="")
        self.search_status_var = tk.StringVar(value="Ready")
        self._search_results_cache: List[Dict[str, Any]] = []

        # Category View State
        self.current_category_name = "Uncategorized"
        self._category_problems_cache: List[Dict[str, Any]] = []

        # Git State
        self._git_last_file: "Path | None" = None
        self._git_file_staged = False
        self._git_file_committed = False
        self._git_busy = False
        self._git_avail_var = tk.StringVar(value="Checking git...")
        self._git_root_display_var = tk.StringVar(value="Git Root: (None)")
        self._git_remote_display_var = tk.StringVar(value="Git Remote: (None)")
        self._git_file_var = tk.StringVar(value="None — create a problem first")
        self._commit_msg_var = tk.StringVar(value="")

        # Ensure core project directories exist
        dirs_ok, dirs_msg = backend.ensure_project_directories()
        if not dirs_ok:
            messagebox.showwarning("Directory Notice", dirs_msg)

        # Build UI layout
        self._create_widgets()

        # Initial data load
        self._load_initial_state()

    def _configure_styles(self) -> None:
        """Set up clean, native styling."""
        self.root.configure(bg="#F8FAFC")
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Main.TFrame", background="#F8FAFC")
        style.configure("Card.TFrame", background="#FFFFFF", relief="solid", borderwidth=1)
        style.configure("GitCard.TFrame", background="#F8FAFC", relief="solid", borderwidth=1)
        style.configure("Header.TLabel", background="#F8FAFC", foreground="#0F172A", font=("Segoe UI", 15, "bold"))
        style.configure("Subheader.TLabel", background="#F8FAFC", foreground="#64748B", font=("Segoe UI", 9))
        style.configure("CardTitle.TLabel", background="#FFFFFF", foreground="#0F172A", font=("Segoe UI", 11, "bold"))
        style.configure("CardText.TLabel", background="#FFFFFF", foreground="#334155", font=("Segoe UI", 9))
        style.configure("GitTitle.TLabel", background="#F8FAFC", foreground="#1E3A5F", font=("Segoe UI", 11, "bold"))
        style.configure("GitLabel.TLabel", background="#F8FAFC", foreground="#334155", font=("Segoe UI", 9))
        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), padding=5)
        style.configure("Secondary.TButton", font=("Segoe UI", 9), padding=5)
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), padding=5)
        style.configure("GitBtn.TButton", font=("Segoe UI", 8), padding=3)

    def _create_widgets(self) -> None:
        """Create the window layout: Clean Left Sidebar + Right Content Views."""
        app_container = ttk.Frame(self.root, style="Main.TFrame")
        app_container.pack(fill=tk.BOTH, expand=True)

        # ── 1. CLEAN LEFT SIDEBAR (Home, Search, Repository & Git) ─────────────
        self.sidebar_frame = tk.Frame(app_container, bg="#0F172A", width=195, padx=12, pady=16)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar_frame.pack_propagate(False)

        # App Brand Header
        brand_lbl = tk.Label(
            self.sidebar_frame,
            text="DSA ORGANIZER",
            font=("Segoe UI", 12, "bold"),
            fg="#F8FAFC",
            bg="#0F172A",
            anchor="w",
        )
        brand_lbl.pack(fill=tk.X, pady=(0, 2))

        sub_lbl = tk.Label(
            self.sidebar_frame,
            text="LOCAL UTILITY",
            font=("Segoe UI", 8, "bold"),
            fg="#64748B",
            bg="#0F172A",
            anchor="w",
        )
        sub_lbl.pack(fill=tk.X, pady=(0, 16))

        # Part 1: Cleaned Sidebar containing only Home, Search, and Repository & Git
        self.nav_btn_home = tk.Button(
            self.sidebar_frame,
            text="⌂   Home",
            font=("Segoe UI", 10, "bold"),
            bg="#1E293B",
            fg="#38BDF8",
            activebackground="#334155",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            anchor="w",
            cursor="hand2",
            command=lambda: self._show_view("home"),
        )
        self.nav_btn_home.pack(fill=tk.X, pady=(0, 4))

        self.nav_btn_search = tk.Button(
            self.sidebar_frame,
            text="🔎  Search",
            font=("Segoe UI", 10),
            bg="#0F172A",
            fg="#94A3B8",
            activebackground="#1E293B",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            anchor="w",
            cursor="hand2",
            command=lambda: self._show_view("search"),
        )
        self.nav_btn_search.pack(fill=tk.X, pady=(0, 4))

        self.nav_btn_repo = tk.Button(
            self.sidebar_frame,
            text="⚙   Repository & Git",
            font=("Segoe UI", 10),
            bg="#0F172A",
            fg="#94A3B8",
            activebackground="#1E293B",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            anchor="w",
            cursor="hand2",
            command=lambda: self._show_view("repo"),
        )
        self.nav_btn_repo.pack(fill=tk.X, pady=(0, 4))

        # Bottom Repository Indicator in Sidebar
        sidebar_spacer = tk.Frame(self.sidebar_frame, bg="#0F172A")
        sidebar_spacer.pack(fill=tk.BOTH, expand=True)

        self.sidebar_repo_lbl = tk.Label(
            self.sidebar_frame,
            textvariable=self._sidebar_repo_var,
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#1E293B",
            padx=8,
            pady=6,
            anchor="w",
            relief="flat",
        )
        self.sidebar_repo_lbl.pack(fill=tk.X, pady=(4, 0))

        # ── 2. RIGHT MAIN CONTENT AREA ───────────────────────────────────────────
        self.main_content_container = ttk.Frame(app_container, style="Main.TFrame")
        self.main_content_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Build View 1: Home Dashboard View
        self._create_home_view()

        # Build View 2: Search View
        self._create_search_view()

        # Build View 3: Repository & Git Configuration View
        self._create_repo_config_view()

        # Build View 4: Dedicated Topic / Category View
        self._create_category_view()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. HOME DASHBOARD VIEW
    # ──────────────────────────────────────────────────────────────────────────

    def _create_home_view(self) -> None:
        """Create the Home Dashboard screen layout."""
        self.home_frame = ttk.Frame(self.main_content_container, style="Main.TFrame", padding="16 12 16 12")

        # Top Bar: Title + Quick Action Buttons (+ Add New Problem, Rescan)
        top_bar = ttk.Frame(self.home_frame, style="Main.TFrame")
        top_bar.pack(fill=tk.X, pady=(0, 10))

        title_box = ttk.Frame(top_bar, style="Main.TFrame")
        title_box.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(title_box, text="DSA Practice Overview", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Real repository statistics and recorded activity",
            style="Subheader.TLabel",
        ).pack(anchor="w")

        btn_box = ttk.Frame(top_bar, style="Main.TFrame")
        btn_box.pack(side=tk.RIGHT)

        ttk.Button(
            btn_box,
            text="+ Add New Problem",
            style="Accent.TButton",
            command=self._on_add_problem,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            btn_box,
            text="↺ Rescan",
            style="Secondary.TButton",
            command=self._on_rescan_repository,
        ).pack(side=tk.LEFT)

        # Stat Cards Container (Row of 4 cards)
        stat_cards_frame = ttk.Frame(self.home_frame, style="Main.TFrame")
        stat_cards_frame.pack(fill=tk.X, pady=(0, 10))

        def make_stat_card(parent, title: str, var: tk.StringVar, sub_var_or_text, fg_color: str):
            card = tk.Frame(parent, bg="#FFFFFF", relief="solid", borderwidth=1, padx=12, pady=10)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

            tk.Label(card, text=title.upper(), font=("Segoe UI", 8, "bold"), fg="#64748B", bg="#FFFFFF", anchor="w").pack(fill=tk.X)
            tk.Label(card, textvariable=var, font=("Segoe UI", 20, "bold"), fg=fg_color, bg="#FFFFFF", anchor="w").pack(fill=tk.X, pady=(2, 0))

            if isinstance(sub_var_or_text, tk.StringVar):
                tk.Label(card, textvariable=sub_var_or_text, font=("Segoe UI", 8), fg="#475569", bg="#FFFFFF", anchor="w").pack(fill=tk.X, pady=(2, 0))
            else:
                tk.Label(card, text=str(sub_var_or_text), font=("Segoe UI", 8), fg="#64748B", bg="#FFFFFF", anchor="w").pack(fill=tk.X, pady=(2, 0))
            return card

        make_stat_card(stat_cards_frame, "Total Problems", self.stat_total_var, "Recognized solutions", "#0F172A")
        make_stat_card(stat_cards_frame, "This Week", self.stat_week_var, "Mon → Sun activity", "#2563EB")
        make_stat_card(stat_cards_frame, "This Month", self.stat_month_var, "Current calendar month", "#0284C7")
        make_stat_card(stat_cards_frame, "Current Streak", self.stat_streak_var, self.stat_longest_streak_var, "#16A34A")

        # Main Body: Split between Data and Empty State
        self.home_empty_frame = tk.Frame(self.home_frame, bg="#FFFFFF", relief="solid", borderwidth=1, padx=30, pady=40)

        empty_title = tk.Label(
            self.home_empty_frame,
            text="No DSA problems found in repository",
            font=("Segoe UI", 13, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        )
        empty_title.pack(pady=(0, 6))

        empty_desc = tk.Label(
            self.home_empty_frame,
            text="Add your first DSA problem to start building your recorded repository activity and dashboard metrics.",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#FFFFFF",
        )
        empty_desc.pack(pady=(0, 16))

        ttk.Button(
            self.home_empty_frame,
            text="+ Add First Problem",
            style="Accent.TButton",
            command=self._on_add_problem,
        ).pack()

        # Data Container (when problems > 0)
        self.home_data_frame = ttk.Frame(self.home_frame, style="Main.TFrame")

        # Middle Row: Categories (Left) + Recent Problems (Right)
        middle_row = ttk.Frame(self.home_data_frame, style="Main.TFrame")
        middle_row.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # ── Left Column: Categories ──
        cats_card = tk.Frame(middle_row, bg="#FFFFFF", relief="solid", borderwidth=1, padx=12, pady=10)
        cats_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(cats_card, text="CATEGORIES", font=("Segoe UI", 9, "bold"), fg="#0F172A", bg="#FFFFFF", anchor="w").pack(fill=tk.X, pady=(0, 6))

        # Most & Less Practiced Highlights Box
        highlights_frame = tk.Frame(cats_card, bg="#F8FAFC", padx=8, pady=6, relief="solid", borderwidth=1)
        highlights_frame.pack(fill=tk.X, pady=(0, 8))

        # Most Practiced Sub-box
        tk.Label(highlights_frame, text="Most Practiced", font=("Segoe UI", 8, "bold"), fg="#1E3A5F", bg="#F8FAFC", anchor="w").pack(fill=tk.X)
        self.most_practiced_container = tk.Frame(highlights_frame, bg="#F8FAFC")
        self.most_practiced_container.pack(fill=tk.X, pady=(2, 6))

        # Less Practiced Sub-box
        tk.Label(highlights_frame, text="Less Practiced", font=("Segoe UI", 8, "bold"), fg="#64748B", bg="#F8FAFC", anchor="w").pack(fill=tk.X)
        self.least_practiced_container = tk.Frame(highlights_frame, bg="#F8FAFC")
        self.least_practiced_container.pack(fill=tk.X, pady=(2, 0))

        # All Categories Breakdown Table
        tk.Label(cats_card, text="All Categories Breakdown", font=("Segoe UI", 8, "bold"), fg="#64748B", bg="#FFFFFF", anchor="w").pack(fill=tk.X, pady=(4, 2))

        cat_tree_frame = ttk.Frame(cats_card)
        cat_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.cats_tree = ttk.Treeview(
            cat_tree_frame,
            columns=("category", "count"),
            show="headings",
            height=5,
            selectmode="browse",
        )
        self.cats_tree.heading("category", text="Primary Category", anchor="w")
        self.cats_tree.heading("count", text="Count", anchor="e")
        self.cats_tree.column("category", width=140, anchor="w")
        self.cats_tree.column("count", width=50, anchor="e")

        cat_scroll = ttk.Scrollbar(cat_tree_frame, orient=tk.VERTICAL, command=self.cats_tree.yview)
        self.cats_tree.configure(yscrollcommand=cat_scroll.set)
        self.cats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.cats_tree.bind("<Double-1>", lambda e: self._on_home_cat_selected())
        self.cats_tree.bind("<ButtonRelease-1>", lambda e: self._on_home_cat_selected())

        # ── Right Column: Recent Problems ──
        recent_card = tk.Frame(middle_row, bg="#FFFFFF", relief="solid", borderwidth=1, padx=12, pady=10)
        recent_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(recent_card, text="RECENT PROBLEMS", font=("Segoe UI", 9, "bold"), fg="#0F172A", bg="#FFFFFF", anchor="w").pack(fill=tk.X, pady=(0, 6))

        recent_tree_frame = ttk.Frame(recent_card)
        recent_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.recent_tree = ttk.Treeview(
            recent_tree_frame,
            columns=("title", "category", "platform", "date"),
            show="headings",
            height=9,
            selectmode="browse",
        )
        self.recent_tree.heading("title", text="Title", anchor="w")
        self.recent_tree.heading("category", text="Category", anchor="w")
        self.recent_tree.heading("platform", text="Platform", anchor="w")
        self.recent_tree.heading("date", text="Added Date", anchor="w")

        self.recent_tree.column("title", width=130, anchor="w")
        self.recent_tree.column("category", width=85, anchor="w")
        self.recent_tree.column("platform", width=75, anchor="w")
        self.recent_tree.column("date", width=85, anchor="w")

        recent_scroll = ttk.Scrollbar(recent_tree_frame, orient=tk.VERTICAL, command=self.recent_tree.yview)
        self.recent_tree.configure(yscrollcommand=recent_scroll.set)
        self.recent_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        recent_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Bottom Row: Activity Heatmap ──
        heatmap_card = tk.Frame(self.home_data_frame, bg="#FFFFFF", relief="solid", borderwidth=1, padx=12, pady=8)
        heatmap_card.pack(fill=tk.X)

        hm_header = tk.Frame(heatmap_card, bg="#FFFFFF")
        hm_header.pack(fill=tk.X, pady=(0, 4))

        tk.Label(hm_header, text="ACTIVITY HEATMAP — LAST 12 WEEKS", font=("Segoe UI", 8, "bold"), fg="#0F172A", bg="#FFFFFF").pack(side=tk.LEFT)

        # Heatmap legend
        legend_frame = tk.Frame(hm_header, bg="#FFFFFF")
        legend_frame.pack(side=tk.RIGHT)
        tk.Label(legend_frame, text="Less ", font=("Segoe UI", 7), fg="#64748B", bg="#FFFFFF").pack(side=tk.LEFT)
        for col in ("#E2E8F0", "#93C5FD", "#3B82F6", "#1D4ED8"):
            tk.Label(legend_frame, text="■", font=("Segoe UI", 8), fg=col, bg="#FFFFFF").pack(side=tk.LEFT, padx=1)
        tk.Label(legend_frame, text=" More", font=("Segoe UI", 7), fg="#64748B", bg="#FFFFFF").pack(side=tk.LEFT)

        # Heatmap Canvas (height=130 to allow full rendering of month headers and all 7 rows without clipping)
        self.heatmap_canvas = tk.Canvas(
            heatmap_card,
            height=130,
            bg="#FFFFFF",
            highlightthickness=0,
            relief="flat",
        )
        self.heatmap_canvas.pack(fill=tk.X, pady=(2, 2))
        self.heatmap_canvas.bind("<Motion>", self._on_heatmap_hover)
        self.heatmap_canvas.bind("<Leave>", lambda e: self.heatmap_hover_var.set("Hover over any day square to view recorded activity."))

        # Heatmap status / hover text
        self.heatmap_hover_label = tk.Label(
            heatmap_card,
            textvariable=self.heatmap_hover_var,
            font=("Segoe UI", 8),
            fg="#475569",
            bg="#FFFFFF",
            anchor="w",
        )
        self.heatmap_hover_label.pack(fill=tk.X)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. SEARCH VIEW (PHASE 6)
    # ──────────────────────────────────────────────────────────────────────────

    def _create_search_view(self) -> None:
        """Create the Search and Metadata/File Browser screen layout."""
        self.search_frame = ttk.Frame(self.main_content_container, style="Main.TFrame", padding="16 12 16 12")

        # Top Bar: Title & Subtitle
        top_bar = ttk.Frame(self.search_frame, style="Main.TFrame")
        top_bar.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(top_bar, text="Search Problems", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            top_bar,
            text="Search and filter repository problems by structured metadata header fields",
            style="Subheader.TLabel",
        ).pack(anchor="w")

        # Search Box Card
        search_card = tk.Frame(self.search_frame, bg="#FFFFFF", relief="solid", borderwidth=1, padx=12, pady=10)
        search_card.pack(fill=tk.X, pady=(0, 8))

        input_row = ttk.Frame(search_card)
        input_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(input_row, text="🔎", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(0, 6))
        self.search_entry = ttk.Entry(input_row, textvariable=self.search_query_var, font=("Segoe UI", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.search_query_var.trace_add("write", lambda *args: self._on_search_query_changed())

        ttk.Button(
            input_row,
            text="Clear",
            style="Secondary.TButton",
            command=self._on_search_clear,
        ).pack(side=tk.RIGHT)

        # Filters Bar
        filters_row = ttk.Frame(search_card)
        filters_row.pack(fill=tk.X)

        # 1. Category Filter Dropdown
        ttk.Label(filters_row, text="Category:", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.search_cat_combo = ttk.Combobox(
            filters_row,
            textvariable=self.search_category_var,
            state="readonly",
            width=16,
        )
        self.search_cat_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.search_cat_combo.bind("<<ComboboxSelected>>", lambda e: self._on_search_query_changed())

        # 2. Platform Filter Dropdown
        ttk.Label(filters_row, text="Platform:", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.search_plat_combo = ttk.Combobox(
            filters_row,
            textvariable=self.search_platform_var,
            state="readonly",
            width=14,
        )
        self.search_plat_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.search_plat_combo.bind("<<ComboboxSelected>>", lambda e: self._on_search_query_changed())

        # 3. Language Filter Dropdown
        ttk.Label(filters_row, text="Language:", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.search_lang_combo = ttk.Combobox(
            filters_row,
            textvariable=self.search_language_var,
            state="readonly",
            width=12,
        )
        self.search_lang_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.search_lang_combo.bind("<<ComboboxSelected>>", lambda e: self._on_search_query_changed())

        # 4. Importance Filter Dropdown
        ttk.Label(filters_row, text="Importance:", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.search_imp_combo = ttk.Combobox(
            filters_row,
            textvariable=self.search_importance_var,
            values=["All", "5", "4", "3", "2", "1"],
            state="readonly",
            width=6,
        )
        self.search_imp_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.search_imp_combo.bind("<<ComboboxSelected>>", lambda e: self._on_search_query_changed())

        ttk.Button(
            filters_row,
            text="Reset Filters",
            style="Secondary.TButton",
            command=self._on_search_reset_filters,
        ).pack(side=tk.RIGHT)

        # Split Content Area: Category Browser (Left) + Search Results (Right)
        split_frame = ttk.Frame(self.search_frame, style="Main.TFrame")
        split_frame.pack(fill=tk.BOTH, expand=True)

        # ── Left: Category Browser ──
        cat_browser_card = tk.Frame(split_frame, bg="#FFFFFF", relief="solid", borderwidth=1, padx=10, pady=8, width=190)
        cat_browser_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        cat_browser_card.pack_propagate(False)

        tk.Label(cat_browser_card, text="CATEGORIES", font=("Segoe UI", 8, "bold"), fg="#0F172A", bg="#FFFFFF", anchor="w").pack(fill=tk.X, pady=(0, 4))

        cat_list_frame = ttk.Frame(cat_browser_card)
        cat_list_frame.pack(fill=tk.BOTH, expand=True)

        self.search_cat_tree = ttk.Treeview(
            cat_list_frame,
            columns=("category", "count"),
            show="headings",
            selectmode="browse",
        )
        self.search_cat_tree.heading("category", text="Category", anchor="w")
        self.search_cat_tree.heading("count", text="#", anchor="e")
        self.search_cat_tree.column("category", width=120, anchor="w")
        self.search_cat_tree.column("count", width=40, anchor="e")
        self.search_cat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.search_cat_tree.bind("<<TreeviewSelect>>", self._on_category_browser_selected)

        # ── Right: Search Results ──
        results_card = tk.Frame(split_frame, bg="#FFFFFF", relief="solid", borderwidth=1, padx=12, pady=8)
        results_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        results_header_row = tk.Frame(results_card, bg="#FFFFFF")
        results_header_row.pack(fill=tk.X, pady=(0, 6))

        self.search_results_count_lbl = tk.Label(
            results_header_row,
            textvariable=self.search_status_var,
            font=("Segoe UI", 9, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
            anchor="w",
        )
        self.search_results_count_lbl.pack(side=tk.LEFT)

        self.open_file_btn = ttk.Button(
            results_header_row,
            text="Open File",
            style="Accent.TButton",
            command=self._on_open_selected_problem,
        )
        self.open_file_btn.pack(side=tk.RIGHT)

        # Results Table
        results_tree_frame = ttk.Frame(results_card)
        results_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.search_results_tree = ttk.Treeview(
            results_tree_frame,
            columns=("title", "category", "platform", "language", "importance", "date", "path"),
            show="headings",
            selectmode="browse",
        )
        self.search_results_tree.heading("title", text="Title", anchor="w")
        self.search_results_tree.heading("category", text="Category", anchor="w")
        self.search_results_tree.heading("platform", text="Platform", anchor="w")
        self.search_results_tree.heading("language", text="Language", anchor="w")
        self.search_results_tree.heading("importance", text="Importance", anchor="center")
        self.search_results_tree.heading("date", text="Added Date", anchor="w")
        self.search_results_tree.heading("path", text="Relative Path", anchor="w")

        self.search_results_tree.column("title", width=140, anchor="w")
        self.search_results_tree.column("category", width=95, anchor="w")
        self.search_results_tree.column("platform", width=85, anchor="w")
        self.search_results_tree.column("language", width=65, anchor="w")
        self.search_results_tree.column("importance", width=75, anchor="center")
        self.search_results_tree.column("date", width=85, anchor="w")
        self.search_results_tree.column("path", width=150, anchor="w")

        results_scroll = ttk.Scrollbar(results_tree_frame, orient=tk.VERTICAL, command=self.search_results_tree.yview)
        self.search_results_tree.configure(yscrollcommand=results_scroll.set)
        self.search_results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.search_results_tree.bind("<Double-1>", lambda e: self._on_open_selected_problem())

    # ──────────────────────────────────────────────────────────────────────────
    # 3. REPOSITORY & GIT CONFIGURATION VIEW
    # ──────────────────────────────────────────────────────────────────────────

    def _create_repo_config_view(self) -> None:
        """Create the Repository Configuration & Git screen (Phase 0, 1, 2 view)."""
        self.repo_config_frame = ttk.Frame(self.main_content_container, style="Main.TFrame", padding="20 16 20 16")

        # Header Title
        title_label = ttk.Label(self.repo_config_frame, text="Repository & Git Configuration", style="Header.TLabel")
        title_label.pack(anchor="w", pady=(0, 2))

        subtitle_label = ttk.Label(
            self.repo_config_frame,
            text="Configure your local DSA Git repository and remote connection",
            style="Subheader.TLabel",
        )
        subtitle_label.pack(anchor="w", pady=(0, 10))

        # Main Card Container (Repository Configuration)
        self.card = ttk.Frame(self.repo_config_frame, style="Card.TFrame", padding="16 14 16 14")
        self.card.pack(fill=tk.X, expand=False)

        # Top Action Bar inside Card
        action_bar = ttk.Frame(self.card, style="Card.TFrame")
        action_bar.pack(fill=tk.X, pady=(0, 8))

        self.section_label = ttk.Label(action_bar, text="Repository Configuration", style="CardTitle.TLabel")
        self.section_label.pack(side=tk.LEFT, anchor="w")

        # 1. Local Repository Path Row
        path_label = ttk.Label(self.card, text="Local Repository Path:", style="CardText.TLabel")
        path_label.pack(anchor="w", pady=(0, 2))

        input_frame = ttk.Frame(self.card, style="Card.TFrame")
        input_frame.pack(fill=tk.X, pady=(0, 6))

        self.path_entry = ttk.Entry(input_frame, textvariable=self.selected_path_var, font=("Segoe UI", 9))
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.browse_btn = ttk.Button(
            input_frame,
            text="Select Folder",
            style="Secondary.TButton",
            command=self._on_browse,
        )
        self.browse_btn.pack(side=tk.RIGHT)

        # 2. Git Remote URL Row
        remote_label = ttk.Label(self.card, text="Git Remote URL:", style="CardText.TLabel")
        remote_label.pack(anchor="w", pady=(0, 2))

        remote_frame = ttk.Frame(self.card, style="Card.TFrame")
        remote_frame.pack(fill=tk.X, pady=(0, 6))

        self.remote_entry = ttk.Entry(remote_frame, textvariable=self.remote_url_var, font=("Segoe UI", 9))
        self.remote_entry.pack(fill=tk.X)

        # Status Label Display
        status_title = ttk.Label(self.card, text="Status:", style="CardText.TLabel")
        status_title.pack(anchor="w", pady=(2, 2))

        self.status_display = tk.Label(
            self.card,
            textvariable=self.status_var,
            bg="#FFFFFF",
            fg="#2563EB",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            justify="left",
            wraplength=600,
        )
        self.status_display.pack(fill=tk.X, pady=(0, 6))

        # Save Button
        button_bar = ttk.Frame(self.card, style="Card.TFrame")
        button_bar.pack(anchor="w", pady=(0, 6))

        self.save_btn = ttk.Button(
            button_bar,
            text="Save & Verify Git Configuration",
            style="Action.TButton",
            command=self._on_save,
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Result / Feedback Display Box
        self.feedback_box = tk.Label(
            self.card,
            text="",
            bg="#FFFFFF",
            fg="#374151",
            font=("Segoe UI", 9),
            anchor="nw",
            justify="left",
            relief="groove",
            borderwidth=1,
            padx=10,
            pady=4,
            wraplength=600,
            height=3,
        )
        self.feedback_box.pack(fill=tk.X, expand=False, pady=(2, 0))

        # ── Git Integration Card ───────────────────────────────────────────────
        self.git_card = ttk.Frame(self.repo_config_frame, style="GitCard.TFrame", padding="14 10 14 10")
        self.git_card.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        # Git header bar
        git_header = ttk.Frame(self.git_card, style="GitCard.TFrame")
        git_header.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(git_header, text="⎷  Git Integration", style="GitTitle.TLabel").pack(side=tk.LEFT)
        self.git_refresh_btn = ttk.Button(
            git_header,
            text="↺ Refresh Status",
            style="GitBtn.TButton",
            command=self._on_refresh_git_status,
        )
        self.git_refresh_btn.pack(side=tk.RIGHT)

        # Git availability / status line
        self.git_avail_label = tk.Label(
            self.git_card,
            textvariable=self._git_avail_var,
            bg="#F8FAFC",
            fg="#374151",
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        self.git_avail_label.pack(fill=tk.X, pady=(0, 2))

        # Git root and remote lines
        info_row = ttk.Frame(self.git_card, style="GitCard.TFrame")
        info_row.pack(fill=tk.X, pady=(0, 4))

        self.git_root_label = tk.Label(
            info_row,
            textvariable=self._git_root_display_var,
            bg="#F8FAFC",
            fg="#4B5563",
            font=("Segoe UI", 8),
            anchor="w",
            justify="left",
        )
        self.git_root_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.git_remote_label = tk.Label(
            info_row,
            textvariable=self._git_remote_display_var,
            bg="#F8FAFC",
            fg="#4B5563",
            font=("Segoe UI", 8),
            anchor="w",
            justify="left",
        )
        self.git_remote_label.pack(side=tk.RIGHT)

        # Last created file row
        lf_row = ttk.Frame(self.git_card, style="GitCard.TFrame")
        lf_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(lf_row, text="Last created file:", style="GitLabel.TLabel").pack(side=tk.LEFT)
        self.git_file_label = tk.Label(
            lf_row,
            textvariable=self._git_file_var,
            bg="#F8FAFC",
            fg="#1E3A5F",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            justify="left",
        )
        self.git_file_label.pack(side=tk.LEFT, padx=(6, 0))

        # Stage / Commit / Push action bar
        action_row = ttk.Frame(self.git_card, style="GitCard.TFrame")
        action_row.pack(fill=tk.X, pady=(0, 4))

        self.git_stage_btn = ttk.Button(
            action_row,
            text="Stage File",
            style="GitBtn.TButton",
            command=self._on_stage_file,
            state=tk.DISABLED,
        )
        self.git_stage_btn.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Label(action_row, text="Commit msg:", style="GitLabel.TLabel").pack(side=tk.LEFT)
        self.commit_msg_entry = ttk.Entry(
            action_row,
            textvariable=self._commit_msg_var,
            font=("Segoe UI", 9),
            width=24,
        )
        self.commit_msg_entry.pack(side=tk.LEFT, padx=(4, 6), fill=tk.X, expand=True)

        self.git_commit_btn = ttk.Button(
            action_row,
            text="Commit",
            style="GitBtn.TButton",
            command=self._on_commit,
        )
        self.git_commit_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.git_push_btn = ttk.Button(
            action_row,
            text="Push",
            style="GitBtn.TButton",
            command=self._on_push,
        )
        self.git_push_btn.pack(side=tk.LEFT)

        # Git log / output area
        ttk.Label(self.git_card, text="Git Activity Log", style="GitLabel.TLabel").pack(anchor="w", pady=(0, 2))
        self.git_log = ScrolledText(
            self.git_card,
            height=4,
            font=("Consolas", 8),
            bg="#0F172A",
            fg="#94A3B8",
            insertbackground="#94A3B8",
            wrap=tk.WORD,
            relief="flat",
            borderwidth=0,
        )
        self.git_log.pack(fill=tk.BOTH, expand=True)
        self.git_log.configure(state=tk.DISABLED)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. TOPIC / CATEGORY VIEW (PHASE 7)
    # ──────────────────────────────────────────────────────────────────────────

    def _create_category_view(self) -> None:
        """Create the dedicated Topic / Category View screen layout."""
        self.category_frame = ttk.Frame(self.main_content_container, style="Main.TFrame", padding="16 12 16 12")

        # Top Navigation Bar: [ ← Home ] and Action Buttons
        nav_bar = ttk.Frame(self.category_frame, style="Main.TFrame")
        nav_bar.pack(fill=tk.X, pady=(0, 8))

        back_btn = ttk.Button(
            nav_bar,
            text="← Home",
            style="Secondary.TButton",
            command=lambda: self._show_view("home"),
        )
        back_btn.pack(side=tk.LEFT)

        btn_box = ttk.Frame(nav_bar, style="Main.TFrame")
        btn_box.pack(side=tk.RIGHT)

        ttk.Button(
            btn_box,
            text="+ Add New Problem",
            style="Accent.TButton",
            command=self._on_add_problem_in_category,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            btn_box,
            text="↺ Rescan",
            style="Secondary.TButton",
            command=self._on_rescan_repository,
        ).pack(side=tk.LEFT)

        # Header Title: Category Name & Problem Count
        header_box = ttk.Frame(self.category_frame, style="Main.TFrame")
        header_box.pack(fill=tk.X, pady=(0, 8))

        self.cat_view_title_label = ttk.Label(header_box, text="Category Name", style="Header.TLabel")
        self.cat_view_title_label.pack(anchor="w")

        self.cat_view_subtitle_label = ttk.Label(header_box, text="0 Problems", style="Subheader.TLabel")
        self.cat_view_subtitle_label.pack(anchor="w")

        # ── Overview Card: Category Statistics ──
        self.cat_overview_card = tk.Frame(self.category_frame, bg="#FFFFFF", relief="solid", borderwidth=1, padx=14, pady=10)
        self.cat_overview_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            self.cat_overview_card,
            text="CATEGORY OVERVIEW",
            font=("Segoe UI", 9, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 8))

        # Stats grid rows inside card
        stats_grid = tk.Frame(self.cat_overview_card, bg="#FFFFFF")
        stats_grid.pack(fill=tk.X)

        # Row 0: Problems Count
        tk.Label(stats_grid, text="Problems", font=("Segoe UI", 9, "bold"), fg="#64748B", bg="#FFFFFF", width=14, anchor="w").grid(row=0, column=0, sticky="w", pady=2)
        self.cat_stat_problems_lbl = tk.Label(stats_grid, text="0", font=("Segoe UI", 9), fg="#0F172A", bg="#FFFFFF", anchor="w")
        self.cat_stat_problems_lbl.grid(row=0, column=1, sticky="w", pady=2)

        # Row 1: Platforms
        tk.Label(stats_grid, text="Platforms", font=("Segoe UI", 9, "bold"), fg="#64748B", bg="#FFFFFF", width=14, anchor="w").grid(row=1, column=0, sticky="w", pady=2)
        self.cat_stat_platforms_lbl = tk.Label(stats_grid, text="-", font=("Segoe UI", 9), fg="#0F172A", bg="#FFFFFF", anchor="w")
        self.cat_stat_platforms_lbl.grid(row=1, column=1, sticky="w", pady=2)

        # Row 2: Languages
        tk.Label(stats_grid, text="Languages", font=("Segoe UI", 9, "bold"), fg="#64748B", bg="#FFFFFF", width=14, anchor="w").grid(row=2, column=0, sticky="w", pady=2)
        self.cat_stat_languages_lbl = tk.Label(stats_grid, text="-", font=("Segoe UI", 9), fg="#0F172A", bg="#FFFFFF", anchor="w")
        self.cat_stat_languages_lbl.grid(row=2, column=1, sticky="w", pady=2)

        # Row 3: Latest Added
        tk.Label(stats_grid, text="Latest Added", font=("Segoe UI", 9, "bold"), fg="#64748B", bg="#FFFFFF", width=14, anchor="w").grid(row=3, column=0, sticky="w", pady=2)
        self.cat_stat_latest_lbl = tk.Label(stats_grid, text="-", font=("Segoe UI", 9), fg="#0F172A", bg="#FFFFFF", anchor="w")
        self.cat_stat_latest_lbl.grid(row=3, column=1, sticky="w", pady=2)

        # ── Problems Section ──
        prob_sec_header = ttk.Frame(self.category_frame, style="Main.TFrame")
        prob_sec_header.pack(fill=tk.X, pady=(4, 4))
        ttk.Label(prob_sec_header, text="Problems", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)

        # Empty Category Container
        self.cat_empty_frame = tk.Frame(self.category_frame, bg="#FFFFFF", relief="solid", borderwidth=1, padx=20, pady=30)
        tk.Label(
            self.cat_empty_frame,
            text="No problems are currently recorded in this category.",
            font=("Segoe UI", 10),
            fg="#64748B",
            bg="#FFFFFF",
        ).pack(pady=(0, 10))
        ttk.Button(
            self.cat_empty_frame,
            text="+ Add New Problem",
            style="Accent.TButton",
            command=self._on_add_problem_in_category,
        ).pack()

        # Populated Category Container (Problems Treeview Table)
        self.cat_table_card = tk.Frame(self.category_frame, bg="#FFFFFF", relief="solid", borderwidth=1, padx=10, pady=8)
        self.cat_table_card.pack(fill=tk.BOTH, expand=True)

        tree_frame = ttk.Frame(self.cat_table_card)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.cat_problems_tree = ttk.Treeview(
            tree_frame,
            columns=("title", "platform", "language", "importance", "added", "tags"),
            show="headings",
            selectmode="browse",
        )
        self.cat_problems_tree.heading("title", text="Problem", anchor="w")
        self.cat_problems_tree.heading("platform", text="Platform", anchor="w")
        self.cat_problems_tree.heading("language", text="Language", anchor="w")
        self.cat_problems_tree.heading("importance", text="Importance", anchor="w")
        self.cat_problems_tree.heading("added", text="Added Date", anchor="w")
        self.cat_problems_tree.heading("tags", text="Tags", anchor="w")

        self.cat_problems_tree.column("title", width=220, anchor="w")
        self.cat_problems_tree.column("platform", width=120, anchor="w")
        self.cat_problems_tree.column("language", width=80, anchor="w")
        self.cat_problems_tree.column("importance", width=90, anchor="w")
        self.cat_problems_tree.column("added", width=120, anchor="w")
        self.cat_problems_tree.column("tags", width=150, anchor="w")

        cat_tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.cat_problems_tree.yview)
        self.cat_problems_tree.configure(yscrollcommand=cat_tree_scroll.set)
        self.cat_problems_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.cat_problems_tree.bind("<Double-1>", lambda e: self._on_open_selected_category_problem())

        # Action Bar below Table
        cat_action_bar = ttk.Frame(self.cat_table_card)
        cat_action_bar.pack(fill=tk.X, pady=(6, 0))

        ttk.Button(
            cat_action_bar,
            text="Open File",
            style="Secondary.TButton",
            command=self._on_open_selected_category_problem,
        ).pack(side=tk.LEFT)

        self.cat_table_status_lbl = ttk.Label(
            cat_action_bar,
            text="",
            font=("Segoe UI", 8),
            foreground="#64748B",
        )
        self.cat_table_status_lbl.pack(side=tk.RIGHT, padx=(0, 4))

    # ──────────────────────────────────────────────────────────────────────────
    # VIEW NAVIGATION & REFRESH LOGIC
    # ──────────────────────────────────────────────────────────────────────────

    def _show_view(self, view_name: str, category_name: str = "") -> None:
        """Switch between Home, Search, Repository Configuration, and Category views."""
        self._current_view = view_name

        # Reset all sidebar buttons
        self.nav_btn_home.configure(bg="#0F172A", fg="#94A3B8", font=("Segoe UI", 10))
        self.nav_btn_search.configure(bg="#0F172A", fg="#94A3B8", font=("Segoe UI", 10))
        self.nav_btn_repo.configure(bg="#0F172A", fg="#94A3B8", font=("Segoe UI", 10))

        self.home_frame.pack_forget()
        self.search_frame.pack_forget()
        self.repo_config_frame.pack_forget()
        self.category_frame.pack_forget()

        if view_name == "home":
            self.nav_btn_home.configure(bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 10, "bold"))
            self.home_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_home_dashboard()
        elif view_name == "search":
            self.nav_btn_search.configure(bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 10, "bold"))
            self.search_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_search_view()
        elif view_name == "category":
            self.current_category_name = category_name or getattr(self, "current_category_name", "Uncategorized")
            self.category_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_category_view()
        else:
            self.nav_btn_repo.configure(bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 10, "bold"))
            self.repo_config_frame.pack(fill=tk.BOTH, expand=True)

    def _show_category_view(self, category_name: str) -> None:
        """Open the dedicated Category View for the selected category."""
        self._show_view("category", category_name=category_name)

    def _refresh_category_view(self) -> None:
        """Fetch category view data from backend and refresh all UI elements."""
        repo_path = self.selected_path_var.get().strip()
        category_name = getattr(self, "current_category_name", "Uncategorized")
        cat_data = backend.get_category_view(repo_path, category_name)

        display_name = cat_data.get("category", category_name)
        prob_count = cat_data.get("problem_count", 0)
        self.current_category_name = display_name

        self.cat_view_title_label.configure(text=display_name)
        self.cat_view_subtitle_label.configure(
            text=f"{prob_count} {'Problem' if prob_count == 1 else 'Problems'}"
        )

        # Overview Card Stats
        self.cat_stat_problems_lbl.configure(text=str(prob_count))

        plat_counts = cat_data.get("platform_counts", {})
        if plat_counts:
            plat_str = " · ".join([f"{p} ({c})" if c > 1 else p for p, c in plat_counts.items()])
        else:
            plat_str = "-"
        self.cat_stat_platforms_lbl.configure(text=plat_str)

        lang_counts = cat_data.get("language_counts", {})
        if lang_counts:
            lang_str = " · ".join([f"{l} ({c})" if c > 1 else l for l, c in lang_counts.items()])
        else:
            lang_str = "-"
        self.cat_stat_languages_lbl.configure(text=lang_str)

        latest = cat_data.get("latest_added")
        self.cat_stat_latest_lbl.configure(text=latest if latest else "-")

        # Problems List
        problems = cat_data.get("problems", [])
        self._category_problems_cache = problems

        if prob_count == 0:
            self.cat_table_card.pack_forget()
            self.cat_empty_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        else:
            self.cat_empty_frame.pack_forget()
            self.cat_table_card.pack(fill=tk.BOTH, expand=True)

            self.cat_problems_tree.delete(*self.cat_problems_tree.get_children())
            for idx, prob in enumerate(problems):
                raw_imp = prob.get("importance", "")
                imp_str = f"★ {raw_imp}" if raw_imp else "-"
                added_str = prob.get("added_date", "")
                dt = backend.parse_date_safely(added_str)
                if dt is not None:
                    display_date = dt.strftime("%b %d, %Y")
                else:
                    display_date = added_str

                self.cat_problems_tree.insert(
                    "",
                    tk.END,
                    iid=str(idx),
                    values=(
                        prob.get("title", ""),
                        prob.get("platform", ""),
                        prob.get("language", ""),
                        imp_str,
                        display_date,
                        prob.get("tags", ""),
                    ),
                )
            self.cat_table_status_lbl.configure(
                text=f"{prob_count} {'problem' if prob_count == 1 else 'problems'}"
            )

    def _on_home_cat_selected(self) -> None:
        """Handle selection or click on a category in the Home category breakdown table."""
        sel = self.cats_tree.selection()
        if not sel:
            return
        item = self.cats_tree.item(sel[0])
        vals = item.get("values", [])
        if vals:
            cat_name = str(vals[0]).strip()
            if cat_name:
                self._show_category_view(cat_name)

    def _on_add_problem_in_category(self) -> None:
        """Open Add Problem dialog with current category pre-selected."""
        repo_path = self.selected_path_var.get().strip()
        is_valid, msg = backend.validate_repository(repo_path)
        if not is_valid:
            messagebox.showerror(
                "Repository Required",
                f"Cannot add problem: A valid repository must be configured first.\n\nReason: {msg}",
            )
            self._show_view("repo")
            return

        current_cat = getattr(self, "current_category_name", "")
        AddProblemDialog(
            parent=self.root,
            repo_path=repo_path,
            initial_category=current_cat,
            on_success_callback=self._on_problem_created,
        )

    def _on_open_selected_category_problem(self) -> None:
        """Prompt confirmation dialog to open the selected problem from category view."""
        sel = self.cat_problems_tree.selection()
        if not sel:
            messagebox.showinfo("Selection Required", "Please select a problem from the list to open.", parent=self.root)
            return

        idx = int(sel[0])
        cache = getattr(self, "_category_problems_cache", [])
        if 0 <= idx < len(cache):
            problem_data = cache[idx]
            repo_path = self.selected_path_var.get().strip()
            OpenFileConfirmDialog(self.root, problem_data, repo_path)

    def _refresh_home_dashboard(self) -> None:
        """Fetch dashboard statistics from backend and update all Home UI components."""
        repo_path = self.selected_path_var.get().strip()
        stats = backend.get_dashboard_stats(repo_path)

        tot = stats.get("total_problems", 0)
        this_week = stats.get("this_week", 0)
        this_month = stats.get("this_month", 0)
        cur_streak = stats.get("current_streak", 0)
        long_streak = stats.get("longest_streak", 0)

        self.stat_total_var.set(str(tot))
        self.stat_week_var.set(str(this_week))
        self.stat_month_var.set(str(this_month))
        self.stat_streak_var.set(f"{cur_streak} {'day' if cur_streak == 1 else 'days'}")
        self.stat_longest_streak_var.set(f"Best: {long_streak} {'day' if long_streak == 1 else 'days'}")

        # Update repo badge in sidebar
        if repo_path and Path(repo_path).is_dir():
            folder_name = Path(repo_path).name
            self._sidebar_repo_var.set(f"📂 {folder_name}")
        else:
            self._sidebar_repo_var.set("📂 (No Repo)")

        if tot == 0:
            self.home_empty_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
            self.home_data_frame.pack_forget()
        else:
            self.home_empty_frame.pack_forget()
            self.home_data_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

            # Populate Categories
            self._populate_home_categories(stats)

            # Populate Recent Problems
            self._populate_home_recent_problems(stats)

            # Render Activity Heatmap
            self._render_activity_heatmap(stats)

    def _populate_home_categories(self, stats: Dict[str, Any]) -> None:
        """Populate Most Practiced, Less Practiced, and all Category breakdowns."""
        # 1. Most Practiced
        for child in self.most_practiced_container.winfo_children():
            child.destroy()

        most = stats.get("most_practiced_categories", [])
        if most:
            for cat, count in most:
                row = tk.Frame(self.most_practiced_container, bg="#F8FAFC", cursor="hand2")
                row.pack(fill=tk.X, pady=1)
                lbl_name = tk.Label(row, text=cat, font=("Segoe UI", 9), fg="#0F172A", bg="#F8FAFC", cursor="hand2")
                lbl_name.pack(side=tk.LEFT)
                lbl_cnt = tk.Label(row, text=f"{count}", font=("Segoe UI", 8, "bold"), fg="#1E3A5F", bg="#E2E8F0", padx=5, pady=1, cursor="hand2")
                lbl_cnt.pack(side=tk.RIGHT)

                # Make entire row clickable to open Category View
                row.bind("<Button-1>", lambda e, c=cat: self._show_category_view(c))
                lbl_name.bind("<Button-1>", lambda e, c=cat: self._show_category_view(c))
                lbl_cnt.bind("<Button-1>", lambda e, c=cat: self._show_category_view(c))
        else:
            tk.Label(self.most_practiced_container, text="None recorded", font=("Segoe UI", 8, "italic"), fg="#94A3B8", bg="#F8FAFC").pack(anchor="w")

        # 2. Less Practiced
        for child in self.least_practiced_container.winfo_children():
            child.destroy()

        least = stats.get("least_practiced_categories", [])
        if least:
            for cat, count in least:
                row = tk.Frame(self.least_practiced_container, bg="#F8FAFC", cursor="hand2")
                row.pack(fill=tk.X, pady=1)
                lbl_name = tk.Label(row, text=cat, font=("Segoe UI", 9), fg="#0F172A", bg="#F8FAFC", cursor="hand2")
                lbl_name.pack(side=tk.LEFT)
                lbl_cnt = tk.Label(row, text=f"{count}", font=("Segoe UI", 8, "bold"), fg="#64748B", bg="#E2E8F0", padx=5, pady=1, cursor="hand2")
                lbl_cnt.pack(side=tk.RIGHT)

                # Make entire row clickable to open Category View
                row.bind("<Button-1>", lambda e, c=cat: self._show_category_view(c))
                lbl_name.bind("<Button-1>", lambda e, c=cat: self._show_category_view(c))
                lbl_cnt.bind("<Button-1>", lambda e, c=cat: self._show_category_view(c))
        else:
            tk.Label(self.least_practiced_container, text="None recorded", font=("Segoe UI", 8, "italic"), fg="#94A3B8", bg="#F8FAFC").pack(anchor="w")

        # 3. All Categories Tree
        self.cats_tree.delete(*self.cats_tree.get_children())
        counts_dict = stats.get("category_counts", {})
        sorted_cats = sorted(counts_dict.items(), key=lambda x: (-x[1], x[0].lower()))
        for cat, count in sorted_cats:
            self.cats_tree.insert("", tk.END, values=(cat, count))

    def _populate_home_recent_problems(self, stats: Dict[str, Any]) -> None:
        """Populate Recent Problems treeview."""
        self.recent_tree.delete(*self.recent_tree.get_children())
        recent = stats.get("recent_problems", [])
        for prob in recent:
            self.recent_tree.insert(
                "",
                tk.END,
                values=(
                    prob.get("title", ""),
                    prob.get("category", ""),
                    prob.get("platform", ""),
                    prob.get("formatted_date", "") or prob.get("added_date", ""),
                ),
            )

    def _render_activity_heatmap(self, stats: Dict[str, Any]) -> None:
        """
        Draw 12-week activity grid on the heatmap canvas with month headers and day labels.
        """
        self.heatmap_canvas.delete("all")
        weeks = stats.get("heatmap_weeks", [])
        self._cached_heatmap_weeks = weeks

        if not weeks:
            return

        cell_size = 14
        spacing = 4
        start_x = 42
        start_y = 22

        # 1. Month Labels on top of columns
        last_month = None
        for w_idx, week in enumerate(weeks):
            if not week:
                continue
            first_day_month = week[0].get("month_name", "")
            if first_day_month != last_month:
                x = start_x + w_idx * (cell_size + spacing)
                self.heatmap_canvas.create_text(
                    x,
                    10,
                    text=first_day_month,
                    font=("Segoe UI", 7, "bold"),
                    fill="#64748B",
                    anchor="w",
                )
                last_month = first_day_month

        # 2. Day labels on left
        day_labels = [("Mon", 0), ("Wed", 2), ("Fri", 4), ("Sun", 6)]
        for label, r in day_labels:
            y = start_y + r * (cell_size + spacing) + cell_size // 2
            self.heatmap_canvas.create_text(
                20,
                y,
                text=label,
                font=("Segoe UI", 7),
                fill="#64748B",
                anchor="center",
            )

        # 3. Color map for exact levels (0=empty, 1=level1, 2=level2, 3+=level3)
        level_colors = {
            0: "#E2E8F0",
            1: "#93C5FD",
            2: "#3B82F6",
            3: "#1D4ED8",
        }

        # 4. Draw cells
        for w_idx, week in enumerate(weeks):
            x = start_x + w_idx * (cell_size + spacing)
            for d_idx, day_cell in enumerate(week):
                y = start_y + d_idx * (cell_size + spacing)
                level = day_cell.get("level", 0)
                color = level_colors.get(level, "#E2E8F0")

                outline = "#0F172A" if day_cell.get("is_today") else "#CBD5E1"
                width = 2 if day_cell.get("is_today") else 1

                tag = f"cell_{w_idx}_{d_idx}"
                self.heatmap_canvas.create_rectangle(
                    x,
                    y,
                    x + cell_size,
                    y + cell_size,
                    fill=color,
                    outline=outline,
                    width=width,
                    tags=(tag, "cell"),
                )

    def _on_heatmap_hover(self, event: tk.Event) -> None:
        """Update hover status text when mouse moves over a heatmap cell."""
        if not self._cached_heatmap_weeks:
            return

        cell_size = 14
        spacing = 4
        start_x = 42
        start_y = 22

        rel_x = event.x - start_x
        rel_y = event.y - start_y

        if rel_x < 0 or rel_y < 0:
            self.heatmap_hover_var.set("Hover over any square to inspect activity.")
            return

        w_idx = rel_x // (cell_size + spacing)
        d_idx = rel_y // (cell_size + spacing)

        if 0 <= w_idx < len(self._cached_heatmap_weeks):
            week = self._cached_heatmap_weeks[w_idx]
            if 0 <= d_idx < len(week):
                cell = week[d_idx]
                cnt = cell.get("count", 0)
                d_str = cell.get("formatted_date") or cell.get("date", "")
                suffix = "problem" if cnt == 1 else "problems"
                today_tag = " (Today)" if cell.get("is_today") else ""
                self.heatmap_hover_var.set(f"{d_str}{today_tag} — {cnt} {suffix}")
                return

        self.heatmap_hover_var.set("Hover over any square to inspect activity.")

    # ──────────────────────────────────────────────────────────────────────────
    # SEARCH VIEW LOGIC (PHASE 6)
    # ──────────────────────────────────────────────────────────────────────────

    def _refresh_search_view(self) -> None:
        """Refresh search filter options dynamically from normalized repository records and execute search."""
        repo_path = self.selected_path_var.get().strip()

        # Perform scan query to retrieve dynamic filter options from repo
        search_res = backend.search_problems(repo_path, query="")
        opts = search_res.get("filter_options", {})

        # Dynamic Category filter dropdown values
        categories = ["All Categories"] + opts.get("categories", backend.get_categories())
        self.search_cat_combo["values"] = categories
        if self.search_category_var.get() not in categories:
            self.search_category_var.set("All Categories")

        # Dynamic Platform filter dropdown values
        platforms = ["All Platforms"] + opts.get("platforms", backend.get_all_platforms())
        self.search_plat_combo["values"] = platforms
        if self.search_platform_var.get() not in platforms:
            self.search_platform_var.set("All Platforms")

        # Dynamic Language filter dropdown values
        languages = ["All Languages"] + opts.get("languages", ["C++", "Java", "Python"])
        self.search_lang_combo["values"] = languages
        if self.search_language_var.get() not in languages:
            self.search_language_var.set("All Languages")

        self._execute_search()

    def _on_search_query_changed(self) -> None:
        """Callback on search entry typing or filter dropdown selection."""
        self._execute_search()

    def _on_search_clear(self) -> None:
        """Clear the search query entry while preserving active dropdown filters."""
        self.search_query_var.set("")
        self._execute_search()

    def _on_search_reset_filters(self) -> None:
        """Reset all search filters to default and clear query."""
        self.search_query_var.set("")
        self.search_category_var.set("All Categories")
        self.search_platform_var.set("All Platforms")
        self.search_language_var.set("All Languages")
        self.search_importance_var.set("All")
        self._execute_search()

    def _execute_search(self) -> None:
        """Execute search using backend.search_problems and update UI."""
        repo_path = self.selected_path_var.get().strip()
        query = self.search_query_var.get()

        cat_filter = self.search_category_var.get()
        if cat_filter == "All Categories":
            cat_filter = ""

        plat_filter = self.search_platform_var.get()
        if plat_filter == "All Platforms":
            plat_filter = ""

        lang_filter = self.search_language_var.get()
        if lang_filter == "All Languages":
            lang_filter = ""

        imp_filter = self.search_importance_var.get()
        if imp_filter == "All":
            imp_filter = ""

        search_res = backend.search_problems(
            repo_path=repo_path,
            query=query,
            category=cat_filter,
            platform=plat_filter,
            language=lang_filter,
            importance=imp_filter,
        )

        results = search_res.get("results", [])
        total_matching = search_res.get("total_matching", len(results))
        total_repo = search_res.get("total_repository", total_matching)
        self._search_results_cache = results

        # 1. Update Category Browser listbox
        self.search_cat_tree.delete(*self.search_cat_tree.get_children())
        self.search_cat_tree.insert("", tk.END, iid="all", values=("All", total_matching))

        cat_counts = search_res.get("category_counts", {})
        sorted_cats = sorted(cat_counts.items(), key=lambda x: (-x[1], x[0].lower()))
        for cat, count in sorted_cats:
            self.search_cat_tree.insert("", tk.END, iid=cat, values=(cat, count))

        # 2. Update Search Results Tree
        self.search_results_tree.delete(*self.search_results_tree.get_children())
        for idx, item in enumerate(results):
            raw_imp = item.get("importance", "")
            imp_str = f"★ {raw_imp}" if raw_imp else "-"
            self.search_results_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(
                    item.get("title", ""),
                    item.get("category", ""),
                    item.get("platform", ""),
                    item.get("language", ""),
                    imp_str,
                    item.get("added_date", ""),
                    item.get("rel_path", ""),
                ),
            )

        # 3. Update status text
        if total_matching == 0:
            if query or cat_filter or plat_filter or lang_filter or imp_filter:
                self.search_status_var.set("No matching problems found.")
            else:
                self.search_status_var.set("No problems found in repository.")
        else:
            self.search_status_var.set(f"Showing {total_matching} of {total_repo} problems")

    def _on_category_browser_selected(self, event: tk.Event) -> None:
        """Handle selection in the category browser on the left."""
        sel = self.search_cat_tree.selection()
        if not sel:
            return
        cat_id = sel[0]
        if cat_id == "all":
            self.search_category_var.set("All Categories")
        else:
            self.search_category_var.set(cat_id)
        self._execute_search()

    def _on_open_selected_problem(self) -> None:
        """Prompt confirmation dialog to open the selected problem file."""
        sel = self.search_results_tree.selection()
        if not sel:
            messagebox.showinfo("Selection Required", "Please select a problem from the list to open.", parent=self.root)
            return

        idx = int(sel[0])
        if 0 <= idx < len(self._search_results_cache):
            problem_data = self._search_results_cache[idx]
            repo_path = self.selected_path_var.get().strip()
            OpenFileConfirmDialog(self.root, problem_data, repo_path)

    # ──────────────────────────────────────────────────────────────────────────
    # INITIAL STATE & REPOSITORY CONFIGURATION
    # ──────────────────────────────────────────────────────────────────────────

    def _load_initial_state(self) -> None:
        """Load configuration from backend on startup and run verification."""
        config, error_msg = backend.load_config()

        if error_msg:
            self._set_status(f"✗ Configuration Error: {error_msg}", is_error=True)
            self._show_feedback(f"Error loading project.json:\n{error_msg}\n\nPlease check the file manually.")
            self.save_btn.configure(state=tk.DISABLED)
            self.browse_btn.configure(state=tk.DISABLED)
            self._show_view("repo")
            return

        cfg_dict = config or {}
        repo_path = (cfg_dict.get("repository") or cfg_dict.get("repository_path", "")).strip()
        self.selected_path_var.set(repo_path)

        git_cfg = cfg_dict.get("git", {})
        remote_url = ""
        if isinstance(git_cfg, dict):
            remote_url = git_cfg.get("remote_url", "").strip()
        self.remote_url_var.set(remote_url)

        if not repo_path:
            self.section_label.configure(text="Welcome — Setup Repository")
            self._set_status("No repository configured.", is_error=False, neutral=True)
            self._show_feedback("Welcome! Configure your DSA repository folder to get started.")
            self.browse_btn.configure(text="Select Folder")
            self._show_view("repo")
        else:
            self.section_label.configure(text="Repository Overview")
            self.browse_btn.configure(text="Change Repository")

            # Run full verification
            verif = backend.verify_git_configuration(repo_path, remote_url)
            self._update_git_panel_info(verif)

            if verif["success"]:
                self._set_status("✓ Git repository found", is_success=True)
                self._show_feedback(f"Loaded existing configuration successfully.\n\n{verif['message']}")
            else:
                is_val, val_msg = backend.validate_repository(repo_path)
                if is_val:
                    self._set_status("⚠ Configured directory is not inside a Git repository", neutral=True)
                    self._show_feedback(f"Local path exists, but Git verification reported:\n{verif['message']}")
                else:
                    self._set_status(f"✗ Repository not found ({val_msg})", is_error=True)
                    self._show_feedback(f"Warning: Configured repository cannot be reached:\n{val_msg}\n\nPlease update the repository location.")

            # Home is the primary first screen on startup
            self._show_view("home")

    def _update_git_panel_info(self, verif: dict) -> None:
        """Update git panel labels from a verification report dictionary."""
        if verif.get("git_available"):
            avail_txt = "✓ Git available"
            self.git_avail_label.configure(fg="#16A34A")
        else:
            avail_txt = "✗ Git unavailable"
            self.git_avail_label.configure(fg="#DC2626")

        if verif.get("is_repo") and verif.get("repo_root"):
            root_txt = f"Git Root: {verif['repo_root']}"
            self._git_avail_var.set(f"{avail_txt} — Git repository verified")
        else:
            root_txt = "Git Root: Not inside a Git repository"
            if verif.get("git_available"):
                self._git_avail_var.set(f"{avail_txt} — Not inside a Git repository")
                self.git_avail_label.configure(fg="#D97706")

        self._git_root_display_var.set(root_txt)

        if verif.get("remote_url"):
            self._git_remote_display_var.set(f"Remote: {verif.get('remote_name', 'origin')} → {verif['remote_url']}")
        else:
            self._git_remote_display_var.set("Remote: (None configured)")

    def _on_browse(self) -> None:
        """Open a directory chooser dialog."""
        initial_dir = self.selected_path_var.get()
        if not initial_dir or not Path(initial_dir).is_dir():
            initial_dir = str(PROJECT_ROOT)

        chosen = filedialog.askdirectory(
            parent=self.root,
            title="Select DSA Repository Directory",
            initialdir=initial_dir,
        )
        if chosen:
            resolved_chosen = str(Path(chosen).resolve())
            self.selected_path_var.set(resolved_chosen)
            is_valid, msg = backend.validate_repository(resolved_chosen)
            if is_valid:
                self._set_status("Folder selected (pending save)", neutral=True)
                self._show_feedback(f"Folder selected:\n{resolved_chosen}\n\nClick 'Save & Verify Git Configuration' to write and verify.")
            else:
                self._set_status(f"✗ Invalid folder: {msg}", is_error=True)
                self._show_feedback(f"Error: {msg}")

    def _on_save(self) -> None:
        """Save and verify Git configuration per Phase 2 requirements."""
        path_to_save = self.selected_path_var.get().strip()
        remote_to_save = self.remote_url_var.get().strip()

        if not path_to_save:
            self._set_status("✗ No folder selected.", is_error=True)
            self._show_feedback("Please select or enter a repository path before saving.")
            return

        # 1. Save config to project.json
        success, message = backend.save_repository_config(path_to_save, remote_to_save)
        if not success:
            self._set_status("✗ Configuration failed", is_error=True)
            self._show_feedback(f"Configuration failed:\n{message}")
            messagebox.showerror("Error", f"Failed to save configuration:\n{message}")
            return

        # 2. Run verification
        verif = backend.verify_git_configuration(path_to_save, remote_to_save)
        self.browse_btn.configure(text="Change Repository")
        self.section_label.configure(text="Repository Overview")
        self._update_git_panel_info(verif)

        if verif["success"]:
            self._set_status("✓ Git configuration verified", is_success=True)
            self._show_feedback(verif["message"])
            self._git_log_write(f"[INFO] Configuration verified:\n{verif['message']}\n")
            messagebox.showinfo("Configuration Saved", "Git configuration saved and verified successfully!\n\n" + verif["message"])
            self._refresh_home_dashboard()
        else:
            err_msg = verif["message"]
            if "not inside a Git repository" in err_msg:
                self._set_status("⚠ Not a Git repository", is_error=False, neutral=True)
            else:
                self._set_status("✗ Git verification failed", is_error=True)
            self._show_feedback(f"Configuration saved to project.json, but Git verification reported:\n\n{err_msg}")
            self._git_log_write(f"[WARN] Git verification notice:\n{err_msg}\n")
            messagebox.showwarning("Git Verification Notice", err_msg)

    def _on_add_problem(self) -> None:
        """Open Add Problem dialog after verifying repository configuration."""
        repo_path = self.selected_path_var.get().strip()
        is_valid, msg = backend.validate_repository(repo_path)
        if not is_valid:
            messagebox.showerror(
                "Repository Required",
                f"Cannot add problem: A valid repository must be configured first.\n\nReason: {msg}",
            )
            self._show_view("repo")
            return

        AddProblemDialog(
            parent=self.root,
            repo_path=repo_path,
            on_success_callback=self._on_problem_created,
        )

    def _on_rescan_repository(self) -> None:
        """Scan the configured repository for existing problems and open rescan dialog."""
        repo_path = self.selected_path_var.get().strip()
        is_valid, msg = backend.validate_repository(repo_path)
        if not is_valid:
            messagebox.showerror(
                "Repository Required",
                f"Cannot rescan repository: A valid repository must be configured first.\n\nReason: {msg}",
                parent=self.root,
            )
            self._show_view("repo")
            return

        scan_result = backend.scan_repository(repo_path)
        if not scan_result.get("success"):
            messagebox.showerror(
                "Rescan Error",
                f"Failed to scan repository:\n{scan_result.get('error')}",
                parent=self.root,
            )
            return

        dlg = RescanDialog(
            parent=self.root,
            repo_path=repo_path,
            initial_scan=scan_result,
        )
        def _on_rescan_closed(e):
            if e.widget == dlg:
                self._refresh_home_dashboard()
                if getattr(self, "_current_view", "") == "category":
                    self._refresh_category_view()

        dlg.bind("<Destroy>", _on_rescan_closed)

    def _on_problem_created(self, file_path: Path, title: str, category: str) -> None:
        """Callback executed when a problem is created and physically verified."""
        feedback = (
            "✓ Problem created successfully!\n\n"
            f"Title: {title}\n"
            f"Category: {category}\n"
            f"File: {file_path}\n"
            "Physical file verified on disk."
        )
        self._show_feedback(feedback)

        # Update git panel state
        self._git_last_file = Path(file_path)
        self._git_file_staged = False
        self._git_file_committed = False
        self._git_file_var.set(str(file_path))
        self._commit_msg_var.set(f"Add {title} solution")
        self.git_stage_btn.configure(state=tk.NORMAL)
        self._git_log_write(f"[INFO] Problem file created: {file_path}\n")
        self._on_refresh_git_status()

        # Refresh Home Dashboard & Category view
        self._refresh_home_dashboard()
        if getattr(self, "_current_view", "") == "category":
            self._refresh_category_view()

    def _set_status(self, text: str, is_error: bool = False, is_success: bool = False, neutral: bool = False) -> None:
        self.status_var.set(text)
        if is_error:
            self.status_display.configure(fg="#DC2626")
        elif is_success:
            self.status_display.configure(fg="#16A34A")
        elif neutral:
            self.status_display.configure(fg="#D97706")
        else:
            self.status_display.configure(fg="#2563EB")

    def _show_feedback(self, text: str) -> None:
        self.feedback_box.configure(text=text)

    # ──────────────────────────────────────────────────────────────────────────
    # Phase 2 & 2.5: Git Integration event handlers & Reliability
    # ──────────────────────────────────────────────────────────────────────────

    def _set_git_busy(self, busy: bool) -> None:
        """Prevent duplicate operations by locking Git buttons while an action runs."""
        self._git_busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.git_refresh_btn.configure(state=state)
        self.git_commit_btn.configure(state=state)
        self.git_push_btn.configure(state=state)
        if busy or not self._git_last_file:
            self.git_stage_btn.configure(state=tk.DISABLED)
        else:
            self.git_stage_btn.configure(state=tk.NORMAL)
        self.root.update_idletasks()

    def _check_git_availability(self) -> None:
        """Check if git is installed and update the git availability label."""
        is_avail, msg = backend.is_git_available()
        if is_avail:
            self._git_avail_var.set(f"✓ Git available — {msg}")
            self.git_avail_label.configure(fg="#16A34A")
        else:
            self._git_avail_var.set(f"✗ {msg}")
            self.git_avail_label.configure(fg="#DC2626")

    def _on_refresh_git_status(self) -> None:
        """Refresh the git status for the configured repository."""
        if self._git_busy:
            return

        repo_path = self.selected_path_var.get().strip()
        if not repo_path:
            self._git_log_write("[WARN] No repository configured — cannot refresh git status.\n")
            return

        is_avail, avail_msg = backend.is_git_available()
        if not is_avail:
            self._git_log_write(f"[ERROR] {avail_msg}\n")
            return

        is_repo, repo_msg, root = backend.get_git_repo_root(repo_path)
        if not is_repo or not root:
            self._git_log_write(f"[WARN] Not a git repository: {repo_msg}\n")
            return

        self._set_git_busy(True)
        try:
            success, msg, status_output = backend.get_git_status(repo_path)
            if success:
                if status_output:
                    self._git_log_write(f"[STATUS]\n{status_output}\n")
                else:
                    self._git_log_write("[STATUS] Working tree is clean.\n")
            else:
                self._git_log_write(f"[ERROR] {msg}\n")
        finally:
            self._set_git_busy(False)

    def _on_stage_file(self) -> None:
        """Stage the last-created problem file via git add (single-file only)."""
        if self._git_busy:
            return

        if not self._git_last_file:
            messagebox.showwarning("No File", "No problem file has been created yet in this session.", parent=self.root)
            return

        repo_path = self.selected_path_var.get().strip()
        if not repo_path:
            messagebox.showerror("No Repository", "No repository is configured.", parent=self.root)
            return

        is_repo, repo_msg, root = backend.get_git_repo_root(repo_path)
        if not is_repo or not root:
            self._git_log_write(f"[ERROR] Cannot stage — not a git repository: {repo_msg}\n")
            messagebox.showerror("Not a Git Repository", repo_msg, parent=self.root)
            return

        self._set_git_busy(True)
        try:
            success, msg = backend.git_add_file(repo_path, self._git_last_file)
            if success:
                self._git_file_staged = True
                self._git_file_committed = False
                self._git_log_write(f"[STAGED] {msg}\n")
                s_ok, _, status_out = backend.get_git_status(repo_path)
                if s_ok and status_out:
                    self._git_log_write(f"[STATUS]\n{status_out}\n")
                messagebox.showinfo("Staged", f"✓ Staged successfully:\n{self._git_last_file.name}", parent=self.root)
            else:
                self._git_log_write(f"[ERROR] {msg}\n")
                messagebox.showerror("Stage Failed", msg, parent=self.root)
        finally:
            self._set_git_busy(False)

    def _on_commit(self) -> None:
        """Commit staged changes with the user-supplied message."""
        if self._git_busy:
            return

        commit_msg = self._commit_msg_var.get().strip()
        if not commit_msg:
            messagebox.showwarning(
                "Commit Message Required",
                "Please enter a commit message before committing.",
                parent=self.root,
            )
            return

        repo_path = self.selected_path_var.get().strip()
        if not repo_path:
            messagebox.showerror("No Repository", "No repository is configured.", parent=self.root)
            return

        is_repo, repo_msg, root = backend.get_git_repo_root(repo_path)
        if not is_repo or not root:
            self._git_log_write(f"[ERROR] Cannot commit — not a git repository: {repo_msg}\n")
            messagebox.showerror("Not a Git Repository", repo_msg, parent=self.root)
            return

        self._set_git_busy(True)
        try:
            success, msg = backend.git_commit(repo_path, commit_msg)
            if success:
                self._git_file_committed = True
                self._git_log_write(f"[COMMIT] {msg}\n")
                self._commit_msg_var.set("")
                s_ok, _, status_out = backend.get_git_status(repo_path)
                if s_ok:
                    self._git_log_write(f"[STATUS]\n{status_out if status_out else 'Working tree is clean.'}\n")
                messagebox.showinfo("Commit Successful", f"✓ Commit successful.\n\n{msg}", parent=self.root)
            else:
                self._git_log_write(f"[ERROR] {msg}\n")
                if "Nothing staged to commit" in msg:
                    messagebox.showinfo("Nothing Staged", "Nothing staged to commit.\nPlease click 'Stage File' first.", parent=self.root)
                else:
                    messagebox.showerror("Commit Failed", msg, parent=self.root)
        finally:
            self._set_git_busy(False)

    def _on_push(self) -> None:
        """Push committed changes to the configured remote."""
        if self._git_busy:
            return

        if self._git_last_file and not self._git_file_committed:
            warn = "Cannot push: Please commit the newly created problem before pushing to remote."
            self._git_log_write(f"[WARN] {warn}\n")
            messagebox.showwarning("Commit Required", warn, parent=self.root)
            return

        repo_path = self.selected_path_var.get().strip()
        if not repo_path:
            messagebox.showerror("No Repository", "No repository is configured.", parent=self.root)
            return

        is_repo, repo_msg, root = backend.get_git_repo_root(repo_path)
        if not is_repo or not root:
            self._git_log_write(f"[ERROR] Cannot push — not a git repository: {repo_msg}\n")
            messagebox.showerror("Not a Git Repository", repo_msg, parent=self.root)
            return

        remotes_ok, _, remotes = backend.get_git_remotes(root)
        if not remotes_ok or not remotes:
            err = "Cannot push: no Git remote is configured."
            self._git_log_write(f"[ERROR] {err}\n")
            messagebox.showerror("Push Error", err, parent=self.root)
            return

        self._git_log_write("[PUSH] Running git push...\n")
        self._set_git_busy(True)
        try:
            success, msg = backend.git_push(repo_path)
            if success:
                self._git_log_write(f"[PUSH] {msg}\n")
                messagebox.showinfo("Push Successful", msg, parent=self.root)
            else:
                self._git_log_write(f"[ERROR] {msg}\n")
                messagebox.showerror("Push Failed", msg, parent=self.root)
        finally:
            self._set_git_busy(False)

    def _git_log_write(self, text: str) -> None:
        """Append a line to the dark git activity log (read-only terminal area)."""
        self.git_log.configure(state=tk.NORMAL)
        self.git_log.insert(tk.END, text)
        self.git_log.see(tk.END)
        self.git_log.configure(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    app = DSAOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()


