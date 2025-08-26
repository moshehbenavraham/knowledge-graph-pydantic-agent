#!/usr/bin/env python3
"""
Script to clean problematic characters from documentation files.
Removes null bytes, control characters, and other non-printable characters.
"""

import os
import sys
from pathlib import Path


def clean_file(filepath):
    """Clean problematic characters from a file."""
    with open(filepath, 'rb') as f:
        content = f.read()
    
    original_size = len(content)
    
    # Remove null bytes
    content = content.replace(b'\x00', b'')
    
    # Remove other control characters (except tab, newline, carriage return)
    cleaned = bytearray()
    for byte in content:
        if byte >= 0x20 or byte in (0x09, 0x0A, 0x0D):  # Printable or allowed whitespace
            cleaned.append(byte)
        elif byte in (0x1c, 0x02, 0x14):  # Skip these control chars
            continue
        else:
            # Replace other control chars with space
            cleaned.append(0x20)
    
    if len(cleaned) != original_size:
        print(f"Cleaned {filepath}: removed {original_size - len(cleaned)} problematic bytes")
        with open(filepath, 'wb') as f:
            f.write(cleaned)
        return True
    return False


def main():
    """Clean all documentation files in the project."""
    project_root = Path(__file__).parent.parent
    extensions = {'.md', '.txt', '.rst'}
    
    cleaned_count = 0
    for ext in extensions:
        for filepath in project_root.rglob(f'*{ext}'):
            if clean_file(filepath):
                cleaned_count += 1
    
    if cleaned_count:
        print(f"\nCleaned {cleaned_count} files")
    else:
        print("All files are clean!")
    
    return 0 if cleaned_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())