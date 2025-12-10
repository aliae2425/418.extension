# -*- coding: utf-8 -*-

class KeynoteItem(object):
    def __init__(self, key, description, parent_key=None):
        self.Key = key
        self.Description = description
        self.ParentKey = parent_key
        self.Children = []

    def __repr__(self):
        return "<KeynoteItem {} - {}>".format(self.Key, self.Description)
