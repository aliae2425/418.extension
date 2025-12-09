# -*- coding: utf-8 -*-
import os
import subprocess

__title__ = "Update Checker"
__author__ = "Aliae"
__min_revit_ver__ = 2020

# Icons: place two PNGs in this folder: up_to_date.png and update_available.png
# SmartButton can switch icon at load via get_button_icon

EXT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
REPO_DIR = EXT_ROOT  # assuming the extension folder is the git repo root

REMOTE = os.environ.get("UPDATE_REMOTE", "origin")
BRANCH = os.environ.get("UPDATE_BRANCH", "main")


def __selfinit__(button, *args, **kwargs):
    # Allow pyRevit to initialize the smartbutton module
    # Returning True indicates successful initialization
    return True


def _run_git(args, cwd=None):
    try:
        proc = subprocess.Popen(["git"] + args, cwd=cwd or REPO_DIR,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=False)
        out, err = proc.communicate(timeout=5)
        if proc.returncode == 0:
            return out.decode("utf-8").strip()
    except Exception:
        pass
    return None


def _get_local_head():
    return _run_git(["rev-parse", "HEAD"]) or ""


def _get_remote_head():
    # Use ls-remote to avoid requiring fetch permissions
    ref = "refs/heads/{0}".format(BRANCH)
    line = _run_git(["ls-remote", REMOTE, ref]) or ""
    if not line:
        return ""
    return line.split("\t")[0]


def _is_update_available():
    local = _get_local_head()
    remote = _get_remote_head()
    if not local or not remote:
        return False
    return local != remote


def get_button_tooltip():
    if _is_update_available():
        return "Une mise à jour est disponible pour le plugin."
    return "Le plugin est à jour."


def get_button_icon():
    icon_name = "update_available.png" if _is_update_available() else "up_to_date.png"
    icon_path = os.path.join(os.path.dirname(__file__), icon_name)
    if os.path.exists(icon_path):
        return icon_path
    # fallback to default
    return os.path.join(os.path.dirname(__file__), "up_to_date.png")


def script_execute():
    # If clicked, optionally open README or run update
    # For now, just inform the user.
    try:
        from pyrevit import script
        logger = script.get_logger()
        if _is_update_available():
            logger.info("Mise à jour disponible sur la branche main.")
        else:
            logger.info("Le plugin est déjà à jour.")
    except Exception:
        pass
