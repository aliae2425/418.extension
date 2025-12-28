# -*- coding: utf-8 -*-
"""418.extension startup

Hook: détecte quand une vue est placée sur une feuille (création/modif d'un Viewport)
et renomme automatiquement la vue.

Format demandé (remplacement):
  <numero de la feuille>_<niveau>_<titre sur la feuille>_<numero vue>.<echelle>

Exemple:
  A101_RDC_Coupe AA_1.100

Remarque: ce script tourne au chargement de l'extension (pas via un bouton).
"""

from __future__ import print_function

try:
    import clr  # noqa: F401
except Exception:
    clr = None

from pyrevit import DB

try:
    import builtins  # type: ignore
except Exception:
    import __builtin__ as builtins  # type: ignore


# ------------------------------- Configuration ------------------------------
# Format demandé (remplacement):
#   <numero de la feuille>_<niveau>_<titre sur la feuille>_<numero vue>.<echelle>
# Exemple:
#   A101_RDC_Coupe AA_1.100
NAME_SEPARATOR = "_"

MISSING_TOKEN = "NA"

# Ne pas renommer ces types (souvent placés plusieurs fois)
SKIP_VIEW_TYPES = set()
for _vt_name in ("DrawingSheet", "Legend", "Schedule", "Report"):
    try:
        SKIP_VIEW_TYPES.add(getattr(DB.ViewType, _vt_name))
    except Exception:
        pass

# Limite raisonnable (Revit impose une limite interne; on reste conservateur)
MAX_VIEW_NAME_LEN = 250


# ------------------------------ Etat global hook ----------------------------
_HOOK_FLAG = "_418_autorename_view_on_sheet_hook_installed"
_STATE_FLAG = "_418_autorename_view_on_sheet_hook_state"


def _get_state():
    state = getattr(builtins, _STATE_FLAG, None)
    if state is None:
        state = {
            "pending": [],  # list of (doc, viewIdInt, desiredName)
            "handlers": {},
        }
        setattr(builtins, _STATE_FLAG, state)
    return state


def _safe_str(value):
    try:
        return str(value)
    except Exception:
        try:
            return value.ToString()
        except Exception:
            return ""


def _sanitize_token(token):
    """Nettoie un morceau de nom de vue pour éviter les caractères interdits."""
    text = (_safe_str(token) or "").strip()
    if not text:
        return ""

    invalid = set('\\/:*?"<>|{}[];`~\n\r\t')
    cleaned = []
    for ch in text:
        cleaned.append("-" if ch in invalid else ch)
    return "".join(cleaned).strip()


