# -*- coding: utf-8 -*-

# pylint: disable=E0401,W0613,W0703,C0302

import os
import os.path as op
import shutil
import math
from collections import defaultdict

from natsort import natsorted

from pyrevit import HOST_APP
from pyrevit import framework
from pyrevit.framework import System
from pyrevit import coreutils
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script

from pyrevit.runtime.types import DocumentEventUtils
from pyrevit.interop import adc

from ...core.AppPaths import AppPaths
from ...data import keynotes_db as kdb
from ..helpers.UIResourceLoader import UIResourceLoader
from .EditRecordWindow import EditRecordWindow


HELP_URL = 'https://www.notion.so/pyrevitlabs/Manage-Keynotes-6f083d6f66fe43d68dc5d5407c8e19da'


_STR = {
    'Title': 'Manage Keynotes',
    'AllCategories': '-- ALL CATEGORIES --',
    'SetKeynoteFileTransactionName': 'Set Keynote File',
    'UpdateKeynotesTransactionName': 'Update Keynotes',
    'UpdateKeynoteInfo': 'Reloads keynote file and updates keynotes per changes',
    'KeynoteFileNotExists': 'Keynote file is not accessible. Please select a keynote file.',
    'KeynoteFileNotSetup': 'Keynote file is not setup.',
    'KeynoteFileIsReadOnly': 'Keynote file is read-only.',
    'KeynoteFileConnectionFailed': 'Existing keynote file needs to be converted to a format usable by this tool.\n\nAre you sure you want to convert?',
    'KeynoteFileConnectionConvert': 'Convert',
    'KeynoteFileConnectionSelectOther': 'Select a different keynote file',
    'KeynoteFileConnectionHelp': 'Give me more info',
    'KeynoteFileConversionCompleted': 'Conversion completed!',
    'KeynoteFileConversionFailed': 'Conversion failed!',
    'KeynoteFileNotConversion': 'Keynote file is not yet converted.',
    'KeynoteFileLaunchAgain': 'Launch the tool again to manage keynotes.',
    'KeynoteFileBackupException': 'Error backing up existing keynote file.',
    'KeynoteFilePreparingException': 'Error preparing new keynote file.',
    'EnterUniqueKey': 'Enter a Unique Key',
    'ChooseUniqueKey': 'Choose New Key',
    'SelectParentCategory': 'Select Parent Category',
    'SelectFilter': 'Select Filter',
    'KeynoteLockedUnknownUser': 'and unknown user',
    'KeynoteLocked': 'Category is locked and is being edited by {}. Wait until their changes are committed.',
    'CategoryLockedUnknownUser': 'and unknown user',
    'CategoryLocked': 'Category is locked and is being edited by {}. Wait until their changes are committed.',
    'CategoryChildrenLocked': 'At least one keynote in this category is locked. Wait until the changes are committed.',
    'CategoryHasChildren': 'Category "{}" is not empty. Delete all its keynotes first.',
    'CategoryUsed': 'Category "{}" is used in the model. Can not delete.',
    'PromptToDeleteCategory': 'Are you sure you want to delete category "{}"?',
    'KeynoteHasChildren': 'Keynote "{}" has sub-keynotes. Delete all its sub-keynotes first.',
    'KeynoteUsed': 'Keynote "{}" is used in the model. Can not delete.',
    'PromptToDeleteKeynote': 'Are you sure you want to delete keynote "{}"?',
    'ReKeyKeynoteTransaction': 'Rekey Keynote {}',
    'ReKeyKeynoteChildrenLocked': 'At least one child keynote of this keynote is locked. Wait until the changes are committed.',
    'ReCatKeynoteChildrenLocked': 'At least one child keynote of this keynote is locked. Wait until the changes are committed.',
    'KeynoteName': '{} "{}" Keynote @ "{}"',
    'LastEditKeynote': ' - Last Edited By "{}"',
    'SkipDuplicates': 'Do you want me to skip duplicates if any?',
    'ErrorRetrievingKeynotes': 'Error retrieving keynotes.',
    'ADCLockedLocalFile': 'Keynote file is being modified and locked by: {}. Please try again later',
    'ADCLockedLocalFileNone': 'Can not get keynote file from {}',
    'ADCNotAvailable': 'This model is using a keynote file managed by {long} ({short}) but it is not available. Please install/run it and retry.',
}


