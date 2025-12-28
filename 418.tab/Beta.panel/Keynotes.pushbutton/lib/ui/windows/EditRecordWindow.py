# -*- coding: utf-8 -*-

# pylint: disable=E0401,W0613,W0703,C0302

from natsort import natsorted

from pyrevit import framework
from pyrevit.framework import System
from pyrevit import forms

from ...core.AppPaths import AppPaths
from ...data import keynotes_db as kdb
from ..helpers.UIResourceLoader import UIResourceLoader


_STR = {
    'AddCategoryTitle': 'Add Category',
    'EditCategoryTitle': 'Edit Category',
    'AddKeynoteTitle': 'Add Keynote',
    'EditKeynoteTitle': 'Edit Keynote',
    'CreateCategoryKey': 'Create Category Key',
    'EditCategoryKey': 'Category Key',
    'CreateKeynoteKey': 'Create Keynote Key',
    'EditKeynoteKey': 'Keynote Key',
    'AddCategoryApply': 'Add Category',
    'EditCategoryApply': 'Update Category',
    'AddKeynoteApply': 'Add Keynote',
    'EditKeynoteApply': 'Update Keynote',
    'EnterUniqueKey': 'Enter a Unique Key',
    'KeynoteKeyValidate': 'Keynote must have a unique key.',
    'KeynoteTextValidate': 'Keynote must have a text.',
    'KeynoteParentValidate': 'Keynote must have a parent.',
    'CategoryKeyValidate': 'Category must have a unique key.',
    'CategoryTitleValidate': 'Category must have a title.',
    'CategoryTitleRemoved': 'Existing title is removed. Category must have a title.',
    'KeynoteTextRemoved': 'Existing text is removed. Keynote must have a text.',
    'ComingSoon': 'Not yet implemented. Coming soon.',
    'SelectTemplate': 'Select Template',
    'TemplateReserved': '-- reserved for future use --',
    'TemplateDontUse': '!! do not use !!',
}


def _s(key, default=None):
    return _STR.get(key, default or key)


