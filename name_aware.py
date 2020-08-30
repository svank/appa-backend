from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Union

import ads_name


class ContainerWithName:
    __slots__ = ("value", "name", "last_names_used")
    
    def __init__(self, name: ads_name.ADSName, value):
        self.name = name
        self.value = value
        self.last_names_used = [name.last_name]
    
    def __hash__(self):
        return hash(self.name)


Name = Union[str, "ads_name.ADSName"]


class NameAwareDict:
    items_by_last_name: Dict[str, List[ContainerWithName]]
    
    def __init__(self):
        self.clear()
    
    def __getitem__(self, key: Name, return_container=False):
        """
        Attempts to find a record under the given name. If not found,
        attempts to find a record under the name's synonym, if set.
        """
        if type(key) is str:
            key = ads_name.ADSName.parse(key)
        items = self.items_by_last_name[key.last_name]
        for item in items:
            if item.name == key:
                container = item
                break
        else:
            if (key.synonym is not None
                    and key.synonym.last_name != key.last_name):
                container = self.__getitem__(key.synonym, True)
                if container.name != key:
                    raise KeyError(key)
            else:
                raise KeyError(key)
        
        if return_container:
            return container
        else:
            return container.value
    
    def __setitem__(self, key: Name, value):
        """
        Stores data under the given name. If the name has a synonym with a
        different last name, the same container is stored under the synonym's
        last name. The container only ever stores the name that was last used
        to store data, but remains in all items_by_last_name lists it has been
        added to.
        Cases:
         - Store and look up using same name. Easy.
         - Store under alt or canonical name which have the exact same last
           name. Lookup under canonical or alt name. Lookup succeeds, same as
           when given names vary.
         - Store under canonical name. Look up under alt name. Lookup uses the
           canonical synonym if no hits on alt name, and succeeds.
         - Store under alt name. Data is also stored under canonical name.
           Look up under canonical name. Lookup succeeds.
         - As above, but look up under a different alt name. Lookup attempts
           with the canonical name and succeeds.
         - Store under canonical name. Update using alt name. The container is
           found using the canonical name and is entered under the alt name.
           Lookups succeed as above.
         - Store under alt name. Update using canonical name. The container is
           found using the canonical name and updated.
           Lookups succeed as above.
         - Store under alt name. Update using a different alt name. The
           container is found using the shared canonical name and entered under
           the new alt name. Lookups succeed as above.
        """
        if type(key) is str:
            key = ads_name.ADSName.parse(key)
        
        container = None
        container_filed_under_self = False
        container_filed_under_synonym = False

        # Search for an existing container under the given name
        items = self.items_by_last_name[key.last_name]
        for item in items:
            if item.name == key:
                container = item
                container_filed_under_self = True
                break

        # Search for an existing container under a synonym
        handle_synonym = (key.synonym is not None
                          and key.synonym.last_name != key.last_name)
        if container is None and handle_synonym:
            for item in self.items_by_last_name[key.synonym.last_name]:
                if item.name == key.synonym:
                    container = item
                    container_filed_under_synonym = True
                    break
        
        if container is None:
            # Create a new container if none was found
            container = ContainerWithName(key, value)
        else:
            # Update the found container
            container.name = key
            container.value = value
        
        if not container_filed_under_self:
            items.append(container)
            if handle_synonym:
                # If we're here, this container was found under a synonym
                # with a different last name
                container.last_names_used.append(key.last_name)
        
        if not container_filed_under_synonym and handle_synonym:
            self.items_by_last_name[key.synonym.last_name].append(container)
            container.last_names_used.append(key.synonym.last_name)
    
    def __delitem__(self, key):
        if type(key) is str:
            key = ads_name.ADSName.parse(key)
        
        container = self.__getitem__(key, True)
        for last_name in container.last_names_used:
            items = self.items_by_last_name[last_name]
            for i, item in enumerate(items):
                if item is container:
                    if len(items) == 1:
                        del self.items_by_last_name[last_name]
                    else:
                        items.pop(i)
                    break
    
    def __len__(self):
        containers = set()
        for items in self.items_by_last_name.values():
            containers.update(items)
        return len(containers)
    
    def __contains__(self, key: Name):
        if type(key) is str:
            key = ads_name.ADSName.parse(key)
        
        for item in self.items_by_last_name[key.last_name]:
            if item.name == key:
                return True

        if key.synonym is not None and key.synonym.last_name != key.last_name:
            return key.synonym in self
        
        return False
    
    def __str__(self):
        return str(self.items_by_last_name)
    
    def __repr__(self):
        return repr(self.items_by_last_name)
    
    def _iter_all(self):
        items_seen = set()
        for items in self.items_by_last_name.values():
            for item in items:
                if item not in items_seen:
                    items_seen.add(item)
                    yield item.name, item.value
    
    def __iter__(self):
        for key, value in self._iter_all():
            yield key
    
    def keys(self):
        # Simply turns output of __iter__ into a list
        return tuple(self)
    
    def values(self):
        return tuple(v for k, v in self._iter_all())
    
    def items(self):
        return tuple(self._iter_all())
    
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
