from __future__ import annotations

import itertools
from typing import Tuple


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
    _last_name: str
    _given_names: Tuple[str]
    
    _require_exact: bool = False
    _require_less_specific: bool = False
    _require_more_specific: bool = False
    _allow_same_specific: bool = True
    
    _original_name: str
    _full_name: str
    _qualified_full_name: str
    
    _equality_cache: {}
    _name_cache = {}
    
    @classmethod
    def parse(cls, last_name, *given_names):
        """Converts a string to an ADSName.
        
        Names may be given as a single string in the format "Last, First, M..."
        or as a number of strings following the order last, first, middle...
        
        Any number of given names are accepted after the last/family name.
        Except for the last name, single-letter names (followed by an optional
        period) are assumed to be initials."""
        if type(last_name) == ADSName:
            return last_name
        key = (last_name, *given_names)
        if key not in cls._name_cache:
            instance = ADSName(last_name, *given_names)
            cls._name_cache[key] = instance
            return instance
        return cls._name_cache[key]
    
    def __init__(self, last_name, *given_names):
        """Do not call this method directly. Instead, use ADSName.parse()."""
        for name in itertools.chain([last_name], given_names):
            if type(name) != str:
                raise TypeError(f"Invalid type: {name} is {type(name)},"
                                " expected str")
        
        self._equality_cache = {}
        
        if len(given_names):
            self._original_name = f"{last_name}, {' '.join(given_names)}"
            self._last_name = last_name
            self._given_names = given_names
        else:
            # A complete name has been passed as a single string.
            self._original_name = last_name
            # Let's break it into components
            parts = last_name.split(",", maxsplit=1)
            self._last_name = parts[0]
            
            # Check whether we only have a last name
            if len(parts) > 1 and len(parts[1]) > 0:
                self._given_names = parts[1].split()
            else:
                self._given_names = tuple()
        
        self._last_name = self._last_name.lower()
        self._given_names = tuple(n[0].lower() if len(n.rstrip('.')) == 1
                                  else n.lower()
                                  for n in self._given_names)
        
        modifier_prefix = ""
        if self._last_name[0:2] in (">=", "=>"):
            self._require_more_specific = True
            self._allow_same_specific = True
            self._last_name = self._last_name[2:]
            modifier_prefix = ">="
        elif self._last_name[0:2] in ("<=", "=<"):
            self._require_less_specific = True
            self._allow_same_specific = True
            self._last_name = self._last_name[2:]
            modifier_prefix = "<="
        elif self._last_name.startswith(">"):
            self._require_more_specific = True
            self._allow_same_specific = False
            self._last_name = self._last_name[1:]
            modifier_prefix = ">"
        elif self._last_name.startswith("<"):
            self._require_less_specific = True
            self._allow_same_specific = False
            self._last_name = self._last_name[1:]
            modifier_prefix = "<"
        elif self._last_name.startswith("="):
            self._require_exact = True
            self._last_name = self._last_name[1:]
            modifier_prefix = "="
        
        # This value is used in equality checking (a very frequent operation),
        # so it is memoized for speed. One goal here is to ensure consistent
        # formatting so that changes in input spacing or punctuation still
        # produce the same output. This is valuable for e.g. caching.
        self._qualified_full_name = self.last_name
        if len(self._given_names):
            self._qualified_full_name += ","
            for given_name in self._given_names:
                self._qualified_full_name += " " + given_name
                if len(given_name) == 1:
                    self._qualified_full_name += "."
        
        # We *could* just save _qualified_full_name before stripping the
        # modifiers from the last name, but we need to ensure the modifiers
        # show up in a consistent order, so we re-add them here in a
        # deterministic way.
        self._qualified_full_name = modifier_prefix + self._qualified_full_name
    
    def __eq__(self, other):
        """Checks equality by my understanding of ADS's name-matching rules.
        
        A layer of caching is implemented."""
        if type(other) is str:
            other = ADSName.parse(other)
        elif type(other) is not ADSName:
            return NotImplemented
        
        if (self is other
                and self._allow_same_specific
                and other._allow_same_specific):
            return True
        
        try:
            return self._equality_cache[other._qualified_full_name]
        except KeyError:
            pass
        
        exactly_equal = (self._last_name == other._last_name
                         and self._given_names == other._given_names)
        
        if self._require_exact or other._require_exact:
            equal = exactly_equal
        elif exactly_equal:
            equal = (self._allow_same_specific
                     and other._allow_same_specific)
        else:
            consistent = (
                self._last_name == other._last_name
                and
                ADSName._name_data_are_consistent(
                    self._given_names, other._given_names)
            )
            if not consistent:
                equal = False
            else:
                if ((self._require_more_specific
                     or other._require_less_specific)
                        and not other.is_more_specific_than(self)):
                    equal = False
                elif ((self._require_less_specific
                       or other._require_more_specific)
                        and not self.is_more_specific_than(other)):
                    equal = False
                else:
                    equal = True
        
        self._equality_cache[other._qualified_full_name] = equal
        other._equality_cache[self._qualified_full_name] = equal
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
    def excludes_self(self):
        return ((self._require_less_specific or self._require_more_specific)
                and not self._allow_same_specific)
    
    @property
    def original_name(self):
        return self._original_name

    @property
    def bare_original_name(self):
        return self._strip_modifiers(self._original_name)

    @property
    def full_name(self):
        return self._strip_modifiers(self._qualified_full_name)
    
    def _strip_modifiers(self, name):
        while len(name) > 0 and name[0] in ('=', '<', '>'):
            name = name[1:]
        return name
    
    @property
    def qualified_full_name(self):
        return self._qualified_full_name
