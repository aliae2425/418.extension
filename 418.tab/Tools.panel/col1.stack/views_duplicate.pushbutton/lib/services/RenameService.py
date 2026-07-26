# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re as _re


class RenameService(object):
    """Applique une transformation de nommage à une chaîne.

    Supporte le mode littéral (str.replace) et le mode regex (re.sub).
    En mode regex, une expression invalide est signalée via `regex_error`
    et laisse le nom source intact (jamais d'exception vers l'appelant).
    """

    def __init__(self, prefixe=u'', rechercher=u'', remplacer=u'',
                 suffixe=u'', use_regex=False):
        self.prefixe = prefixe
        self.rechercher = rechercher
        self.remplacer = remplacer
        self.suffixe = suffixe
        self.use_regex = use_regex
        self._pattern = None
        self._regex_error = u''
        if use_regex and rechercher:
            self._compile()

    def _compile(self):
        try:
            self._pattern = _re.compile(self.rechercher)
            self._regex_error = u''
        except Exception as exc:
            self._pattern = None
            self._regex_error = unicode(exc) if hasattr(__builtins__, 'unicode') else str(exc)

    @property
    def regex_error(self):
        """Message d'erreur si l'expression régulière est invalide, sinon vide."""
        return self._regex_error

    @property
    def is_valid(self):
        """False si le mode regex est actif et que l'expression est invalide."""
        if self.use_regex and self.rechercher:
            return self._pattern is not None
        return True

    def apply(self, name):
        """Retourne `prefixe + substitution(name) + suffixe`.

        En mode regex invalide retourne `prefixe + name + suffixe` (pas d'exception).
        """
        result = name
        if self.rechercher:
            if self.use_regex:
                if self._pattern is not None:
                    try:
                        result = self._pattern.sub(self.remplacer, result)
                    except Exception:
                        pass
            else:
                result = result.replace(self.rechercher, self.remplacer)
        return self.prefixe + result + self.suffixe