def _s(key, default=None):
    return _STR.get(key, default or key)


def get_keynote_pcommands():
    return list(reversed([x for x in coreutils.get_enum_values(UI.PostableCommand) if str(x).endswith('Keynote')]))


class KeynoteManagerWindow(forms.WPFWindow):
    def __init__(self, reset_config=False):
        self._paths = AppPaths()
        forms.WPFWindow.__init__(self, self._paths.main_xaml())

        # Merge resources like BatchExport (avoids relative Source issues)
        try:
            UIResourceLoader(self, self._paths).merge_all_for_main()
        except Exception:
            pass

        # Optional custom window chrome (TitleBar + CloseWindowButton)
        try:
            if hasattr(self, 'CloseWindowButton'):
                self.CloseWindowButton.Click += self._on_close_window
            if hasattr(self, 'TitleBar'):
                self.TitleBar.MouseLeftButtonDown += self._on_title_bar_mouse_down
        except Exception:
            pass

        # Basic title (no locale system)
        try:
            self.Title = _s('Title')
        except Exception:
            pass

        self._kfile = None
        self._kfile_handler = None
        self._kfile_ext = None

        self._conn = None
        self._determine_kfile()
        self._connect_kfile()

        self._cache = []
        self._allcat = kdb.RKeynote(key='', text=_s('AllCategories'), parent_key='', locked=False, owner='', children=None)

        self._needs_update = False
        self._config = script.get_config()
        self._used_keysdict = self.get_used_keynote_elements()
        self.load_config(reset_config)
        self.search_tb.Focus()

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

    @property
    def window_geom(self):
        return (self.Width, self.Height, self.Top, self.Left)

    @window_geom.setter
    def window_geom(self, geom_tuple):
        width, height, top, left = geom_tuple
        self.Width = self.Width if math.isnan(width) else width
        self.Height = self.Height if math.isnan(height) else height
        self.Top = self.Top if math.isnan(top) else top
        self.Left = self.Left if math.isnan(left) else left

    @property
    def target_id(self):
        return hash(self._kfile)

    @property
    def search_term(self):
        return self.search_tb.Text

    @search_term.setter
    def search_term(self, value):
        self.search_tb.Text = value

    @property
    def postable_keynote_command(self):
        return get_keynote_pcommands()[self.postcmd_idx]

    @property
    def postcmd_options(self):
        return [self.userknote_rb, self.materialknote_rb, self.elementknote_rb]

    @property
    def postcmd_idx(self):
        for idx, postcmd_op in enumerate(self.postcmd_options):
            if postcmd_op.IsChecked:
                return idx

    @postcmd_idx.setter
    def postcmd_idx(self, index):
        postcmd_op = self.postcmd_options[index if index is not None else 0]
        postcmd_op.IsChecked = True

    @property
    def selected_keynote(self):
        return self.keynotes_tv.SelectedItem

    @property
    def active_category(self):
        return self.categories_tv.SelectedItem

    @property
    def selected_category(self):
        cat = self.active_category
        if cat:
            if cat != self._allcat:
                return cat
            elif self.selected_keynote and not self.selected_keynote.parent_key:
                return self.selected_keynote

    @selected_category.setter
    def selected_category(self, cat_key):
        self._update_ktree(active_catkey=cat_key)

    @property
    def all_categories(self):
        try:
            return kdb.get_categories(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return []

    @property
    def all_keynotes(self):
        try:
            return kdb.get_keynotes(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return []

    @property
    def current_keynotes(self):
        return self.keynotes_tv.ItemsSource

    def get_used_keynote_elements(self):
        used_keys = defaultdict(list)
        try:
            for knote in revit.query.get_used_keynotes(doc=revit.doc):
                key = knote.Parameter[DB.BuiltInParameter.KEY_VALUE].AsString()
                used_keys[key].append(knote.Id)
        except Exception as ex:
            forms.alert(str(ex))
        return used_keys

    def save_config(self):
        new_window_geom_dict = {}
        for kfile, wgeom_value in self._config.get_option('last_window_geom', {}).items():
            if op.exists(kfile):
                new_window_geom_dict[kfile] = wgeom_value
        new_window_geom_dict[self._kfile] = self.window_geom
        self._config.set_option('last_window_geom', new_window_geom_dict)

        new_postcmd_dict = {}
        for kfile, lpc_value in self._config.get_option('last_postcmd_idx', {}).items():
            if op.exists(kfile):
                new_postcmd_dict[kfile] = lpc_value
        new_postcmd_dict[self._kfile] = self.postcmd_idx
        self._config.set_option('last_postcmd_idx', new_postcmd_dict)

        new_category_dict = {}
        for kfile, lc_value in self._config.get_option('last_category', {}).items():
            if op.exists(kfile):
                new_category_dict[kfile] = lc_value
        new_category_dict[self._kfile] = ''
        if self.active_category:
            new_category_dict[self._kfile] = self.active_category.key
        self._config.set_option('last_category', new_category_dict)

        new_search_dict = {}
        if self.search_term:
            new_search_dict[self._kfile] = self.search_term
        self._config.set_option('last_search_term', new_search_dict)

        script.save_config()

    def load_config(self, reset_config):
        last_window_geom_dict = {} if reset_config else self._config.get_option('last_window_geom', {})
        if last_window_geom_dict and self._kfile in last_window_geom_dict:
            width, height, top, left = last_window_geom_dict[self._kfile]
        else:
            width, height, top, left = (None, None, None, None)

        if all([width, height, top, left]) and coreutils.is_box_visible_on_screens(left, top, width, height):
            self.window_geom = (width, height, top, left)
        else:
            self.WindowStartupLocation = framework.Windows.WindowStartupLocation.CenterScreen

        last_postcmd_dict = {} if reset_config else self._config.get_option('last_postcmd_idx', {})
        self.postcmd_idx = last_postcmd_dict.get(self._kfile, 0)

        last_category_dict = {} if reset_config else self._config.get_option('last_category', {})
        if last_category_dict and self._kfile in last_category_dict:
            self._update_ktree(active_catkey=last_category_dict[self._kfile])
        else:
            self.selected_category = self._allcat

        last_searchterm_dict = {} if reset_config else self._config.get_option('last_search_term', {})
        self.search_term = last_searchterm_dict.get(self._kfile, '')

    def _determine_kfile(self):
        self._kfile = revit.query.get_local_keynote_file(doc=revit.doc)
        self._kfile_handler = None
        self._kfile_ext = None
        if not self._kfile:
            self._kfile_ext = revit.query.get_external_keynote_file(doc=revit.doc)
            self._kfile_handler = 'unknown'

        if self._kfile_ext and self._kfile_handler == 'unknown':
            if adc.is_available():
                self._kfile_handler = 'adc'
                local_kfile = adc.get_local_path(self._kfile_ext)
                if local_kfile:
                    locked, owner = adc.is_locked(self._kfile_ext)
                    if locked:
                        forms.alert(_s('ADCLockedLocalFile').format(owner), exitscript=True)
                    adc.sync_file(self._kfile_ext)
                    adc.lock_file(self._kfile_ext)
                    self._kfile = local_kfile
                    try:
                        self.Title += ' (BIM360)'
                    except Exception:
                        pass
                else:
                    forms.alert(_s('ADCLockedLocalFileNone').format(adc.ADC_NAME), exitscript=True)
            else:
                forms.alert(
                    _s('ADCNotAvailable').format(long=adc.ADC_NAME, short=adc.ADC_SHORTNAME),
                    exitscript=True,
                )

    def _change_kfile(self):
        kfile = forms.pick_file('txt')
        if kfile:
            try:
                with revit.Transaction(_s('SetKeynoteFileTransactionName')):
                    revit.update.set_keynote_file(kfile, doc=revit.doc)
            except Exception as skex:
                forms.alert(str(skex))

    def _connect_kfile(self):
        if not self._kfile or not op.exists(self._kfile):
            self._kfile = None
            forms.alert(_s('KeynoteFileNotExists'))
            self._change_kfile()
            self._determine_kfile()

        if not self._kfile:
            raise Exception(_s('KeynoteFileNotSetup'))

        if not os.access(self._kfile, os.W_OK):
            raise Exception(_s('KeynoteFileIsReadOnly'))

        try:
            self._conn = kdb.connect(self._kfile)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message, exitscript=True)
        except Exception as ex:
            res = forms.alert(
                _s('KeynoteFileConnectionFailed'),
                options=[
                    _s('KeynoteFileConnectionConvert'),
                    _s('KeynoteFileConnectionSelectOther'),
                    _s('KeynoteFileConnectionHelp'),
                ],
            )
            if res:
                if res == _s('KeynoteFileConnectionConvert'):
                    try:
                        self._convert_existing()
                        forms.alert(_s('KeynoteFileConversionCompleted'))
                        if not self._conn:
                            forms.alert(_s('KeynoteFileLaunchAgain'), exitscript=True)
                    except Exception as convex:
                        forms.alert('{} {}'.format(_s('KeynoteFileConversionFailed'), convex), exitscript=True)
                elif res == _s('KeynoteFileConnectionSelectOther'):
                    self._change_kfile()
                    self._determine_kfile()
                    self._connect_kfile()
                    return
                elif res == _s('KeynoteFileConnectionHelp'):
                    script.open_url(HELP_URL)
                    script.exit()
            else:
                forms.alert(_s('KeynoteFileNotConversion'), exitscript=True)

    def _empty_file(self, filepath):
        open(filepath, 'w').close()

    def _convert_existing(self):
        temp_kfile = script.get_data_file(op.basename(self._kfile), 'bak')
        if op.exists(temp_kfile):
            script.remove_data_file(temp_kfile)
        try:
            shutil.copy(self._kfile, temp_kfile)
        except Exception:
            raise Exception(_s('KeynoteFileBackupException'))

        try:
            self._empty_file(self._kfile)
        except Exception:
            raise Exception(_s('KeynoteFilePreparingException'))

        try:
            self._conn = kdb.connect(self._kfile)
            kdb.import_legacy_keynotes(self._conn, temp_kfile, skip_dup=True)
        except Exception as ex:
            shutil.copy(temp_kfile, self._kfile)
            raise ex
        finally:
            try:
                script.remove_data_file(temp_kfile)
            except Exception:
                pass

    def _update_ktree(self, active_catkey=None):
        categories = [self._allcat]
        categories.extend(self.all_categories)

        last_idx = 0
        if active_catkey:
            cat_keys = [x.key for x in categories]
            if active_catkey in cat_keys:
                last_idx = cat_keys.index(active_catkey)
        else:
            if self.categories_tv.ItemsSource:
                last_idx = self.categories_tv.SelectedIndex

        self.categories_tv.ItemsSource = None
        self.categories_tv.ItemsSource = categories
        self.categories_tv.SelectedIndex = last_idx

    def _update_ktree_knotes(self, fast=False):
        keynote_filter = self.search_term if self.search_term else None

        if keynote_filter and kdb.RKeynoteFilters.ViewOnly.code in keynote_filter:
            visible_keys = [x.TagText for x in revit.query.get_visible_keynotes(revit.active_view)]
            kdb.RKeynoteFilters.ViewOnly.set_keys(visible_keys)

        if fast and keynote_filter:
            active_tree = list(self._cache)
        else:
            try:
                active_tree = kdb.get_keynotes_tree(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                active_tree = []
            except Exception as ex:
                forms.alert(_s('ErrorRetrievingKeynotes') + '\n' + str(ex), exitscript=True)
                active_tree = []

            selected_cat = self.selected_category
            if selected_cat:
                if selected_cat.key:
                    active_tree = [x for x in active_tree if x.parent_key == self.selected_category.key]
            else:
                parents = defaultdict(list)
                for rkey in active_tree:
                    parents[rkey.parent_key].append(rkey)
                categories = self.all_categories
                for crkey in categories:
                    if crkey.key in parents:
                        crkey.children.extend(parents[crkey.key])
                active_tree = categories

        for knote in active_tree:
            knote.update_used(self._used_keysdict)

        self._cache = list(active_tree)
        if keynote_filter:
            clean_filter = keynote_filter.lower()
            filtered_keynotes = []
            for rkey in active_tree:
                if rkey.filter(clean_filter):
                    filtered_keynotes.append(rkey)
        else:
            filtered_keynotes = active_tree

        self.keynotes_tv.ItemsSource = filtered_keynotes

    def _update_catedit_buttons(self):
        self.catEditButtons.IsEnabled = bool(self.selected_category and not self.selected_category.locked)

    def _update_knoteedit_buttons(self):
        if self.selected_keynote and not self.selected_keynote.locked:
            self.keynoteEditButtons.IsEnabled = bool(self.selected_keynote.parent_key)
            self.keynoteSearch.IsEnabled = self.keynoteEditButtons.IsEnabled
            self.catEditButtons.IsEnabled = not self.keynoteEditButtons.IsEnabled
        else:
            self.keynoteEditButtons.IsEnabled = False
            self.keynoteSearch.IsEnabled = False

    def _pick_new_key(self):
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

        return forms.ask_for_unique_string(
            prompt=_s('EnterUniqueKey'),
            title=_s('ChooseUniqueKey'),
            reserved_values=reserved_keys,
            owner=self,
        )

    def _pick_category(self):
        return forms.SelectFromList.show(
            self.all_categories,
            title=_s('SelectParentCategory'),
            name_attr='text',
            item_container_template=self.Resources['treeViewItem'],
            owner=self,
        )

    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)
        self._update_ktree_knotes(fast=True)

    def clear_search(self, sender, args):
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.search_tb.Focus()

    def custom_filter(self, sender, args):
        sfilter = forms.SelectFromList.show(kdb.RKeynoteFilters.get_available_filters(), title=_s('SelectFilter'), owner=self)
        if sfilter:
            self.search_term = sfilter.format_term(self.search_term)

    def selected_category_changed(self, sender, args):
        self._update_catedit_buttons()
        self._update_ktree_knotes()

    def selected_keynote_changed(self, sender, args):
        self._update_catedit_buttons()
        self._update_knoteedit_buttons()

    def refresh(self, sender, args):
        if self._conn:
            self._update_ktree()
            self._update_ktree_knotes()
        self.search_tb.Focus()

    def add_category(self, sender, args):
        try:
            new_cat = EditRecordWindow(self, self._conn, kdb.EDIT_MODE_ADD_CATEG).show()
            if new_cat:
                self.selected_category = new_cat.key
                self._needs_update = True
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
        except Exception as ex:
            forms.alert(str(ex))

    def edit_category(self, sender, args):
        selected_category = self.selected_category
        selected_keynote = self.selected_keynote

        target_keynote = None
        if selected_category:
            target_keynote = selected_category
        elif selected_keynote and not selected_keynote.parent_key:
            target_keynote = selected_keynote

        if target_keynote:
            if target_keynote.locked:
                owner = '"{}"'.format(target_keynote.owner) if target_keynote.owner else _s('KeynoteLockedUnknownUser')
                forms.alert(_s('KeynoteLocked').format(owner))
            else:
                try:
                    EditRecordWindow(self, self._conn, kdb.EDIT_MODE_EDIT_CATEG, rkeynote=target_keynote).show()
                    self._needs_update = True
                finally:
                    self._update_ktree()
                    if selected_keynote:
                        self._update_ktree_knotes()

    def rekey_category(self, sender, args):
        selected_category = self.selected_category
        selected_keynote = self.selected_keynote

        target_keynote = None
        if selected_category:
            target_keynote = selected_category
        elif selected_keynote and not selected_keynote.parent_key:
            target_keynote = selected_keynote

        if target_keynote:
            if target_keynote.locked:
                owner = '"{}"'.format(target_keynote.owner) if target_keynote.owner else _s('CategoryLockedUnknownUser')
                forms.alert(_s('CategoryLocked').format(owner))
            elif any(x.locked for x in target_keynote.children):
                forms.alert(_s('CategoryChildrenLocked'))
            else:
                try:
                    from_key = target_keynote.key
                    to_key = self._pick_new_key()
                    if to_key and to_key != from_key:
                        kdb.update_category_key(self._conn, from_key, to_key)
                        with kdb.BulkAction(self._conn):
                            for ckey in target_keynote.children:
                                kdb.move_keynote(self._conn, ckey.key, to_key)
                        self.rekey_keynote_refs(from_key, to_key)
                    self._needs_update = True
                finally:
                    self._update_ktree()
                    if selected_keynote:
                        self._update_ktree_knotes()

    def remove_category(self, sender, args):
        selected_category = self.selected_category
        if selected_category:
            if selected_category.has_children():
                forms.alert(_s('CategoryHasChildren').format(selected_category.key))
            elif selected_category.used:
                forms.alert(_s('CategoryUsed').format(selected_category.key))
            else:
                if forms.alert(_s('PromptToDeleteCategory').format(selected_category.key), yes=True, no=True):
                    try:
                        kdb.remove_category(self._conn, selected_category.key)
                        self._needs_update = True
                    finally:
                        self._update_ktree(active_catkey=self._allcat)

    def add_keynote(self, sender, args):
        parent_key = None
        if self.selected_keynote:
            parent_key = self.selected_keynote.parent_key
        elif self.selected_category:
            parent_key = self.selected_category.key

        if not parent_key:
            cat = self._pick_category()
            if cat:
                parent_key = cat.key

        if parent_key:
            try:
                EditRecordWindow(self, self._conn, kdb.EDIT_MODE_ADD_KEYNOTE, pkey=parent_key).show()
                self._needs_update = True
            finally:
                self._update_ktree_knotes()

    def add_sub_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if selected_keynote:
            try:
                EditRecordWindow(self, self._conn, kdb.EDIT_MODE_ADD_KEYNOTE, pkey=selected_keynote.key).show()
                self._needs_update = True
            finally:
                self._update_ktree_knotes()

    def duplicate_keynote(self, sender, args):
        if self.selected_keynote:
            try:
                EditRecordWindow(
                    self,
                    self._conn,
                    kdb.EDIT_MODE_ADD_KEYNOTE,
                    text=self.selected_keynote.text,
                    pkey=self.selected_keynote.parent_key,
                ).show()
                self._needs_update = True
            finally:
                self._update_ktree_knotes()

    def remove_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if selected_keynote:
            if selected_keynote.children:
                forms.alert(_s('KeynoteHasChildren').format(selected_keynote.key))
            elif selected_keynote.used:
                forms.alert(_s('KeynoteUsed').format(selected_keynote.key))
            else:
                if forms.alert(_s('PromptToDeleteKeynote').format(selected_keynote.key), yes=True, no=True):
                    try:
                        kdb.remove_keynote(self._conn, selected_keynote.key)
                        self._needs_update = True
                    finally:
                        self._update_ktree_knotes()

    def edit_keynote(self, sender, args):
        if self.selected_keynote:
            try:
                EditRecordWindow(self, self._conn, kdb.EDIT_MODE_EDIT_KEYNOTE, rkeynote=self.selected_keynote).show()
                self._needs_update = True
            finally:
                self._update_ktree_knotes()

    def rekey_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if any(x.locked for x in selected_keynote.children):
            forms.alert(_s('ReKeyKeynoteChildrenLocked'))
        else:
            try:
                from_key = selected_keynote.key
                to_key = self._pick_new_key()
                if to_key and to_key != from_key:
                    kdb.update_keynote_key(self._conn, from_key, to_key)
                    with kdb.BulkAction(self._conn):
                        for ckey in selected_keynote.children:
                            kdb.move_keynote(self._conn, ckey.key, to_key)
                    self.rekey_keynote_refs(from_key, to_key)
                self._needs_update = True
            finally:
                self._update_ktree_knotes()

    def rekey_keynote_refs(self, from_key, to_key):
        with revit.Transaction(_s('ReKeyKeynoteTransaction').format(from_key)):
            for kid in self.get_used_keynote_elements().get(from_key, []):
                kel = revit.doc.GetElement(kid)
                if kel:
                    key_param = kel.Parameter[DB.BuiltInParameter.KEY_VALUE]
                    if key_param:
                        key_param.Set(to_key)

    def recat_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if any(x.locked for x in selected_keynote.children):
            forms.alert(_s('ReCatKeynoteChildrenLocked'))
        else:
            try:
                from_cat = selected_keynote.parent_key
                to_cat = self._pick_category()
                if to_cat and to_cat.key != from_cat:
                    kdb.move_keynote(self._conn, selected_keynote.key, to_cat.key)
                self._needs_update = True
            finally:
                self._update_ktree_knotes()

    def show_keynote(self, sender, args):
        if self.selected_keynote:
            self.Close()
            out = script.get_output()
            kids = self.get_used_keynote_elements().get(self.selected_keynote.key, [])
            for kid in kids:
                source = ''
                viewname = ''
                kel = revit.doc.GetElement(kid)
                ehist = revit.query.get_history(kel)
                if kel:
                    source = kel.Parameter[DB.BuiltInParameter.KEY_SOURCE_PARAM].AsString()
                    vel = revit.doc.GetElement(kel.OwnerViewId)
                    if vel:
                        viewname = revit.query.get_name(vel)

                report = _s('KeynoteName').format(out.linkify(kid), source, viewname)
                if ehist:
                    report += _s('LastEditKeynote').format(ehist.last_changed_by)
                print(report)

    def place_keynote(self, sender, args):
        self.Close()
        keynotes_cat = revit.query.get_category(DB.BuiltInCategory.OST_KeynoteTags)
        if keynotes_cat and self.selected_keynote:
            knote_key = self.selected_keynote.key
            def_kn_typeid = revit.doc.GetDefaultFamilyTypeId(keynotes_cat.Id)
            kn_type = revit.doc.GetElement(def_kn_typeid)
            if kn_type:
                try:
                    DocumentEventUtils.PostCommandAndUpdateNewElementProperties(
                        HOST_APP.uiapp,
                        revit.doc,
                        self.postable_keynote_command,
                        _s('UpdateKeynotesTransactionName'),
                        DB.BuiltInParameter.KEY_VALUE,
                        knote_key,
                    )
                except Exception as ex:
                    forms.alert(str(ex))

    def change_keynote_file(self, sender, args):
        self._change_kfile()
        self._determine_kfile()
        self._connect_kfile()
        self._needs_update = True
        self.Close()

    def show_keynote_file(self, sender, args):
        coreutils.show_entry_in_explorer(self._kfile)

    def import_keynotes(self, sender, args):
        kfile = forms.pick_file('txt')
        if kfile:
            res = forms.alert(_s('SkipDuplicates'), yes=True, no=True)
            try:
                kdb.import_legacy_keynotes(self._conn, kfile, skip_dup=res)
            finally:
                self._update_ktree(active_catkey=self._allcat)
                self._update_ktree_knotes()

    def export_keynotes(self, sender, args):
        kfile = forms.save_file('txt')
        if kfile:
            try:
                kdb.export_legacy_keynotes(self._conn, kfile)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)

    def export_visible_keynotes(self, sender, args):
        kfile = forms.save_file('txt')
        if kfile:
            include_list = set()
            for rkey in self.current_keynotes:
                include_list.update(rkey.collect_keys())
            try:
                kdb.export_legacy_keynotes(self._conn, kfile, include_keys=include_list)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)

    def update_model(self, sender, args):
        self._needs_update = True
        self.Close()

    def window_closing(self, sender, args):
        if self._kfile_handler == 'adc':
            try:
                adc.unlock_file(self._kfile_ext)
            except Exception:
                pass

        if self._needs_update:
            with revit.Transaction(_s('UpdateKeynotesTransactionName')):
                revit.update.update_linked_keynotes(doc=revit.doc)

        try:
            self.save_config()
        except Exception:
            pass

        if self._conn:
            try:
                self._conn.Dispose()
            except Exception:
                pass
