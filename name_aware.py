from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Union, Generic, TypeVar

from ads_name import ADSName
from author_record import AuthorRecord
from path_node import PathNode

Name = Union[str, ADSName]
HasName = TypeVar("HasName", PathNode, AuthorRecord)


class NameAwareDict(Generic[HasName]):
    items_by_last_name: Dict[str, List[HasName]]
    
    def __init__(self):
        self.items_by_last_name = defaultdict(list)
    
    def __getitem__(self, key: Name) -> HasName:
        if type(key) is str:
            key = ADSName.parse(key)
        items = self.items_by_last_name[key.last_name]
        for item in items:
            if item.name == key:
                return item
        raise KeyError(key)
    
    def __setitem__(self, key: Name, value: HasName):
        if type(key) is str:
            key = ADSName.parse(key)
        items = self.items_by_last_name[key.last_name]
        for i, item in enumerate(items):
            if item.name == key:
                items[i] = value
                return
        items.append(value)
    
    def __delitem__(self, key):
        if type(key) == str:
            key = ADSName.parse(key)
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
            key = ADSName.parse(key)
        
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
        keys = []
        for items in self.items_by_last_name.values():
            for item in items:
                keys.append(item.name)
        return keys
    
    def values(self):
        values = []
        for items in self.items_by_last_name.values():
            for item in items:
                values.append(item)
        return values
    
    def items(self):
        return zip(self.keys(), self.values())


class NameAwareSet:
    def __init__(self):
        self._dict = NameAwareDict()
    
    def add(self, item: Name):
        if type(item) is str:
            item = ADSName.parse(item)
        self._dict[item] = PathNode(name=item)
    
    def __iter__(self):
        return iter(self._dict)
    
    def __len__(self):
        return len(self._dict)
    
    def __contains__(self, item):
        return item in self._dict

    def __str__(self):
        return str(self._dict.keys())

    def __repr__(self):
        return repr(self._dict.keys())
