# -*- coding: utf-8 -*-
import codecs
from ..data.KeynoteItem import KeynoteItem

class KeynoteParser(object):
    def parse(self, file_path):
        items = {} # key -> item
        roots = []
        
        try:
            with codecs.open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            # Fallback for other encodings if needed, or just fail
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
        # First pass: create all items
        for line in lines:
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            key = parts[0]
            desc = parts[1] if len(parts) > 1 else ""
            parent_key = parts[2] if len(parts) > 2 else None
            
            item = KeynoteItem(key, desc, parent_key)
            items[key] = item
            
        # Second pass: build hierarchy
        for key, item in items.items():
            if item.ParentKey and item.ParentKey in items:
                parent = items[item.ParentKey]
                parent.Children.append(item)
            else:
                roots.append(item)
                
        return roots

    def save(self, file_path, roots):
        lines = []
        
        # Helper to flatten the tree
        def flatten(item_list):
            flat = []
            for item in item_list:
                flat.append(item)
                flat.extend(flatten(item.Children))
            return flat

        all_items = flatten(roots)
        # Sort by key for nicer output
        all_items.sort(key=lambda x: x.Key)

        for item in all_items:
            # Format: Key \t Description \t ParentKey
            line = "{}\t{}".format(item.Key, item.Description)
            if item.ParentKey:
                line += "\t{}".format(item.ParentKey)
            lines.append(line)
            
        with codecs.open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
