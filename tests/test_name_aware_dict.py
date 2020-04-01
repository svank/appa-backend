from unittest import TestCase

from ads_name import ADSName
from name_aware import NameAwareDict
from path_node import PathNode

equal_names = [ADSName.parse(n) for n in ("Murray, Stephen",
                                          "Murray, S.",
                                          "Murray, Stephen S")]
diff_names  = [ADSName.parse(n) for n in ("Murray, Eva",
                                          "Burray, Eva")]


class TestNameAwareDict(TestCase):
    
    def test_get_set_item(self):
        nad = NameAwareDict()
        
        node = PathNode(equal_names[0])
        nad[equal_names[0]] = node

        for name in diff_names:
            with self.assertRaises(KeyError):
                nad[name]
            nad[name] = PathNode(name)
        
        for name in equal_names:
            self.assertIs(node, nad[name])
            
        for name in diff_names:
            self.assertIsNot(node, nad[name])
        
        nad[equal_names[2]] = PathNode(equal_names[2])
        self.assertIsNot(node, nad[equal_names[0]])
    
    def test_del_item(self):
        nad = NameAwareDict()
        for name in diff_names:
            nad[name] = PathNode(name)
        
        self.assertIn(diff_names[0], nad)
        self.assertIn(diff_names[1], nad)
        del nad[diff_names[0]]
        self.assertNotIn(diff_names[0], nad)
        self.assertIn(diff_names[1], nad)
        del nad[diff_names[1]]
        self.assertNotIn(diff_names[1], nad)
    
    def test_keys(self):
        nad = NameAwareDict()
        for name in diff_names:
            nad[name] = PathNode(name)
        keys = nad.keys()
        self.assertIn(diff_names[0], keys)
        self.assertIn(diff_names[1], keys)
        
        for key in nad:
            self.assertIn(key, diff_names)
        
    
    def test_len(self):
        nad = NameAwareDict()

        for name in diff_names:
            nad[name] = PathNode(name)
        
        self.assertEqual(len(nad), len(diff_names))

        for name in equal_names:
            nad[name] = PathNode(name)
        
        self.assertEqual(len(nad), len(diff_names) + 1)
    
    def test_contains(self):
        nad = NameAwareDict()
        
        self.assertNotIn(equal_names[0], nad)
        
        nad[equal_names[0]] = PathNode(equal_names[0])
        
        for name in equal_names:
            self.assertIn(name, nad)
        
        for name in diff_names:
            self.assertNotIn(name, nad)
            
        for name in diff_names:
            nad[name] = PathNode(name)
        
        for name in diff_names:
            self.assertIn(name, nad)
