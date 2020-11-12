from unittest import TestCase

import names.ads_name as ads_name
from names.ads_name import ADSName
from names.name_aware import NameAwareDict, NameAwareSet
from path_node import PathNode

equal_names_str = ["Murray, S.",
                   "Murray, Stephen",
                   "Murray, Stephen S",
                   "Murray, Stephen Steve"]
equal_names = [ADSName.parse(n) for n in equal_names_str]

diff_names_str = ["Murray, Eva",
                  "Burray, Eva",
                  "Murray, Eric"]
diff_names = [ADSName.parse(n) for n in diff_names_str]


class TestNameAwareDict(TestCase):
    def test_get_set_item(self):
        nad = NameAwareDict()

        with self.assertRaises(KeyError):
            nad[diff_names[0]]
        with self.assertRaises(KeyError):
            nad[diff_names[1]]
        
        node = PathNode(equal_names[0])
        nad[equal_names[0]] = node
        
        diff_nodes = []
        for name in diff_names:
            with self.assertRaises(KeyError):
                nad[name]
            new_node = PathNode(name)
            nad[name] = new_node
            diff_nodes.append(new_node)
        
        for name in equal_names:
            self.assertIs(node, nad[name])
            
        for name, target_node in zip(diff_names, diff_nodes):
            self.assertIsNot(node, nad[name])
            self.assertIs(target_node, nad[name])
        
        new_node = PathNode(equal_names[2])
        nad[equal_names[2]] = new_node
        for name in equal_names:
            self.assertIsNot(node, nad[name])
            self.assertIs(new_node, nad[name])
    
    def test_del_item(self):
        nad = NameAwareDict()
        for name in diff_names:
            nad[name] = PathNode(name)
        
        self.assertIn(diff_names[0], nad)
        self.assertIn(diff_names[1], nad)
        self.assertIn(diff_names[2], nad)
        del nad[diff_names[0]]
        self.assertNotIn(diff_names[0], nad)
        self.assertIn(diff_names[1], nad)
        self.assertIn(diff_names[2], nad)
        del nad[diff_names[1]]
        self.assertNotIn(diff_names[1], nad)
        self.assertIn(diff_names[2], nad)
        del nad[diff_names[2]]
        self.assertNotIn(diff_names[2], nad)
        
        nad[equal_names[0]] = PathNode(equal_names[0])
        del nad[equal_names[1]]
        for name in equal_names:
            self.assertNotIn(name, nad)
            with self.assertRaises(KeyError):
                nad[name]
    
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
    
    def test_with_synonyms(self):
        synonyms = [
            "test_synAA; test_synAB",
            "test_synB, a; test_synB, b",
            "test_synCA, q; test_synCB, q",
            "test_synD, a; test_synD, b c",
            "test_synEB, b; test_synEA, a",
            "test_synFA, a b c d; test_synFB, a",
            "test_synGA, a b c d; test_synGB, a; test_synGC, b"
        ]
        # Hack: inject test synonyms
        ads_name._name_cache.clear()
        ads_name._parse_name_synonyms(synonyms)
        
        for synonym in synonyms:
            names = synonym.split(';')
            
            # The second copy is for the deletion tests later
            nad = NameAwareDict()
            nad2 = NameAwareDict()
            for i, name in enumerate(names):
                nad[name] = i
                nad2[name] = i
            
            # Do the insertion in both orders, to ensure we try both
            # "canonical first" and "canonical last"
            nad_rev = NameAwareDict()
            nad_rev2 = NameAwareDict()
            for i, name in enumerate(reversed(names)):
                nad_rev[name] = i
                nad_rev2[name] = i

            # Ensure that, after inserting under one form and updating under
            # the other form, we can get the latest value from either form.
            for name in names:
                self.assertEqual(nad[name], i)
                self.assertEqual(nad_rev[name], i)
            
            # Check other misc methods
            for name in names:
                self.assertIn(name, nad)
                self.assertIn(name, nad_rev)
            
            self.assertEqual(len(nad), 1)
            self.assertEqual(len(nad_rev), 1)
            
            self.assertEqual(nad.keys(), (ADSName.parse(names[-1]),))
            self.assertEqual(nad_rev.keys(), (ADSName.parse(names[0]),))
            
            self.assertEqual(nad.values(), (i,))
            self.assertEqual(nad_rev.values(), (i,))
            
            # Ensure that deleting one form deletes them all.
            del nad[names[0]]
            self.assertEqual(len(nad), 0)
            for name in names:
                self.assertNotIn(name, nad)
            
            del nad2[names[1]]
            self.assertEqual(len(nad2), 0)
            for name in names:
                self.assertNotIn(name, nad2)
            
            del nad_rev[names[0]]
            self.assertEqual(len(nad_rev), 0)
            for name in names:
                self.assertNotIn(name, nad_rev)
            
            del nad_rev2[names[1]]
            self.assertEqual(len(nad_rev2), 0)
            for name in names:
                self.assertNotIn(name, nad_rev2)
        
        # Verify functionality with '@' modifier
        for synonym in synonyms:
            names_orig = synonym.split(';')
            
            for names in [names_orig, list(reversed(names_orig))]:
                # We'll insert under one name, then verify we can't access
                # or delete under the other
                nad1 = NameAwareDict()
                nad2 = NameAwareDict()
                nad3 = NameAwareDict()
                nad4 = NameAwareDict()
                
                nad1[names[0]] = 1
                nad2[names[-1]] = 1
                nad3['@' + names[0]] = 1
                nad4['@' + names[-1]] = 1
                
                with self.assertRaises(KeyError):
                    nad1['@' + names[-1]]
                with self.assertRaises(KeyError):
                    nad2['@' + names[0]]
                with self.assertRaises(KeyError):
                    nad3[names[-1]]
                with self.assertRaises(KeyError):
                    nad4[names[0]]
                
                # I don't think it's worth it to test modification because
                # it's hard to define how it should work. If we store under
                # 'name' which has 'name2' as a synonym, we get the same
                # value for 'name' and 'name2'. If we then store under
                # '@name2', what should we get when retrieving as 'name2'?
                # If we then store again under 'name', what should we get
                # for 'name2'? Or for '@name2'?
                
                # nad1['@' + names[-1]] = 2
                # self.assertEqual(nad1[names[0]], 1)
                # nad1['@' + names[0]] = 2
                # self.assertEqual(nad1[names[-1]], 1)
                # nad1[names[-1]] = 2
                # self.assertEqual('@' + nad1[names[0]], 1)
                # nad1[names[0]] = 2
                # self.assertEqual('@' + nad1[names[-1]], 1)
                
                with self.assertRaises(KeyError):
                    del nad1['@' + names[-1]]
                with self.assertRaises(KeyError):
                    del nad2['@' + names[0]]
                with self.assertRaises(KeyError):
                    del nad3[names[-1]]
                with self.assertRaises(KeyError):
                    del nad4[names[0]]
        
        # Remove our test synonyms
        ads_name._name_cache.clear()
        ads_name._name_synonyms.clear()
        ads_name._load_synonyms()


