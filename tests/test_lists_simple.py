#!/usr/bin/env python3
"""
Simple test for list commands
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import mystuff
sys.path.insert(0, str(Path(__file__).parent.parent))

from mystuff.commands.lists import (
    create_or_update_list,
    find_list_by_name,
    get_all_lists,
    delete_list_file,
    add_item_to_list,
    remove_item_from_list,
    check_item_in_list,
    search_lists_by_text,
    export_list_to_csv,
    export_list_to_yaml,
    import_list_from_csv,
    import_list_from_yaml,
    get_lists_dir,
    slugify,
)


def test_list_commands():
    """Test list commands functionality"""
    # Create a temporary mystuff directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set MYSTUFF_HOME to our temp directory
        old_mystuff_home = os.environ.get('MYSTUFF_HOME')
        os.environ['MYSTUFF_HOME'] = temp_dir
        
        try:
            print("Testing list commands...")
            
            # Test 1: Create list
            print("1. Creating list...")
            list_data = create_or_update_list("Books to Read")
            assert list_data['name'] == "Books to Read"
            assert list_data['items'] == []
            print("   ✓ Created list successfully")
            
            # Test 2: Find list
            print("2. Finding list...")
            found_list = find_list_by_name("Books to Read")
            assert found_list is not None
            assert found_list['name'] == "Books to Read"
            print("   ✓ Found list correctly")
            
            # Test 3: Add items to list
            print("3. Adding items to list...")
            add_item_to_list("Books to Read", "Clean Code by Robert C. Martin")
            add_item_to_list("Books to Read", "The Pragmatic Programmer")
            add_item_to_list("Books to Read", "Design Patterns")
            
            updated_list = find_list_by_name("Books to Read")
            assert len(updated_list['items']) == 3
            assert updated_list['items'][0]['text'] == "Clean Code by Robert C. Martin"
            assert updated_list['items'][0]['checked'] == False
            print("   ✓ Added items successfully")
            
            # Test 4: Check/uncheck items
            print("4. Checking/unchecking items...")
            check_item_in_list("Books to Read", "Clean Code by Robert C. Martin", True)
            
            updated_list = find_list_by_name("Books to Read")
            assert updated_list['items'][0]['checked'] == True
            print("   ✓ Checked item successfully")
            
            check_item_in_list("Books to Read", "Clean Code by Robert C. Martin", False)
            updated_list = find_list_by_name("Books to Read")
            assert updated_list['items'][0]['checked'] == False
            print("   ✓ Unchecked item successfully")
            
            # Test 5: Create another list
            print("5. Creating another list...")
            create_or_update_list("Movies to Watch")
            add_item_to_list("Movies to Watch", "The Matrix")
            add_item_to_list("Movies to Watch", "Inception")
            
            # Test 6: Get all lists
            print("6. Getting all lists...")
            all_lists = get_all_lists()
            assert len(all_lists) == 2
            list_names = [lst['name'] for lst in all_lists]
            assert "Books to Read" in list_names
            assert "Movies to Watch" in list_names
            print(f"   ✓ Found {len(all_lists)} lists")
            
            # Test 7: Search lists
            print("7. Searching lists...")
            search_results = search_lists_by_text(all_lists, "Books")
            assert len(search_results) == 1
            assert search_results[0]['name'] == "Books to Read"
            print("   ✓ Search by list name works")
            
            search_results = search_lists_by_text(all_lists, "Matrix")
            assert len(search_results) == 1
            assert search_results[0]['name'] == "Movies to Watch"
            print("   ✓ Search by item content works")
            
            # Test 8: Remove item
            print("8. Removing item...")
            remove_item_from_list("Books to Read", "Design Patterns")
            updated_list = find_list_by_name("Books to Read")
            assert len(updated_list['items']) == 2
            item_texts = [item['text'] for item in updated_list['items']]
            assert "Design Patterns" not in item_texts
            print("   ✓ Removed item successfully")
            
            # Test 9: Export to CSV
            print("9. Testing CSV export...")
            csv_file = Path(temp_dir) / "books.csv"
            export_list_to_csv(updated_list, csv_file)
            assert csv_file.exists()
            print("   ✓ CSV export successful")
            
            # Test 10: Export to YAML
            print("10. Testing YAML export...")
            yaml_file = Path(temp_dir) / "books.yaml"
            export_list_to_yaml(updated_list, yaml_file)
            assert yaml_file.exists()
            print("   ✓ YAML export successful")
            
            # Test 11: Import from CSV
            print("11. Testing CSV import...")
            import_list_from_csv("Books from CSV", csv_file)
            imported_list = find_list_by_name("Books from CSV")
            assert imported_list is not None
            assert len(imported_list['items']) == 2
            print("   ✓ CSV import successful")
            
            # Test 12: Import from YAML
            print("12. Testing YAML import...")
            import_list_from_yaml("Books from YAML", yaml_file)
            imported_list = find_list_by_name("Books from YAML")
            assert imported_list is not None
            assert len(imported_list['items']) == 2
            print("   ✓ YAML import successful")
            
            # Test 13: Delete list
            print("13. Deleting list...")
            success = delete_list_file("Movies to Watch")
            assert success
            remaining_lists = get_all_lists()
            list_names = [lst['name'] for lst in remaining_lists]
            assert "Movies to Watch" not in list_names
            print("   ✓ Deleted list successfully")
            
            # Test 14: Slugify function
            print("14. Testing slugify function...")
            assert slugify("Books to Read") == "books-to-read"
            assert slugify("My Special List!") == "my-special-list"
            assert slugify("Test with-dashes") == "test-with-dashes"
            print("   ✓ Slugify function works correctly")
            
            # Test 15: Check file structure
            print("15. Checking file structure...")
            lists_dir = get_lists_dir()
            assert lists_dir.exists()
            
            # Should have books-to-read.yaml and books-from-csv.yaml and books-from-yaml.yaml
            books_file = lists_dir / "books-to-read.yaml"
            csv_import_file = lists_dir / "books-from-csv.yaml"
            yaml_import_file = lists_dir / "books-from-yaml.yaml"
            assert books_file.exists()
            assert csv_import_file.exists()
            assert yaml_import_file.exists()
            print("   ✓ File structure is correct")
            
            print("✅ All list tests passed!")
            
        finally:
            # Restore original MYSTUFF_HOME
            if old_mystuff_home:
                os.environ['MYSTUFF_HOME'] = old_mystuff_home
            elif 'MYSTUFF_HOME' in os.environ:
                del os.environ['MYSTUFF_HOME']


if __name__ == "__main__":
    test_list_commands()
