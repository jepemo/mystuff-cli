#!/usr/bin/env python3
"""
Simple test for eval commands
"""
import os
import tempfile

from mystuff.commands.eval import (
    add_or_update_evaluation,
    filter_evaluations_by_date_range,
    find_evaluation_by_date_and_category,
    generate_report,
    get_all_evaluations,
    get_eval_dir,
    remove_evaluation,
    search_evaluations_by_text,
)


def test_eval_commands():
    """Test eval commands functionality"""
    # Create a temporary mystuff directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set MYSTUFF_HOME to our temp directory
        old_mystuff_home = os.environ.get("MYSTUFF_HOME")
        os.environ["MYSTUFF_HOME"] = temp_dir

        try:
            print("Testing eval commands...")

            # Test 1: Add evaluation
            print("1. Adding evaluation...")
            add_or_update_evaluation(
                "2023-10-05", "productivity", 8, "Very productive day"
            )
            add_or_update_evaluation("2023-10-05", "health", 7, "Went for a run")
            add_or_update_evaluation(
                "2023-10-06", "productivity", 6, "Good but could be better"
            )
            add_or_update_evaluation("2023-11-01", "productivity", 9, "Excellent focus")

            # Test 2: Find evaluation
            print("2. Finding evaluation...")
            eval_entry = find_evaluation_by_date_and_category(
                "2023-10-05", "productivity"
            )
            assert eval_entry is not None
            assert eval_entry["score"] == 8
            assert eval_entry["comments"] == "Very productive day"
            print("   ✓ Found evaluation correctly")

            # Test 3: Update evaluation
            print("3. Updating evaluation...")
            add_or_update_evaluation(
                "2023-10-05", "productivity", 9, "Actually, it was excellent"
            )
            updated_eval = find_evaluation_by_date_and_category(
                "2023-10-05", "productivity"
            )
            assert updated_eval["score"] == 9
            assert updated_eval["comments"] == "Actually, it was excellent"
            print("   ✓ Updated evaluation correctly")

            # Test 4: Get all evaluations
            print("4. Getting all evaluations...")
            all_evals = get_all_evaluations()
            assert len(all_evals) == 4
            print(f"   ✓ Found {len(all_evals)} evaluations")

            # Test 5: Filter by date range
            print("5. Filtering by date range...")
            october_evals = filter_evaluations_by_date_range(
                all_evals, "2023-10-01", "2023-10-31"
            )
            assert len(october_evals) == 3
            print(f"   ✓ Found {len(october_evals)} evaluations in October")

            # Test 6: Search by text
            print("6. Searching by text...")
            run_evals = search_evaluations_by_text(all_evals, "run")
            assert len(run_evals) == 1
            assert run_evals[0]["category"] == "health"
            print("   ✓ Found evaluations with 'run' in comments")

            # Test 7: Generate report
            print("7. Generating report...")
            report = generate_report(all_evals)
            assert "# Self-Evaluation Report" in report
            assert "Total evaluations:" in report
            assert "productivity" in report
            assert "health" in report
            print("   ✓ Generated report successfully")

            # Test 8: Remove evaluation
            print("8. Removing evaluation...")
            success = remove_evaluation("2023-10-05", "health")
            assert success
            remaining_evals = get_all_evaluations()
            assert len(remaining_evals) == 3
            print("   ✓ Removed evaluation successfully")

            # Test 9: Check file structure
            print("9. Checking file structure...")
            eval_dir = get_eval_dir()
            assert eval_dir.exists()

            # Should have 2023-10.yaml and 2023-11.yaml
            october_file = eval_dir / "2023-10.yaml"
            november_file = eval_dir / "2023-11.yaml"
            assert october_file.exists()
            assert november_file.exists()
            print("   ✓ File structure is correct")

            print("✅ All eval tests passed!")

        finally:
            # Restore original MYSTUFF_HOME
            if old_mystuff_home:
                os.environ["MYSTUFF_HOME"] = old_mystuff_home
            elif "MYSTUFF_HOME" in os.environ:
                del os.environ["MYSTUFF_HOME"]


if __name__ == "__main__":
    test_eval_commands()
