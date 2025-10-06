#!/usr/bin/env python
"""
Compile .po files to .mo files manually since gettext tools are not available.
"""
import os
import struct
import re

def parse_po_file(po_file):
    """Parse a .po file and extract msgid/msgstr pairs."""
    translations = {}
    
    with open(po_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Use regex to find msgid/msgstr pairs
    pattern = r'msgid\s+"([^"]*)"\s*msgstr\s+"([^"]*)"'
    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
    
    for msgid, msgstr in matches:
        if msgid and msgstr:  # Skip empty strings
            translations[msgid] = msgstr
    
    return translations

def create_mo_file(translations, mo_file):
    """Create a binary .mo file from translations dictionary."""
    # Add empty string entry for metadata
    keys = [''] + sorted([k for k in translations.keys() if k])
    
    # Create metadata entry
    metadata = 'Content-Type: text/plain; charset=UTF-8\n'
    values = [metadata] + [translations.get(k, k) for k in keys[1:]]
    
    # Encode all strings
    kencoded = [k.encode('utf-8') for k in keys]
    vencoded = [v.encode('utf-8') for v in values]
    
    # Calculate offsets
    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart
    for k in kencoded:
        valuestart += len(k) + 1
    
    # Create offset tables
    koffsets = []
    voffsets = []
    
    offset = keystart
    for k in kencoded:
        koffsets.append((len(k), offset))
        offset += len(k) + 1
    
    offset = valuestart
    for v in vencoded:
        voffsets.append((len(v), offset))
        offset += len(v) + 1
    
    # Write .mo file
    with open(mo_file, 'wb') as f:
        # Magic number (little endian)
        f.write(struct.pack('<I', 0x950412de))
        # Version
        f.write(struct.pack('<I', 0))
        # Number of entries
        f.write(struct.pack('<I', len(keys)))
        # Offset of key table
        f.write(struct.pack('<I', 7 * 4))
        # Offset of value table
        f.write(struct.pack('<I', 7 * 4 + 8 * len(keys)))
        # Hash table size (0 = no hash table)
        f.write(struct.pack('<I', 0))
        # Offset of hash table
        f.write(struct.pack('<I', 0))
        
        # Key table (length, offset pairs)
        for length, offset in koffsets:
            f.write(struct.pack('<I', length))
            f.write(struct.pack('<I', offset))
        
        # Value table (length, offset pairs)
        for length, offset in voffsets:
            f.write(struct.pack('<I', length))
            f.write(struct.pack('<I', offset))
        
        # Keys (null-terminated)
        for k in kencoded:
            f.write(k)
            f.write(b'\x00')
        
        # Values (null-terminated)
        for v in vencoded:
            f.write(v)
            f.write(b'\x00')

def main():
    """Compile all .po files to .mo files."""
    locales = ['ar', 'en']
    
    for locale in locales:
        po_file = f'locale/{locale}/LC_MESSAGES/django.po'
        mo_file = f'locale/{locale}/LC_MESSAGES/django.mo'
        
        if os.path.exists(po_file):
            print(f"Compiling {po_file} to {mo_file}")
            translations = parse_po_file(po_file)
            print(f"Found {len(translations)} translations")
            create_mo_file(translations, mo_file)
            print(f"Created {mo_file}")
        else:
            print(f"Warning: {po_file} not found")
    
    print("Translation compilation completed!")

if __name__ == "__main__":
    main()