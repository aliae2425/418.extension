# -*- coding: utf-8 -*-
import codecs
from .KeynoteItem import KeynoteItem

class KeynoteParser(object):
    def parse(self, file_path):
        items = {}
        roots = []
        
        try:
            # Try reading as UTF-8 (standard for Revit Keynotes)
            with codecs.open(file_path, 'r', 'utf-8') as f:
                lines = f.readlines()
        except Exception:
            # Fallback to default encoding (e.g. ANSI/cp1252)
            with open(file_path, 'r') as f:
                lines = f.readlines()

        # First pass: create all items
        for line in lines:
            if not line.strip() or line.startswith('#'):
                continue
            
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                key = parts[0]
                desc = parts[1]
                parent = parts[2] if len(parts) > 2 else None
                
                # Clean up parent key if it's empty string
                if parent == '':
                    parent = None
                
                item = KeynoteItem(key, desc, parent)
                items[key] = item

        # Second pass: build hierarchy
        for key, item in items.items():
            if item.ParentKey and item.ParentKey in items:
                parent = items[item.ParentKey]
                parent.Children.append(item)
            else:
                roots.append(item)
        
        # Sort roots by Key
        roots.sort(key=lambda x: x.Key)
        
        # Sort children recursively
        self._sort_children(roots)
                
        return roots

    def _sort_children(self, items):
        for item in items:
            item.Children.sort(key=lambda x: x.Key)
            self._sort_children(item.Children)