class TestNameAwareSet(TestCase):
    def test_add(self):
        nas = NameAwareSet()
        
        nas.add(equal_names[0])

        for name, name_str in zip(diff_names, diff_names_str):
            self.assertNotIn(name, nas)
            self.assertNotIn(name_str, nas)
            nas.add(name)
            self.assertIn(name, nas)
            self.assertIn(name_str, nas)
        
        for name, name_str in zip(equal_names, equal_names_str):
            self.assertIn(name, nas)
            self.assertIn(name_str, nas)

        for name, name_str in zip(diff_names, diff_names_str):
            self.assertIn(name, nas)
            self.assertIn(name_str, nas)
        
        nas2 = NameAwareSet()
        
        for name, name_str in zip(diff_names, diff_names_str):
            nas2.add(name_str)
            self.assertIn(name, nas2)
            self.assertIn(name_str, nas2)
    
    def test_len(self):
        nad = NameAwareSet()

        for name in diff_names:
            nad.add(name)
        
        self.assertEqual(len(nad), len(diff_names))

        for name in equal_names:
            nad.add(name)
        
        self.assertEqual(len(nad), len(diff_names) + 1)
    
    def test_values(self):
        nas = NameAwareSet()
        
        for name in diff_names_str:
            nas.add(name)
        
        self.assertEqual(sorted(nas.values()),
                         sorted(diff_names_str))
        
        for name in equal_names_str:
            nas.add(name)
        
        self.assertEqual(sorted(nas.values()),
                         sorted([equal_names_str[-1], *diff_names_str]))

    def test_with_synonyms(self):
        synonyms = [
            "test_synAA;test_synAB",
            "test_synBB, ;test_synBA,",
            "test_synCA, q; test_synCB, q",
            "test_synD, a; test_synD, b c",
            "test_synEB, b; test_synEA, a",
            "test_synFA, a b c d; test_synFB, a"
        ]
        # Hack: inject test synonyms
        ads_name._name_cache.clear()
        ads_name._parse_name_synonyms(synonyms)

        nas = NameAwareSet()
        for synonym in synonyms:
            names = synonym.split(';')
            for name in names:
                nas.add(name)
        self.assertEqual(len(nas), len(synonyms))
    
        # Remove our test synonyms
        ads_name._name_cache.clear()
        ads_name._name_synonyms.clear()
        ads_name._load_synonyms()