def _get_viewport_detail_number(viewport):
    if viewport is None:
        return ""
    try:
        p = viewport.get_Parameter(DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
        if p:
            val = _safe_str(p.AsString())
            return (val or "").strip()
    except Exception:
        pass
    return ""


def _get_view_scale_token(view):
    try:
        sc = int(getattr(view, "Scale", 0) or 0)
        if sc > 0:
            return str(sc)
    except Exception:
        pass

    for _pname in ("VIEW_SCALE",):
        try:
            bip = getattr(DB.BuiltInParameter, _pname)
        except Exception:
            continue
        try:
            p = view.get_Parameter(bip)
            if p:
                ival = p.AsInteger()
                if ival and ival > 0:
                    return str(int(ival))
        except Exception:
            continue

    return ""


def _get_view_level_token(view):
    try:
        lvl = getattr(view, "GenLevel", None)
        if lvl is not None:
            name = _safe_str(getattr(lvl, "Name", ""))
            if name:
                return name
    except Exception:
        pass

    doc = None
    try:
        doc = view.Document
    except Exception:
        doc = None

    for _pname in (
        "PLAN_VIEW_LEVEL",
        "VIEWER_ASSOC_LEVEL",
        "VIEWER_ASSOCIATED_LEVEL",
        "ASSOCIATED_LEVEL",
    ):
        try:
            bip = getattr(DB.BuiltInParameter, _pname)
        except Exception:
            continue
        try:
            p = view.get_Parameter(bip)
            if not p:
                continue
            eid = p.AsElementId()
            if eid and int(eid.IntegerValue) > 0 and doc is not None:
                el = doc.GetElement(eid)
                if el is not None:
                    name = _safe_str(getattr(el, "Name", ""))
                    if name:
                        return name
        except Exception:
            continue

    return ""


def _get_view_title_on_sheet_token(view):
    for _pname in ("VIEW_DESCRIPTION", "VIEW_TITLE"):
        try:
            bip = getattr(DB.BuiltInParameter, _pname)
        except Exception:
            continue
        try:
            p = view.get_Parameter(bip)
            if p:
                val = _safe_str(p.AsString())
                if val and val.strip():
                    return val.strip()
        except Exception:
            continue
    return ""


def _build_desired_name(sheet, viewport, view):
    sheet_number = _safe_str(getattr(sheet, "SheetNumber", "")).strip()
    if not sheet_number:
        return None

    level_token = _sanitize_token(_get_view_level_token(view)) or MISSING_TOKEN
    title_token = _sanitize_token(_get_view_title_on_sheet_token(view)) or MISSING_TOKEN

    detail_number = _sanitize_token(_get_viewport_detail_number(viewport) or "1") or "1"
    scale_token = _sanitize_token(_get_view_scale_token(view)) or MISSING_TOKEN

    desired = "{sn}{sep}{lvl}{sep}{title}{sep}{num}.{scale}".format(
        sn=_sanitize_token(sheet_number) or sheet_number,
        sep=NAME_SEPARATOR,
        lvl=level_token,
        title=title_token,
        num=detail_number,
        scale=scale_token,
    )

    if len(desired) > MAX_VIEW_NAME_LEN:
        desired = desired[:MAX_VIEW_NAME_LEN].rstrip()
    return desired


def _queue_rename(doc, view_id, desired_name):
    state = _get_state()
    item = (doc, int(view_id.IntegerValue), desired_name)

    for existing in state["pending"]:
        if existing[0] == item[0] and existing[1] == item[1] and existing[2] == item[2]:
            return

    state["pending"].append(item)


def _try_set_unique_view_name(view, desired_name):
    base = desired_name

    for idx in range(0, 50):
        if idx == 0:
            candidate = base
        else:
            candidate = "{0} ({1})".format(base, idx + 1)

        if len(candidate) > MAX_VIEW_NAME_LEN:
            candidate = candidate[:MAX_VIEW_NAME_LEN].rstrip()

        try:
            view.Name = candidate
            return True
        except Exception:
            continue

    return False


def _is_renamable_view(view):
    try:
        if view is None or not view.IsValidObject:
            return False
    except Exception:
        return False

    try:
        if getattr(view, "IsTemplate", False):
            return False
    except Exception:
        pass

    try:
        if view.ViewType in SKIP_VIEW_TYPES:
            return False
    except Exception:
        pass

    try:
        if hasattr(view, "IsReadOnly") and view.IsReadOnly:
            return False
    except Exception:
        pass

    return True


def _on_document_changed(sender, args):
    try:
        doc = args.GetDocument()
        if doc is None or not doc.IsValidObject:
            return

        changed_ids = []
        try:
            changed_ids.extend(list(args.GetAddedElementIds()))
        except Exception:
            pass
        try:
            changed_ids.extend(list(args.GetModifiedElementIds()))
        except Exception:
            pass

        if not changed_ids:
            return

        for eid in changed_ids:
            el = doc.GetElement(eid)
            if el is None:
                continue

            if isinstance(el, DB.Viewport):
                try:
                    sheet = doc.GetElement(el.SheetId)
                    view = doc.GetElement(el.ViewId)
                except Exception:
                    continue

                if sheet is None or view is None:
                    continue

                if not _is_renamable_view(view):
                    continue

                desired = _build_desired_name(sheet, el, view)
                if not desired:
                    continue

                _queue_rename(doc, el.ViewId, desired)

    except Exception:
        return


def _on_idling(sender, args):
    state = _get_state()
    pending = state.get("pending") or []
    if not pending:
        return

    state["pending"] = []

    by_doc = {}
    for doc, view_id_int, desired_name in pending:
        if doc is None:
            continue
        try:
            if not doc.IsValidObject:
                continue
        except Exception:
            continue
        by_doc.setdefault(doc, []).append((view_id_int, desired_name))

    for doc, items in by_doc.items():
        t = None
        try:
            t = DB.Transaction(doc, "418: Auto-rename view on sheet")
            t.Start()

            for view_id_int, desired_name in items:
                view = doc.GetElement(DB.ElementId(view_id_int))
                if not _is_renamable_view(view):
                    continue

                try:
                    if _safe_str(view.Name) == _safe_str(desired_name):
                        continue
                except Exception:
                    pass

                _try_set_unique_view_name(view, desired_name)

            t.Commit()
        except Exception:
            try:
                if t and t.HasStarted():
                    t.RollBack()
            except Exception:
                pass


def _install_hooks():
    if getattr(builtins, _HOOK_FLAG, False):
        return

    uiapp = globals().get("__revit__", None)
    if uiapp is None:
        return

    state = _get_state()

    try:
        app = uiapp.Application
    except Exception:
        app = None

    try:
        if app is not None:
            app.DocumentChanged += _on_document_changed
    except Exception:
        pass

    try:
        uiapp.Idling += _on_idling
    except Exception:
        pass

    state["handlers"]["doc_changed"] = _on_document_changed
    state["handlers"]["idling"] = _on_idling

    setattr(builtins, _HOOK_FLAG, True)


_install_hooks()
