from __future__ import annotations


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
    _first_name: str = None
    _first_initial: str = None
    _middle_name: str = None
    _middle_initial: str = None
    
    _exact: bool = False
    _exclude_less_specific: bool = False
    _exclude_more_specific: bool = False
    
    _original_name: str
    _full_name: str
    _qualified_full_name: str
    
    _equality_cache: {}
    _name_cache = {}
    
    @classmethod
    def parse(cls, last_name, first_name=None, middle_name=None):
        if type(last_name) == ADSName:
            return last_name
        key = (last_name, first_name, middle_name)
        if key not in cls._name_cache:
            instance = ADSName(last_name, first_name, middle_name)
            cls._name_cache[key] = instance
            return instance
        return cls._name_cache[key]
    
    def __init__(self, last_name, first_name=None, middle_name=None):
        """Do not call this method directly. Instead, use ADSName.parse()."""
        if type(last_name) != str:
            raise TypeError("Invalid type for name: " + str(type(last_name)))
        
        self._equality_cache = {}
        
        if first_name is None:
            if middle_name is not None:
                raise ValueError(
                    "Cannot provide middle name without first name")
            # A complete name has been passed as a single string.
            self._original_name = last_name
            # Let's break it into components
            parts = last_name.split(",", maxsplit=1)
            self._last_name = parts[0].lower()
            
            # Check whether we only have a last name
            if len(parts) > 1 and len(parts[1]) > 0:
                given_parts = parts[1].split(maxsplit=1)
                first = given_parts[0]
                self._set_first_name_or_initial(first)
                
                # Check whether we have a middle name
                if len(given_parts) > 1:
                    middle = given_parts[1]
                    self._set_middle_name_or_initial(middle)
        else:
            self._original_name = f"{last_name}, {first_name}"
            if middle_name is not None:
                self._original_name += f" {middle_name}"
            self._last_name = last_name.lower()
            self._set_first_name_or_initial(first_name)
            if middle_name is not None:
                self._set_middle_name_or_initial(middle_name)
        
        if len(self._last_name) > 1:
            if self._last_name.startswith("="):
                self._exact = True
                self._last_name = self._last_name[1:]
            elif self._last_name.startswith("<"):
                self._exclude_more_specific = True
                self._last_name = self._last_name[1:]
            elif self._last_name.startswith(">"):
                self._exclude_less_specific = True
                self._last_name = self._last_name[1:]
        
        # This value is used in equality checking (a very frequent operation),
        # so it is memoized for speed
        self._qualified_full_name = self._original_name.lower()
    
    def _set_first_name_or_initial(self, first_name):
        if (len(first_name) == 1 or
                (len(first_name) == 2 and first_name[-1] == '.')):
            self._first_initial = first_name[0].lower()
        else:
            self._first_name = first_name.lower()
    
    def _set_middle_name_or_initial(self, middle_name):
        if (len(middle_name) == 1 or
                (len(middle_name) == 2 and middle_name[-1] == '.')):
            self._middle_initial = middle_name[0].lower()
        else:
            self._middle_name = middle_name.lower()
    
    def __eq__(self, other):
        """Checks equality by my understanding of ADS's name-matching rules.
        
        A layer of caching is implemented."""
        if type(other) is str:
            other = ADSName.parse(other)
        elif type(other) is not ADSName:
            return NotImplemented
        
        if self is other:
            return True
        
        try:
            return self._equality_cache[other._qualified_full_name]
        except KeyError:
            pass

        if self._exact or other._exact:
            equal = (
                self._last_name == other._last_name and
                self._first_initial == other._first_initial and
                self._first_name == other._first_name and
                self._middle_initial == other._middle_initial and
                self._middle_name == other._middle_name
            )
        
        elif ((self._exclude_more_specific or other._exclude_less_specific)
                and self.level_of_detail < other.level_of_detail):
            equal = False
        
        elif ((self._exclude_less_specific or other._exclude_more_specific)
                and self.level_of_detail > other.level_of_detail):
            equal = False
        
        else:
            equal = (
                self._last_name == other._last_name
                and
                ADSName._name_data_are_equal(
                    (self._first_name, self._first_initial),
                    (other._first_name, other._first_initial)
                )
                and
                ADSName._name_data_are_equal(
                    (self._middle_name, self._middle_initial),
                    (other._middle_name, other._middle_initial)
                )
            )
        
        self._equality_cache[other._qualified_full_name] = equal
        other._equality_cache[self._qualified_full_name] = equal
        return equal
    
    @classmethod
    def _name_data_are_equal(cls, nd1, nd2):
        """Accepts and compares two (name, initial) tuples"""
        # If either is empty...
        if nd1 == (None, None) or nd2 == (None, None):
            return True
        
        # If both have a name...
        if nd1[0] is not None and nd2[0] is not None:
            return nd1[0] == nd2[0]
        
        # If both have an initial...
        if nd1[1] is not None and nd2[1] is not None:
            return nd1[1] == nd2[1]
        
        # At this point, one is a name and one is an initial
        name = nd1[0] if nd1[0] is not None else nd2[0]
        initial = nd1[1] if nd1[1] is not None else nd2[1]
        return name.startswith(initial)
    
    def _copy_from(self, src: ADSName):
        self._last_name = src._last_name
        self._first_name = src._first_name
        self._first_initial = src._first_initial
        self._middle_name = src._middle_name
        self._middle_initial = src._middle_initial
        self._original_name = src._original_name
        self._exact = src._exact
        self._exclude_more_specific = src._exclude_more_specific
        self._exclude_less_specific = src._exclude_less_specific
    
    def __str__(self):
        return self.qualified_full_name
    
    def __repr__(self):
        return self.__str__()
    
    def __hash__(self):
        return hash(repr(self))
    
    @property
    def level_of_detail(self):
        return (
            (100 if self._last_name is not None else 0)
            + (20 if self._first_name is not None else 0)
            + (10 if self._first_initial is not None else 0)
            + (2 if self._middle_name is not None else 0)
            + (1 if self._middle_initial is not None else 0)
        )
    
    def __add__(self, other):
        return str(self) + other
    
    def __radd__(self, other):
        return other + str(self)
    
    @property
    def last_name(self):
        return self._last_name
    
    @property
    def first_name(self):
        return self._first_name
    
    @property
    def first_initial(self):
        return self._first_initial
    
    @property
    def middle_name(self):
        return self._middle_name
    
    @property
    def middle_initial(self):
        return self._middle_initial
    
    @property
    def exact(self):
        return self._exact
    
    @property
    def exclude_less_specific(self):
        return self._exclude_less_specific
    
    @property
    def exclude_more_specific(self):
        return self._exclude_more_specific
    
    @property
    def original_name(self):
        return self._original_name

    @property
    def bare_original_name(self):
        if self._original_name[0] in ('=', '<', '>'):
            return self._original_name[1:]
        return self._original_name

    @property
    def full_name(self):
        output = self._qualified_full_name
        if output[0] in ('=', '<', '>'):
            return output[1:]
        return output
        
    
    @property
    def qualified_full_name(self):
        return self._qualified_full_name