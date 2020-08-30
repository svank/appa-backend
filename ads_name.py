from __future__ import annotations

import itertools
import re
import string
from typing import Tuple

from unidecode import unidecode_expect_ascii as unidecode

import local_config
import name_aware

_name_cache = {}
# Translation table to remove all characters that aren't lower-case ascii
# letters or a space. (A space is allowable inside a last name, and will be
# removed as part of a given name during splitting.)
ok_chars = string.ascii_lowercase + ' '
_char_filter = str.maketrans('', '', ''.join(c for c in map(chr, range(256))
                                             if c not in ok_chars))
# Translation table to replace with spaces characters that should be allowed
# to split names into pieces. The period is included here so we can gracefully
# handle a type like "Last, F.M."
_char_prefilter = str.maketrans("-.", "  ")

# Collapses multiple, sequential spaces into one. Used on the last name for
# internal spaces, not needed for given names which are split at white space.
_multiple_spaces_pattern = re.compile(" +")

_name_synonyms = name_aware.NameAwareDict()


class ADSName:
    """Implements a singleton representation of names with appropriate equality
    
    Instances should be created through ADSName.parse(name_data). See below.
    
    All operations are case insensitive. The original input data, with case,
    (from the first time an instance is loaded---see below) is preserved in
    the original_name attribute.
    
    Authors can be listed in different ways. E.g.:
        Lastname, First middle
        Lastname, First M.
        Lastname, F. M.
        Lastname, F.
        Lastname
    One author can also be listed different ways on different publications.
    This means there is an inherent ambiguity in name-matching (never mind the
    possibility of two people with the _same_ name!). To attempt to handle
    this, this class decomposes name strings into first, middle, and last
    names or initials and supports comparison using ADS's name matching
    rules as I understand them.

    See "Author Searches" under
    https://adsabs.github.io/help/search/search-syntax
    
    There is meant to be only one instance of ADSName for each input name
    string. This allows equality checking to be optimized. This parameterized
    singleton nature is implemented through the ADSName.parse() method,
    which should be used to create ADSName instances.
    """
    __slots__ = ['_last_name', '_given_names', '_require_exact',
                 '_require_less_specific', '_require_more_specific',
                 '_allow_same_specific', '_original_name',
                 '_qualified_full_name', '_equality_cache', '_synonym',
                 '_allow_synonym']
    _last_name: str
    _given_names: Tuple[str]
    
    _require_exact: bool
    _require_less_specific: bool
    _require_more_specific: bool
    _allow_same_specific: bool
    _allow_synonym: bool
    
    _original_name: str
    _qualified_full_name: str
    _synonym: ADSName
    
    _equality_cache: {}
    
    @classmethod
    def parse(cls, last_name, *given_names, preserve=False):
        """Converts a string to an ADSName.
        
        Names may be given as a single string in the format "Last, First, M..."
        or as a number of strings following the order last, first, middle...
        
        Any number of given names are accepted after the last/family name.
        Except for the last name, single-letter names (followed by an optional
        period) are assumed to be initials.
        
        If preserve=True, case and punctuation marks are maintained, and the
        text is not converted to ASCII. An existing ADSName instance can be
        re-parsed with preserve=True. This will use the instance's
        original_name to restore information. Using preserve=True will, in
        general, break equality checking."""
        if preserve:
            if type(last_name) is ADSName:
                return ADSName(last_name.original_name,
                               preserve=preserve)
            return ADSName(last_name, *given_names, preserve=preserve)
        
        if type(last_name) == ADSName:
            return last_name
        
        key = (last_name, *given_names)
        try:
            return _name_cache[key]
        except KeyError:
            instance = ADSName(last_name, *given_names)
            _name_cache[key] = instance
            return instance
    
    def __init__(self, last_name, *given_names, preserve=False):
        """Do not call this method directly. Instead, use ADSName.parse()."""
        for name in (last_name, *given_names):
            if type(name) is not str:
                raise TypeError(f"Invalid type: {name} is {type(name)},"
                                " expected str")
        
        self._equality_cache = {}
        self._qualified_full_name = None
        self._synonym = None
        
        if len(given_names):
            self._original_name = f"{last_name}, {' '.join(given_names)}"
            self._last_name = last_name
            self._given_names = given_names
        else:
            # A complete name has been passed as a single string.
            self._original_name = last_name
            
            if not preserve:
                last_name = last_name.translate(_char_prefilter)
            
            # Let's break it into components
            parts = last_name.split(",", maxsplit=1)
            self._last_name = parts[0]
            
            # Check whether we only have a last name
            if len(parts) > 1 and len(parts[1]) > 0:
                self._given_names = parts[1].split()
            else:
                self._given_names = tuple()

        self._last_name = _multiple_spaces_pattern.sub(' ', self._last_name)

        if not preserve:
            self._last_name = unidecode(self._last_name).lower()
            self._given_names = tuple(unidecode(n).lower()
                                      for n in self._given_names)
        
        self._last_name = self._last_name.strip()
        self._given_names = tuple(n.strip() for n in self._given_names)
        
        if len(self._last_name) and self._last_name[0] in '<>=@':
            if self._last_name[0:2] in (">=", "=>"):
                self._require_more_specific = True
                self._allow_same_specific = True
                self._require_less_specific = False
                self._require_exact = False
                self._allow_synonym = True
            
            elif self._last_name[0:2] in ("<=", "=<"):
                self._require_more_specific = False
                self._allow_same_specific = True
                self._require_less_specific = True
                self._require_exact = False
                self._allow_synonym = True
            
            elif self._last_name[0] == ">":
                self._require_more_specific = True
                self._allow_same_specific = False
                self._require_less_specific = False
                self._require_exact = False
                self._allow_synonym = True
            
            elif self._last_name[0] == "<":
                self._require_more_specific = False
                self._allow_same_specific = False
                self._require_less_specific = True
                self._require_exact = False
                self._allow_synonym = True
            
            elif self._last_name[0] == "=":
                self._require_more_specific = False
                self._allow_same_specific = False
                self._require_less_specific = False
                self._require_exact = True
                self._allow_synonym = True
            
            elif self._last_name[0] == "@":
                self._require_more_specific = False
                self._allow_same_specific = True
                self._require_less_specific = False
                self._require_exact = False
                self._allow_synonym = False
            else:
                raise InvalidName("Unexpected modifiers")
        else:
            self._require_more_specific = False
            self._allow_same_specific = True
            self._require_less_specific = False
            self._require_exact = False
            self._allow_synonym = True
        
        # Remove any non-letter characters
        if not preserve:
            self._last_name = self._last_name.translate(_char_filter).strip()
            self._given_names = tuple(name.translate(_char_filter).strip()
                                      for name in self._given_names)
        self._given_names = tuple(gn for gn in self._given_names
                                  if gn != '')

        if self.last_name == '':
            raise InvalidName("Computed last name is empty")
        
        if not preserve and self._allow_synonym:
            try:
                self._synonym = _name_synonyms[self]
            except KeyError:
                pass
    
    def __eq__(self, other):
        """Checks equality by my understanding of ADS's name-matching rules.
        
        A layer of caching is implemented."""
        if type(other) is not ADSName:
            if type(other) is str:
                other = ADSName.parse(other)
            else:
                return NotImplemented
        
        if self is other and self._allow_same_specific:
            return True
        
        try:
            return self._equality_cache[other.qualified_full_name]
        except KeyError:
            pass
        
        if self._last_name != other._last_name:
            equal = False
        elif self._require_exact or other._require_exact:
            equal = self._given_names == other._given_names
        else:
            if not ADSName._name_data_are_consistent(
                    self._given_names, other._given_names):
                equal = False
            else:
                if ((self._require_more_specific
                     or other._require_less_specific)
                        and not other.is_more_specific_than(self)):
                    equal = (self._allow_same_specific
                             and other._allow_same_specific
                             and self._given_names == other._given_names)
                elif ((self._require_less_specific
                       or other._require_more_specific)
                        and not self.is_more_specific_than(other)):
                    equal = (self._allow_same_specific
                             and other._allow_same_specific
                             and self._given_names == other._given_names)
                else:
                    equal = True
        
        if self._allow_synonym and other._allow_synonym:
            if not equal and self._synonym is not None:
                # Inside self._synonym.__eq__,
                # `self._synonym == other._synonym` will be checked.
                equal = self._synonym == other
            if not equal and other._synonym is not None:
                equal = other._synonym == self
            
        self._equality_cache[other.qualified_full_name] = equal
        other._equality_cache[self.qualified_full_name] = equal
        return equal
    
    @classmethod
    def _name_data_are_consistent(cls,
                                  given_names1: Tuple[str],
                                  given_names2: Tuple[str]):
        """Accepts and compares for consistency two given name lists"""
        # If either is empty, they are consistent
        if len(given_names1) == 0 or len(given_names2) == 0:
            return True
        
        # Zip will end iteration when we reach the end of the shorter
        # input list, which is what we want. (A non-given name is consistent
        # with anything.)
        for gn1, gn2 in zip(given_names1, given_names2):
            if len(gn1) == 1:
                # gn1 is an initial. gn2 must start with that initial
                if not gn2.startswith(gn1):
                    return False
            elif len(gn2) == 1:
                # gn2 is an initial. gn1 must start with that initial
                if not gn1.startswith(gn2):
                    return False
            else:
                if gn1 != gn2:
                    return False
        return True
    
    def is_more_specific_than(self, other: ADSName):
        """Returns True if `self` is more specific than the given other name.
        
        A name is "more specific" if it includes every given name in the other
        name, and it either contains an additional given name or contains a
        spelled out given name where the other ADSName contained an initial.
        In other words, it must include all the information in the other name,
        plus some amount of additional information."""
        # If we have fewer given names, we can't be more specific.
        if len(self._given_names) < len(other._given_names):
            return False
        
        # Now we need to ensure we're consistent with the other name _and_
        # have something that counts as "more specific".
        # We count as more specific if we have more given names.
        more_specific = len(self._given_names) > len(other._given_names)
        
        # Now check the given names we have in common
        for s_gn, o_gn in zip(self._given_names, other._given_names):
            # Check if this is a spelled-out name replacing an initial
            if len(s_gn) > 1 and len(o_gn) == 1 and s_gn.startswith(o_gn):
                more_specific = True
            # If that's not the case, both ADSNames must have the same content
            # for this given name
            elif s_gn != o_gn:
                return False
        return more_specific
    
    def __str__(self):
        if self._synonym is not None:
            return (f'{self.qualified_full_name}'
                    f' (possibly AKA "{self._synonym}")')
        return self.qualified_full_name
    
    def __repr__(self):
        return self.__str__()
    
    def __hash__(self):
        return hash(repr(self))
    
    @property
    def level_of_detail(self):
        score = 0
        for gn in self._given_names:
            addition = 10 if len(gn) > 1 else 3
            score += addition
        return score
    
    def __add__(self, other):
        return str(self) + other
    
    def __radd__(self, other):
        return other + str(self)
    
    def __lt__(self, other):
        if type(other) == ADSName:
            other = other.full_name
        elif type(other) != str:
            raise NotImplemented
        return self.full_name < other
    
    def __gt__(self, other):
        if type(other) == ADSName:
            other = other.full_name
        elif type(other) != str:
            raise NotImplemented
        return self.full_name > other
    
    def __le__(self, other):
        if type(other) == ADSName:
            other = other.full_name
        elif type(other) != str:
            raise NotImplemented
        return self.full_name <= other
    
    def __ge__(self, other):
        if type(other) == ADSName:
            other = other.full_name
        elif type(other) != str:
            raise NotImplemented
        return self.full_name >= other
    
    @property
    def last_name(self):
        return self._last_name
    
    @property
    def given_names(self):
        return self._given_names
    
    @property
    def require_exact_match(self):
        return self._require_exact
    
    @property
    def require_less_specific(self):
        return self._require_less_specific
    
    @property
    def require_more_specific(self):
        return self._require_more_specific
    
    @property
    def allow_same_specific(self):
        return self._allow_same_specific
    
    @property
    def allow_synonym(self):
        return self._allow_synonym
    
    @property
    def excludes_self(self):
        return ((self._require_less_specific or self._require_more_specific)
                and not self._allow_same_specific)
    
    @property
    def synonym(self):
        return self._synonym
    
    @property
    def original_name(self):
        return self._original_name

    @property
    def bare_original_name(self):
        return self._strip_modifiers(self._original_name)

    @property
    def full_name(self):
        return self._strip_modifiers(self.qualified_full_name)
    
    def _strip_modifiers(self, name):
        while len(name) > 0 and name[0] in ('=', '<', '>', '@'):
            name = name[1:]
        return name
    
    @property
    def qualified_full_name(self):
        # This value is used in equality checking (a very frequent operation),
        # so it is memoized for speed. One goal here is to ensure consistent
        # formatting so that changes in input spacing or punctuation still
        # produce the same output. This is valuable for e.g. caching.
        if self._qualified_full_name is None:
            self._qualified_full_name = self.modifiers + self.last_name
            if len(self._given_names):
                self._qualified_full_name += ","
                for given_name in self._given_names:
                    self._qualified_full_name += " " + given_name
                    if len(given_name) == 1:
                        self._qualified_full_name += "."
                    
        return self._qualified_full_name
    
    def without_modifiers(self):
        if self.has_modifiers():
            return ADSName.parse(self.full_name)
        return self
    
    def convert_to_initials(self):
        return ADSName.parse(self.last_name,
                             *[gn[0] for gn in self.given_names])
    
    @property
    def modifiers(self):
        modifiers = ""
        if self._require_less_specific:
            if self._allow_same_specific:
                modifiers = '<='
            else:
                modifiers = '<'
        elif self._require_more_specific:
            if self._allow_same_specific:
                modifiers = '>='
            else:
                modifiers = '>'
        elif self._require_exact:
            modifiers = '='
        elif not self._allow_synonym:
            modifiers = '@'
        return modifiers
    
    def has_modifiers(self):
        return (self._require_exact
                or self._require_less_specific
                or self._require_more_specific
                or not self._allow_synonym)


