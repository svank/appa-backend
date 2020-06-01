from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Union

import ads_name


class ContainerWithName:
    __slots__ = ("value", "name")
    
    def __init__(self, name: ads_name.ADSName, value):
        self.name = name
        self.value = value


Name = Union[str, "ads_name.ADSName"]


class NameAwareDict:
    items_by_last_name: Dict[str, List[ContainerWithName]]
    
    def __init__(self):
        self.clear()
    
    def __getitem__(self, key: Name):
        if type(key) is str:
            key = ads_name.ADSName.parse(key)
        items = self.items_by_last_name[key.last_name]
        for item in items:
            if item.name == key:
                return item.value
        raise KeyError(key)
    
    def __setitem__(self, key: Name, value):
        if type(key) is str:
            key = ads_name.ADSName.parse(key)
        container = ContainerWithName(key, value)
        items = self.items_by_last_name[key.last_name]
        for i, item in enumerate(items):
            if item.name == key:
                items[i] = container
                return
        items.append(container)
    
    def __delitem__(self, key):
        if type(key) == str:
            key = ads_name.ADSName.parse(key)
        items = self.items_by_last_name[key.last_name]
        for i, item in enumerate(items):
            if item.name == key:
                items.pop(i)
                if len(items) == 0:
                    del self.items_by_last_name[key.last_name]
                return
    
    def __len__(self):
        count = 0
        for items in self.items_by_last_name.values():
            count += len(items)
        return count
    
    def __contains__(self, key: Name):
        if type(key) is str:
            key = ads_name.ADSName.parse(key)
        
        items = self.items_by_last_name[key.last_name]
        
        for item in items:
            if item.name == key:
                return True
        return False
    
    def __str__(self):
        return str(self.items_by_last_name)
    
    def __repr__(self):
        return repr(self.items_by_last_name)
    
    def __iter__(self):
        for items in self.items_by_last_name.values():
            for item in items:
                yield item.name
    
    def keys(self):
        return list(self)
    
    def values(self):
        values = []
        for items in self.items_by_last_name.values():
            for item in items:
                values.append(item.value)
        return values
    
    def items(self):
        return zip(self.keys(), self.values())
    
    def clear(self):
        self.items_by_last_name = defaultdict(list)


class NameAwareSet:
    def __init__(self):
        self._dict = NameAwareDict()
    
    def add(self, item: Name):
        self._dict[item] = item
    
    def __iter__(self):
        return iter(self._dict)
    
    def __len__(self):
        return len(self._dict)
    
    def __contains__(self, item):
        return item in self._dict

    def __str__(self):
        return str(self.values())

    def __repr__(self):
        return repr(self.values())
    
    def values(self):
        return self._dict.values()
