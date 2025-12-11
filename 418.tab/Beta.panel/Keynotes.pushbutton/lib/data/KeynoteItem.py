# -*- coding: utf-8 -*-

class KeynoteItem(object):
    def __init__(self, key, description, parent_key=None):
        self.Key = key
        self.Description = description
        self.ParentKey = parent_key
        self.Children = []
        self.Count = 0

    @property
    def DisplayText(self):
        if self.Count > 0:
            return "{} ({})".format(self.Description, self.Count)
        return self.Description