class EditRecordWindow(forms.WPFWindow):
    def __init__(
        self,
        owner,
        conn,
        mode,
        rkeynote=None,
        rkey=None,
        text=None,
        pkey=None,
    ):
        paths = AppPaths()
        forms.WPFWindow.__init__(self, paths.edit_record_xaml())

        try:
            UIResourceLoader(self, paths).merge_all_for_edit_record()
        except Exception:
            pass

        try:
            if hasattr(self, 'CloseWindowButton'):
                self.CloseWindowButton.Click += self._on_close_window
            if hasattr(self, 'TitleBar'):
                self.TitleBar.MouseLeftButtonDown += self._on_title_bar_mouse_down
        except Exception:
            pass

        self.Owner = owner
        self._res = None
        self._commited = False
        self._reserved_key = None

        self._conn = conn
        self._mode = mode
        self._cat = False
        self._rkeynote = rkeynote
        self._rkey = rkey
        self._text = text
        self._pkey = pkey

    def _on_close_window(self, sender, args):
        try:
            self.Close()
        except Exception:
            pass

    def _on_title_bar_mouse_down(self, sender, args):
        try:
            self.DragMove()
        except Exception:
            pass

        if self._mode == kdb.EDIT_MODE_ADD_CATEG:
            self._cat = True
            self.hide_element(self.recordParentInput)
            self.Title = _s('AddCategoryTitle')
            self.recordKeyTitle.Text = _s('CreateCategoryKey')
            self.applyChanges.Content = _s('AddCategoryApply')

        elif self._mode == kdb.EDIT_MODE_EDIT_CATEG:
            self._cat = True
            self.hide_element(self.recordParentInput)
            self.Title = _s('EditCategoryTitle')
            self.recordKeyTitle.Text = _s('EditCategoryKey')
            self.applyChanges.Content = _s('EditCategoryApply')
            self.recordKey.IsEnabled = False
            if self._rkeynote and self._rkeynote.key:
                kdb.begin_edit(self._conn, self._rkeynote.key, category=True)

        elif self._mode == kdb.EDIT_MODE_ADD_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = _s('AddKeynoteTitle')
            self.recordKeyTitle.Text = _s('CreateKeynoteKey')
            self.applyChanges.Content = _s('AddKeynoteApply')

        elif self._mode == kdb.EDIT_MODE_EDIT_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = _s('EditKeynoteTitle')
            self.recordKeyTitle.Text = _s('EditKeynoteKey')
            self.applyChanges.Content = _s('EditKeynoteApply')
            self.recordKey.IsEnabled = False
            self.recordParent.IsEnabled = True
            if self._rkeynote and self._rkeynote.key:
                kdb.begin_edit(self._conn, self._rkeynote.key, category=False)

        if self._rkeynote:
            self.active_key = self._rkeynote.key
            self.active_text = self._rkeynote.text
            self.active_parent_key = self._rkeynote.parent_key

        if self._rkey:
            self.active_key = self._rkey
        if self._text:
            self.active_text = self._text
        if self._pkey:
            self.active_parent_key = self._pkey

        self.recordText.Focus()
        self.recordText.SelectAll()

    @property
    def active_key(self):
        if self.recordKey.Content and u'\u25CF' not in self.recordKey.Content:
            return self.recordKey.Content

    @active_key.setter
    def active_key(self, value):
        self.recordKey.Content = value

    @property
    def active_text(self):
        return self.recordText.Text

    @active_text.setter
    def active_text(self, value):
        self.recordText.Text = (value or '').strip()

    @property
    def active_parent_key(self):
        return self.recordParent.Content

    @active_parent_key.setter
    def active_parent_key(self, value):
        self.recordParent.Content = value

    def show(self):
        self.ShowDialog()
        return self._res

    def commit(self):
        if self._mode == kdb.EDIT_MODE_ADD_CATEG:
            if not self.active_key:
                forms.alert(_s('CategoryKeyValidate'))
                return False
            elif not self.active_text.strip():
                forms.alert(_s('CategoryTitleValidate'))
                return False
            try:
                self._res = kdb.add_category(self._conn, self.active_key, self.active_text)
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        elif self._mode == kdb.EDIT_MODE_EDIT_CATEG:
            if not self.active_text:
                forms.alert(_s('CategoryTitleRemoved'))
                return False
            try:
                if self.active_text != self._rkeynote.text:
                    kdb.update_category_title(self._conn, self.active_key, self.active_text)
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        elif self._mode == kdb.EDIT_MODE_ADD_KEYNOTE:
            if not self.active_key:
                forms.alert(_s('KeynoteKeyValidate'))
                return False
            elif not self.active_text:
                forms.alert(_s('KeynoteTextValidate'))
                return False
            elif not self.active_parent_key:
                forms.alert(_s('KeynoteParentValidate'))
                return False
            try:
                self._res = kdb.add_keynote(self._conn, self.active_key, self.active_text, self.active_parent_key)
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        elif self._mode == kdb.EDIT_MODE_EDIT_KEYNOTE:
            if not self.active_text:
                forms.alert(_s('KeynoteTextRemoved'))
                return False
            try:
                if self.active_text != self._rkeynote.text:
                    kdb.update_keynote_text(self._conn, self.active_key, self.active_text)
                if self.active_parent_key != self._rkeynote.parent_key:
                    kdb.move_keynote(self._conn, self.active_key, self.active_parent_key)
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        return True

    def pick_key(self, sender, args):
        if self._reserved_key:
            try:
                kdb.release_key(self._conn, self._reserved_key, category=self._cat)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return

        try:
            categories = kdb.get_categories(self._conn)
            keynotes = kdb.get_keynotes(self._conn)
            locks = kdb.get_locks(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return

        reserved_keys = [x.key for x in categories]
        reserved_keys.extend([x.key for x in keynotes])
        reserved_keys.extend([x.LockTargetRecordKey for x in locks])

        new_key = forms.ask_for_unique_string(
            prompt=_s('EnterUniqueKey'),
            title=self.Title,
            reserved_values=reserved_keys,
            owner=self,
        )
        if new_key:
            try:
                kdb.reserve_key(self._conn, new_key, category=self._cat)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return
            self._reserved_key = new_key
            self.active_key = new_key

    def pick_parent(self, sender, args):
        categories = kdb.get_categories(self._conn)
        keynotes = kdb.get_keynotes(self._conn)
        available_parents = [x.key for x in categories]
        available_parents.extend([x.key for x in keynotes])
        if self.active_key in available_parents:
            available_parents.remove(self.active_key)

        new_parent = forms.SelectFromList.show(
            natsorted(available_parents),
            title='Select Parent',
            multiselect=False,
        )
        if new_parent:
            try:
                kdb.reserve_key(self._conn, self.active_key, category=self._cat)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return
            self._reserved_key = self.active_key
            self.active_parent_key = new_parent

    def to_upper(self, sender, args):
        self.active_text = (self.active_text or '').upper()

    def to_lower(self, sender, args):
        self.active_text = (self.active_text or '').lower()

    def to_title(self, sender, args):
        self.active_text = (self.active_text or '').title()

    def to_sentence(self, sender, args):
        self.active_text = (self.active_text or '').capitalize()

    def select_template(self, sender, args):
        template = forms.SelectFromList.show(
            [_s('TemplateReserved'), _s('TemplateDontUse')],
            title=_s('SelectTemplate'),
            owner=self,
        )
        if template:
            self.active_text = template

    def translate(self, sender, args):
        forms.alert(_s('ComingSoon'))

    def apply_changes(self, sender, args):
        self._commited = self.commit()
        if self._commited:
            self.Close()

    def cancel_changes(self, sender, args):
        self.Close()

    def window_closing(self, sender, args):
        if not self._commited:
            if self._reserved_key:
                try:
                    kdb.release_key(self._conn, self._reserved_key, category=self._cat)
                except Exception:
                    pass
            try:
                kdb.end_edit(self._conn)
            except Exception:
                pass
