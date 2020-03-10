from __future__ import annotations


class ADSName:
    """Handles names

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
    """
    last_name: str
    first_name: str = None
    first_initial: str = None
    middle_name: str = None
    middle_initial: str = None
    exact: bool = False
    exclude_less_specific: bool = False
    exclude_more_specific: bool = False
    original_name: str
    
    def __init__(self, last_name, first_name=None, middle_name=None):
        if type(last_name) == ADSName:
            self._copy_from(last_name)
            return
        elif type(last_name) != str:
            raise TypeError("Invalid type for name: " + str(type(last_name)))
        if first_name is None:
            if middle_name is not None:
                raise ValueError(
                    "Cannot provide middle name without first name")
            # A complete name has been passed as a single string.
            self.original_name = last_name
            # Let's break it into components
            parts = last_name.split(",", maxsplit=1)
            self.last_name = parts[0].lower()
            
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
            self.original_name = f"{last_name}, {first_name}"
            if middle_name is not None:
                self.original_name += f" {middle_name}"
            self.last_name = last_name.lower()
            self._set_first_name_or_initial(first_name)
            if middle_name is not None:
                self._set_middle_name_or_initial(middle_name)
        
        if len(self.last_name) > 1:
            if self.last_name.startswith("="):
                self.exact = True
                self.last_name = self.last_name[1:]
            elif self.last_name.startswith("<"):
                self.exclude_more_specific = True
                self.last_name = self.last_name[1:]
            elif self.last_name.startswith(">"):
                self.exclude_less_specific = True
                self.last_name = self.last_name[1:]
    
    def _set_first_name_or_initial(self, first_name):
        if (len(first_name) == 1 or
                (len(first_name) == 2 and first_name[-1] == '.')):
            self.first_initial = first_name[0].lower()
        else:
            self.first_name = first_name.lower()
    
    def _set_middle_name_or_initial(self, middle_name):
        if (len(middle_name) == 1 or
                (len(middle_name) == 2 and middle_name[-1] == '.')):
            self.middle_initial = middle_name[0].lower()
        else:
            self.middle_name = middle_name.lower()
    
    def _get_first_name_data(self):
        return self.first_name, self.first_initial
    
    def _get_middle_name_data(self):
        return self.middle_name, self.middle_initial
    
    def __eq__(self, other):
        """Checks equality by my understanding of ADS's name-matching rules"""
        if type(other) is str:
            other = ADSName(other)
        if type(other) != ADSName:
            return False
        
        if self.exact or other.exact:
            return (
                self.last_name == other.last_name and
                self.first_initial == other.first_initial and
                self.first_name == other.first_name and
                self.middle_initial == other.middle_initial and
                self.middle_name == other.middle_name
            )
        
        if ((self.exclude_more_specific or other.exclude_less_specific)
                and self.level_of_detail < other.level_of_detail):
            return False
        
        if ((self.exclude_less_specific or other.exclude_more_specific)
                and self.level_of_detail > other.level_of_detail):
            return False
        
        return (
                self.last_name == other.last_name
                and
                ADSName._name_data_are_equal(
                    self._get_first_name_data(),
                    other._get_first_name_data())
                and
                ADSName._name_data_are_equal(
                    self._get_middle_name_data(),
                    other._get_middle_name_data()
                )
        )
    
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
        self.last_name = src.last_name
        self.first_name = src.first_name
        self.first_initial = src.first_initial
        self.middle_name = src.middle_name
        self.middle_initial = src.middle_initial
        self.original_name = src.original_name
        self.exact = src.exact
        self.exclude_more_specific = src.exclude_more_specific
        self.exclude_less_specific = src.exclude_less_specific
    
    @property
    def bare_original_name(self):
        if self.original_name[0] in ('=', '<', '>'):
            return self.original_name[1:]
        return self.original_name
    
    @property
    def full_name(self):
        output = self.last_name
    
        if self.first_name is not None:
            output += f", {self.first_name}"
        if self.first_initial is not None:
            output += f", {self.first_initial}."
    
        if self.middle_name is not None:
            output += f" {self.middle_name}"
        if self.middle_initial is not None:
            output += f" {self.middle_initial}."
            
        return output
    
    def __str__(self):
        output = self.full_name
        if self.exclude_less_specific:
            output = '>' + output
        if self.exclude_more_specific:
            output = '<' + output
        if self.exact:
            output = '=' + output
        return output
    
    def __repr__(self):
        return self.__str__()
    
    def __hash__(self):
        return hash(repr(self))
    
    @property
    def level_of_detail(self):
        return (
            (100 if self.last_name is not None else 0)
            + (20 if self.first_name is not None else 0)
            + (10 if self.first_initial is not None else 0)
            + (2 if self.middle_name is not None else 0)
            + (1 if self.middle_initial is not None else 0)
        )
    
    def __add__(self, other):
        return str(self) + other
    
    def __radd__(self, other):
        return other + str(self)