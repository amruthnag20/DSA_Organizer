"""
test_phase0.py - Automated test suite for Phase 0 requirements and acceptance criteria.
"""

import json
import shutil
import tempfile
from pathlib import Path

from engine import backend


def run_all_tests():
    print("==================================================")
    print("Running Phase 0 Test Suite")
    print("==================================================")
    results = {}

    # Test 5: Required folders (engine/ and DSA/)
    print("\n[Test 5] Checking required directories...")
    ok, msg = backend.ensure_project_directories()
    root = backend.get_project_root()
    engine_exists = (root / "engine").is_dir()
    dsa_exists = (root / "DSA").is_dir()
    if ok and engine_exists and dsa_exists:
        print(f" PASS: engine/ ({engine_exists}) and DSA/ ({dsa_exists}) verified physically.")
        results["Required directories"] = "PASS"
    else:
        print(f" FAIL: {msg}")
        results["Required directories"] = "FAIL"

    # Test 6: DSA directory cleanliness
    print("\n[Test 6] Checking DSA directory cleanliness...")
    dsa_dir = root / "DSA"
    items_in_dsa = list(dsa_dir.iterdir())
    forbidden_categories = {"Arrays", "Strings", "Hashing", "LinkedLists", "Stacks", "Queues", "Trees", "Graphs"}
    created_forbidden = [item.name for item in items_in_dsa if item.name in forbidden_categories]
    if len(created_forbidden) == 0:
        print(f" PASS: DSA/ contains no auto-generated category folders. Current count: {len(items_in_dsa)}")
        results["DSA directory cleanliness"] = "PASS"
    else:
        print(f" FAIL: Found forbidden category folders: {created_forbidden}")
        results["DSA directory cleanliness"] = "FAIL"

    # Use a temporary config path for isolated fresh-startup & persistence tests
    orig_config_path = backend.get_config_path()
    backup_config = None
    if orig_config_path.exists():
        backup_config = orig_config_path.read_text(encoding="utf-8")

    try:
        # Test 1: Fresh startup (no project.json exists)
        print("\n[Test 1] Testing fresh startup (no config)...")
        if orig_config_path.exists():
            orig_config_path.unlink()

        config, err = backend.load_config()
        if err is None and config is not None:
            # Check default fields
            if config.get("repository") == "" and config.get("default_language") == "cpp":
                # Check that project.json was created on disk
                if orig_config_path.exists():
                    print(" PASS: Fresh startup created safe default project.json with empty repository.")
                    results["Fresh startup"] = "PASS"
                else:
                    print(" FAIL: project.json not found on disk after load_config.")
                    results["Fresh startup"] = "FAIL"
            else:
                print(f" FAIL: Unexpected default config contents: {config}")
                results["Fresh startup"] = "FAIL"
        else:
            print(f" FAIL: load_config returned error: {err}")
            results["Fresh startup"] = "FAIL"

        # Test 2: Valid repository configuration & saving
        print("\n[Test 2] Testing valid repository configuration...")
        with tempfile.TemporaryDirectory() as temp_repo:
            temp_repo_path = Path(temp_repo).resolve()
            save_ok, save_msg = backend.save_repository_config(temp_repo_path)
            if save_ok:
                # Physically re-read project.json from disk
                with open(orig_config_path, "r", encoding="utf-8") as f:
                    saved_json = json.load(f)
                if saved_json.get("repository") == str(temp_repo_path):
                    print(f" PASS: Valid repository accepted, written to disk, and verified.")
                    results["Valid repository"] = "PASS"
                else:
                    print(f" FAIL: Saved JSON path mismatch: {saved_json.get('repository')} != {temp_repo_path}")
                    results["Valid repository"] = "FAIL"
            else:
                print(f" FAIL: save_repository_config failed: {save_msg}")
                results["Valid repository"] = "FAIL"

        # Test 3: Invalid path handling
        print("\n[Test 3] Testing invalid repository path...")
        invalid_path = Path("C:/DefinitelyNonExistentDirectory_XYZ123456789")
        is_valid, msg = backend.validate_repository(invalid_path)
        save_ok, save_msg = backend.save_repository_config(invalid_path)
        if not is_valid and not save_ok and "does not exist" in msg:
            print(f" PASS: Invalid path correctly rejected with clear message: '{msg}'")
            results["Invalid repository"] = "PASS"
        else:
            print(f" FAIL: Invalid path was not properly rejected. Valid={is_valid}, Save={save_ok}")
            results["Invalid repository"] = "FAIL"

        # Test 4: Restart persistence
        print("\n[Test 4] Testing restart persistence...")
        # Create a persistent test directory
        test_dir = root / "_test_repo_folder"
        test_dir.mkdir(exist_ok=True)
        try:
            resolved_test_dir = str(test_dir.resolve())
            save_ok, _ = backend.save_repository_config(resolved_test_dir)
            assert save_ok, "Initial save failed"

            # Simulate app restart: call load_config anew
            reloaded_config, reload_err = backend.load_config()
            is_valid, val_msg = backend.validate_repository(reloaded_config.get("repository"))

            if (
                reload_err is None
                and reloaded_config.get("repository") == resolved_test_dir
                and is_valid
            ):
                print(f" PASS: Configuration persisted across restart and verified: {resolved_test_dir}")
                results["Restart persistence"] = "PASS"
            else:
                print(f" FAIL: Failed persistence check. Reloaded: {reloaded_config}")
                results["Restart persistence"] = "FAIL"
        finally:
            if test_dir.exists():
                shutil.rmtree(test_dir, ignore_errors=True)

        # Test Malformed JSON Handling (Error Handling requirement)
        print("\n[Extra Test] Testing malformed project.json handling...")
        orig_config_path.write_text("{ this is not valid json :;;;", encoding="utf-8")
        malformed_cfg, malformed_err = backend.load_config()
        if malformed_cfg is None and malformed_err is not None:
            # Ensure save refuses to overwrite malformed config silently
            with tempfile.TemporaryDirectory() as valid_tmp:
                save_on_malformed_ok, save_on_malformed_msg = backend.save_repository_config(valid_tmp)
                if not save_on_malformed_ok and "malformed" in save_on_malformed_msg.lower():
                    print(" PASS: Malformed JSON handled cleanly, error reported, overwrite prevented.")
                    results["Malformed JSON handling"] = "PASS"
                else:
                    print(" FAIL: Saved over malformed config without proper refusal.")
                    results["Malformed JSON handling"] = "FAIL"
        else:
            print(" FAIL: load_config did not detect malformed JSON.")
            results["Malformed JSON handling"] = "FAIL"

    finally:
        # Restore initial state or clean up
        if backup_config is not None:
            orig_config_path.write_text(backup_config, encoding="utf-8")
        else:
            # Create a clean default project.json for actual user usage
            default_config = {
                "repository": "",
                "default_language": "cpp",
            }
            with open(orig_config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)

    print("\n==================================================")
    print("Test Results Summary:")
    all_passed = True
    for test_name, status in results.items():
        print(f"  - {test_name}: {status}")
        if status != "PASS":
            all_passed = False
    print("==================================================")
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
