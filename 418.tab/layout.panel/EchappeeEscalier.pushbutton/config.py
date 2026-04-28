# -*- coding: utf-8 -*-
# Lecture et écriture de la hauteur d'échappée configurée par l'utilisateur.
from pyrevit.userconfig import user_config

SECTION = 'echappee_escalier'
DEFAUT_HAUTEUR_M = 1.90


def lire_hauteur():
    # Crée la section si elle n'existe pas encore
    try:
        user_config.add_section(SECTION)
    except Exception:
        pass
    val = user_config.echappee_escalier.get_option('hauteur', str(DEFAUT_HAUTEUR_M))
    try:
        return float(val)
    except (ValueError, TypeError):
        return DEFAUT_HAUTEUR_M


def sauver_hauteur(h):
    try:
        user_config.add_section(SECTION)
    except Exception:
        pass
    user_config.echappee_escalier.hauteur = str(h)
    user_config.save_changes()
