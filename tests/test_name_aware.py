from unittest import TestCase

from ads_name import ADSName
from name_aware import NameAwareDict, NameAwareSet
from path_node import PathNode

equal_names = [ADSName.parse(n) for n in ("Murray, S.",
                                          "Murray, Stephen",
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
    
    def test_with_specificity(self):
        nad = NameAwareDict()
        
        for name in diff_names:
            nad[name] = PathNode(name)
        
        for i, name in enumerate(equal_names):
            lt = ADSName.parse("<" + str(name))
            lte = ADSName.parse("<=" + str(name))
            gt = ADSName.parse(">" + str(name))
            gte = ADSName.parse(">=" + str(name))
            ex = ADSName.parse("=" + str(name))
            
            if i == 0:
                self.assertNotIn(lt, nad)
                self.assertNotIn(lte, nad)
            else:
                self.assertIn(lt, nad)
                self.assertIn(lte, nad)
            self.assertNotIn(gt, nad)
            self.assertNotIn(gte, nad)
            self.assertNotIn(ex, nad)
            
            # Node "Last, First" will match and overwrite an existing entry
            # for "Last, F"
            nad[name] = PathNode(name)
            
            self.assertNotIn(lt, nad)
            self.assertIn(gte, nad)
            self.assertIn(lte, nad)
            self.assertNotIn(gt, nad)
            self.assertIn(ex, nad)
        
        nad = NameAwareDict()
        
        for name in diff_names:
            nad[name] = PathNode(name)
        
        for i, name in enumerate(equal_names[::-1]):
            lt = ADSName.parse("<" + str(name))
            lte = ADSName.parse("<=" + str(name))
            gt = ADSName.parse(">" + str(name))
            gte = ADSName.parse(">=" + str(name))
            ex = ADSName.parse("=" + str(name))
            
            if i == 0:
                self.assertNotIn(gt, nad)
                self.assertNotIn(gte, nad)
            else:
                self.assertIn(gt, nad)
                self.assertIn(gte, nad)
            self.assertNotIn(lt, nad)
            self.assertNotIn(lte, nad)
            self.assertNotIn(ex, nad)
            
            # Node "Last, First" will match and overwrite an existing entry
            # for "Last, F"
            nad[name] = PathNode(name)
            
            self.assertNotIn(lt, nad)
            self.assertIn(gte, nad)
            self.assertIn(lte, nad)
            self.assertNotIn(gt, nad)
            self.assertIn(ex, nad)
            


class TestNameAwareSet(TestCase):
    def test_add(self):
        nas = NameAwareSet()
        
        nas.add(equal_names[0])

        for name in diff_names:
            self.assertNotIn(name, nas)
            nas.add(name)
        
        for name in equal_names:
            self.assertIn(name, nas)
            
        for name in diff_names:
            self.assertIn(name, nas)
    
    def test_len(self):
        nad = NameAwareSet()

        for name in diff_names:
            nad.add(name)
        
        self.assertEqual(len(nad), len(diff_names))

        for name in equal_names:
            nad.add(name)
        
        self.assertEqual(len(nad), len(diff_names) + 1)
