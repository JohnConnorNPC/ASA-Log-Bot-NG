#!/usr/bin/env python3
"""Tool to manage replacement words for OCR correction"""

import json
import sys
import os

def load_replacements(filename='replacements.json'):
    """Load existing replacements"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {
        "replacements": {},
        "special_formatting": {
            "word_spacing": [],
            "clean_endings": {
                "remove_quotes": True,
                "fix_parentheses": True
            }
        }
    }

def save_replacements(data, filename='replacements.json'):
    """Save replacements to file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved replacements to {filename}")

def add_replacement(data, old, new):
    """Add a replacement rule"""
    data['replacements'][old] = new
    print(f"Added: '{old}' -> '{new}'")

def remove_replacement(data, old):
    """Remove a replacement rule"""
    if old in data['replacements']:
        del data['replacements'][old]
        print(f"Removed: '{old}'")
    else:
        print(f"Not found: '{old}'")

def list_replacements(data):
    """List all replacements"""
    replacements = data.get('replacements', {})
    if not replacements:
        print("No replacements configured")
        return
    
    print(f"\nConfigured replacements ({len(replacements)} total):")
    print("-" * 50)
    
    # Sort by old text for easier reading
    for old in sorted(replacements.keys()):
        new = replacements[old]
        print(f"'{old}' -> '{new}'")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_replacements.py list")
        print("  python manage_replacements.py add 'old text' 'new text'")
        print("  python manage_replacements.py remove 'old text'")
        print("  python manage_replacements.py test 'sample text'")
        return
    
    command = sys.argv[1].lower()
    data = load_replacements()
    
    if command == 'list':
        list_replacements(data)
    
    elif command == 'add':
        if len(sys.argv) != 4:
            print("Usage: python manage_replacements.py add 'old text' 'new text'")
            return
        old_text = sys.argv[2]
        new_text = sys.argv[3]
        add_replacement(data, old_text, new_text)
        save_replacements(data)
    
    elif command == 'remove':
        if len(sys.argv) != 3:
            print("Usage: python manage_replacements.py remove 'old text'")
            return
        old_text = sys.argv[2]
        remove_replacement(data, old_text)
        save_replacements(data)
    
    elif command == 'test':
        if len(sys.argv) != 3:
            print("Usage: python manage_replacements.py test 'sample text'")
            return
        
        test_text = sys.argv[2]
        print(f"Original: {test_text}")
        
        # Apply replacements
        result = test_text
        for old, new in data['replacements'].items():
            result = result.replace(old, new)
        
        print(f"Result:   {result}")
        
        # Show which replacements were applied
        applied = []
        for old, new in data['replacements'].items():
            if old in test_text:
                applied.append(f"'{old}' -> '{new}'")
        
        if applied:
            print("\nApplied replacements:")
            for repl in applied:
                print(f"  {repl}")
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'list', 'add', 'remove', or 'test'")

if __name__ == "__main__":
    main()