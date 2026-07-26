# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re as _re

try:
    from lib.services.TokenExpander import TokenExpander
except Exception:
    from services.TokenExpander import TokenExpander


class RenameService(object):
    """Applique une transformation de nommage à une chaîne.

    Modes
    ─────
        littéral  str.replace (défaut)
        regex     re.sub — regex invalide → regex_error non vide,
                  apply() retourne le nom intact (jamais d'exception)

    Tokens
    ──────
        Les tokens ({date}, {n}, {type}…) sont résolus dans prefixe,
        remplacer et suffixe via TokenExpander avant chaque apply().
        Passer ``index`` et ``context`` à apply() pour les valoriser.
    """

    def __init__(self, prefixe=u'', rechercher=u'', remplacer=u'',
                 suffixe=u'', use_regex=False, expander=None):
        self.prefixe = prefixe
        self.rechercher = rechercher
        self.remplacer = remplacer
        self.suffixe = suffixe
        self.use_regex = use_regex
        self._expander = expander or TokenExpander()
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
            try:
                self._regex_error = unicode(exc)
            except NameError:
                self._regex_error = str(exc)

    @property
    def regex_error(self):
        """Message d'erreur si l'expression régulière est invalide, sinon vide."""
        return self._regex_error

    @property
    def is_valid(self):
        """False si le mode regex est actif et l'expression invalide."""
        if self.use_regex and self.rechercher:
            return self._pattern is not None
        return True

    def apply(self, name, index=1, context=None):
        """Retourne prefixe + substitution(name) + suffixe, tokens résolus.

        Args:
            name    : chaîne source
            index   : numéro de la copie courante — alimente {n}
            context : dict de tokens supplémentaires, ex. {'type': 'FloorPlan'}
        """
        remplacer = self._expander.expand(self.remplacer, index=index, context=context)
        result = name
        if self.rechercher:
            if self.use_regex:
                if self._pattern is not None:
                    try:
                        result = self._pattern.sub(remplacer, result)
                    except Exception:
                        pass
            else:
                result = result.replace(self.rechercher, remplacer)
        prefixe = self._expander.expand(self.prefixe, index=index, context=context)
        suffixe = self._expander.expand(self.suffixe, index=index, context=context)
        return prefixe + result + suffixe