def _parse_name_synonyms(synonym_list):
    for synonym in synonym_list:
        synonym.strip()
        if len(synonym) == 0 or synonym[0] == '#' or ';' not in synonym:
            continue
        names = synonym.split(";")
        names = [ADSName.parse('@' + name.strip()) for name in names]
        
        # We need to choose one variant to be canonical. Let's choose one with
        # the highest level of detail. As tie-breakers, choose variants with
        # longer last names, more given names, and longer overall names, all
        # of which likely indicate more/better information. The final
        # tie-breaker ends up being reverse-alphabetical order.
        intermed = [(name.level_of_detail,
                     len(name.last_name),
                     len(name.given_names),
                     len(name.full_name),
                     name)
                    for name in names]
        intermed.sort(reverse=True)
        canonical = intermed[0][-1]
        canonical = canonical.without_modifiers()
        variants = [i[-1] for i in intermed[1:]]
        # Our variants are sorted with the most detailed forms first. Our
        # NameAwareDict will end up with the less-detailed forms as keys.
        for variant in variants:
            _name_synonyms[variant] = canonical
    # Names in _name_synonyms now have invalid equality caches.
    keys = _name_synonyms.keys()
    values = _name_synonyms.values()
    for name in itertools.chain(keys, values):
        name._equality_cache.clear()


def _load_synonyms():
    for fname in local_config.name_synonym_lists:
        _parse_name_synonyms(open(fname).readlines())


_load_synonyms()


class InvalidName(RuntimeError):
    pass
