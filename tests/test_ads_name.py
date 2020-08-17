from unittest import TestCase

import ads_name
from ads_name import ADSName, InvalidName

namesA = [
    "murray",
    "murray, s.",
    "murray, s. s.",
    "murray, s. steve",
    "murray, stephen",
    "murray, stephen s.",
    "murray, stephen steve",
    "murray, stephen steve q."
]

# Names and whether they should be equal to each name in namesA
namesB = [
    ("murray", True, True, True, True, True, True, True, True),
    ("Murray", True, True, True, True, True, True, True, True),
    ("murrayer", False, False, False, False, False, False, False, False),
    ("M", False, False, False, False, False, False, False, False),
    ("murray, s", True, True, True, True, True, True, True, True),
    ("Murray, S.", True, True, True, True, True, True, True, True),
    ("Burray, s.", False, False, False, False, False, False, False, False),
    ("murray, e", True, False, False, False, False, False, False, False),
    ("murray, e.", True, False, False, False, False, False, False, False),
    ("murray, s s", True, True, True, True, True, True, True, True),
    ("Murray, S. s.", True, True, True, True, True, True, True, True),
    ("Burray, s. s.", False, False, False, False, False, False, False, False),
    ("murray, e s", True, False, False, False, False, False, False, False),
    ("murray, s e", True, True, False, False, True, False, False, False),
    ("murray, stephen", True, True, True, True, True, True, True, True),
    ("burray, stephen", False, False, False, False, False, False, False, False),
    ("murray, eva", True, False, False, False, False, False, False, False),
    ("murray, stephen s", True, True, True, True, True, True, True, True),
    ("murray, stephen e", True, True, False, False, True, False, False, False),
    ("burray, stephen s", False, False, False, False, False, False, False, False),
    ("murray, stephen s z", True, True, True, True, True, True, True, False),
    ("burray, stephen s q", False, False, False, False, False, False, False, False),
    ("murray, eva s", True, False, False, False, False, False, False, False),
    ("murray, stephen steve", True, True, True, True, True, True, True, True),
    ("murray, stephen eva", True, True, False, False, True, False, False, False),
    ("burray, stephen steve", False, False, False, False, False, False, False, False),
]


class TestADSName(TestCase):
    def test_equality(self):
        for data in namesB:
            nameB = ADSName.parse(data[0])
            results = data[1:]
            for i, result in enumerate(results):
                if result:
                    self.assertEqual(nameB, namesA[i])
                else:
                    self.assertNotEqual(nameB, namesA[i])
        
        self.assertNotEqual(nameB, 1)
        self.assertNotEqual(nameB, "a string")
    
    def test_exact_equality(self):
        for i in range(len(namesA)):
            aname = ADSName.parse("=" + namesA[i])
            self.assertEqual(aname, namesA[i])
            self.assertEqual(aname, aname)
            for j in range(len(namesA)):
                if i != j:
                    self.assertNotEqual(namesA[j], aname)
    
    def test_specificity_equality(self):
        for i, name1 in enumerate(namesA):
            name1_lt = ADSName.parse("<" + name1)
            name1_gt = ADSName.parse(">" + name1)
            name1_lte = ADSName.parse("<=" + name1)
            name1_gte = ADSName.parse(">=" + name1)
            
            self.assertNotEqual(name1_lt, name1_lt)
            self.assertNotEqual(name1_gt, name1_gt)
            self.assertNotEqual(name1_lt, name1_gt)
            self.assertNotEqual(name1_gt, name1_lt)
            
            self.assertEqual(name1_lte, name1_lte)
            self.assertEqual(name1_gte, name1_gte)
            self.assertEqual(name1_lte, name1_gte)
            self.assertEqual(name1_gte, name1_lte)
            
            self.assertNotEqual(name1_lte, name1_lt)
            self.assertNotEqual(name1_gte, name1_gt)
            self.assertNotEqual(name1_lte, name1_gt)
            self.assertNotEqual(name1_gte, name1_lt)
            
            self.assertNotEqual(name1_lt, name1_lte)
            self.assertNotEqual(name1_gt, name1_gte)
            self.assertNotEqual(name1_lt, name1_gte)
            self.assertNotEqual(name1_gt, name1_lte)
            
            for j, name2 in enumerate(namesA):
                name2 = ADSName.parse(name2)
                # A larger index corresponds to more specificity, with a
                # few exceptions
                if i == j:
                    self.assertNotEqual(name1_lt, name2)
                    self.assertNotEqual(name2, name1_lt)
                    self.assertNotEqual(name1_gt, name2)
                    self.assertNotEqual(name2, name1_gt)
    
                    self.assertEqual(name1_lte, name2)
                    self.assertEqual(name2, name1_lte)
                    self.assertEqual(name1_gte, name2)
                    self.assertEqual(name2, name1_gte)
                elif ((i == 2 and j == 4)
                        or (i == 3 and j in (4, 5))
                        or (i == 4 and j in (2, 3))
                        or (i == 5 and j == 3)):
                    self.assertNotEqual(name1_lt, name2)
                    self.assertNotEqual(name2, name1_lt)
                    self.assertNotEqual(name1_gt, name2)
                    self.assertNotEqual(name2, name1_gt)
    
                    self.assertNotEqual(name1_lte, name2)
                    self.assertNotEqual(name2, name1_lte)
                    self.assertNotEqual(name1_gte, name2)
                    self.assertNotEqual(name2, name1_gte)
                elif i > j:
                    self.assertEqual(name1_lt, name2)
                    self.assertEqual(name2, name1_lt)
                    self.assertNotEqual(name1_gt, name2)
                    self.assertNotEqual(name2, name1_gt)
                    
                    self.assertEqual(name1_lte, name2)
                    self.assertEqual(name2, name1_lte)
                    self.assertNotEqual(name1_gte, name2)
                    self.assertNotEqual(name2, name1_gte)
                elif i < j:
                    self.assertNotEqual(name1_lt, name2)
                    self.assertNotEqual(name2, name1_lt)
                    self.assertEqual(name1_gt, name2)
                    self.assertEqual(name2, name1_gt)
                    
                    self.assertNotEqual(name1_lte, name2)
                    self.assertNotEqual(name2, name1_lte)
                    self.assertEqual(name1_gte, name2)
                    self.assertEqual(name2, name1_gte)
                else:
                    self.fail("Shouldn't get here")
    
    def test_modifier_functions(self):
        for mod, req_exact, req_less, req_more, allow_same in (
            ['', False, False, False, True],
            ['>', False, False, True, False],
            ['<', False, True, False, False],
            ['=', True, False, False, False],
            ['>=', False, False, True, True],
            ['<=', False, True, False, True],
        ):
            name = ADSName.parse(mod + namesA[1])
            self.assertEqual(name.require_exact_match, req_exact)
            self.assertEqual(name.require_less_specific, req_less)
            self.assertEqual(name.require_more_specific, req_more)
            self.assertEqual(name.allow_same_specific, allow_same)
            
            self.assertEqual(name.excludes_self,
                             (req_less or req_more) and not allow_same)
            self.assertEqual(name.has_modifiers(), mod != '')
            self.assertEqual(name.modifiers, mod)
            self.assertEqual(name.without_modifiers.full_name, namesA[1])
    
    def test_repr(self):
        """Test than string representations of ADSNames are as expected"""
        for name in namesA:
            for modifier in ['', '=', '>', '<', '<=', '>=']:
                name2 = modifier + name
                self.assertEqual(name2, repr(ADSName.parse(name2)))
            
            name2 = ">=" + name
            self.assertEqual(name2, repr(ADSName.parse("=>" + name)))
            
            name2 = "<=" + name
            self.assertEqual(name2, repr(ADSName.parse("=<" + name)))
    
    def test_creation(self):
        """
        Test different ways of instantiating ADSNames
        """
        self.assertEqual(
            ADSName.parse("murray, stephen s. q."),
            ADSName.parse("murray", "stephen", "s", "q")
        )
        
        self.assertEqual(
            ADSName.parse("murray, stephen s"),
            ADSName.parse("murray", "stephen", "s.")
        )
        
        self.assertEqual(
            ADSName.parse("murray, stephen"),
            ADSName.parse("murray", "stephen")
        )
        
        self.assertEqual(
            ADSName.parse("murray"),
            ADSName.parse("murray")
        )
        
        name = ADSName.parse("murray")
        name2 = ADSName.parse(name)
        self.assertIs(name, name2)
        
        with self.assertRaises(TypeError):
            ADSName.parse(1)
        with self.assertRaises(TypeError):
            ADSName.parse("murray", name)
        with self.assertRaises(TypeError):
            ADSName.parse("murray", None)
    
    def test_add(self):
        name = ADSName.parse(namesA[-1])
        name_str = str(name)
        self.assertEqual("prefix" + name_str, "prefix" + name)
        self.assertEqual(name_str + "suffix", name + "suffix")
    
    def test_original_and_full_name(self):
        """Test that original and full name access works"""
        for n in namesA:
            name = ADSName.parse(n)
            self.assertEqual(name.original_name, n)
            self.assertEqual(name.bare_original_name, n)
            
            name = ADSName.parse(n.upper())
            self.assertEqual(name.original_name, n.upper())
            self.assertEqual(name.bare_original_name, n.upper())
            self.assertNotEqual(name.original_name, n)
            self.assertNotEqual(name.bare_original_name, n)
            self.assertEqual(name.full_name, n)
            self.assertEqual(name.qualified_full_name, n)
            
            for modifier in ['=', '<', '>', '<=', '>=']:
                name = ADSName.parse(modifier + n)
                self.assertEqual(name.original_name, modifier + n)
                self.assertEqual(name.bare_original_name, n)
                self.assertEqual(name.full_name, n)
                self.assertEqual(name.qualified_full_name, modifier + n)
            
            for modifier, cor_modifier in zip(['=<', '=>'], ['<=', '>=']):
                name = ADSName.parse(modifier + n)
                self.assertEqual(name.original_name, modifier + n)
                self.assertEqual(name.bare_original_name, n)
                self.assertEqual(name.full_name, n)
                self.assertEqual(name.qualified_full_name, cor_modifier + n)
                
    
    def test_full_name_formatting(self):
        """Test than name parsing is insensitive to spacing and periods"""
        for n in namesA:
            name1 = ADSName.parse(n)
            name2 = ADSName.parse(n.replace(", ", ",").replace(".", ""))
            self.assertEqual(str(name1), str(name2))
            self.assertEqual(name1, name2)

            for modifier in ['=', '<', '>', '<=', '>=']:
                name1 = ADSName.parse(modifier + n)
                name2 = ADSName.parse((modifier + n).replace(", ", ",").replace(".", ""))
                self.assertEqual(str(name1), str(name2))
                if '=' in modifier:
                    self.assertEqual(name1, name2)
                else:
                    self.assertNotEqual(name1, name2)
    
    def test_level_of_detail(self):
        self.assertEqual(0,
                         ADSName.parse("last").level_of_detail)
        self.assertEqual(3,
                         ADSName.parse("last, f").level_of_detail)
        self.assertEqual(10,
                         ADSName.parse("last, first").level_of_detail)
        self.assertEqual(6,
                         ADSName.parse("last, f m").level_of_detail)
        self.assertEqual(13,
                         ADSName.parse("last, f middle").level_of_detail)
        self.assertEqual(20,
                         ADSName.parse("last, first middle").level_of_detail)
        self.assertEqual(23,
                         ADSName.parse("last, first middle m").level_of_detail)
    
    def test_special_cases(self):
        # A variety of special cases that should be handled
        name = "author, first middle"
        for char in "!@#$%^&*()+={}[];:'\"<>/?":
            name_mutated = name[0:2] + char + name[2:]
            self.assertEqual(ADSName.parse(name_mutated).full_name, name)
        
        # Hyphens should be treated as spaces
        self.assertEqual(ADSName.parse("author, first-middle").full_name,
                         "author, first middle")
        
        self.assertEqual(ADSName.parse("author, first-m").full_name,
                         "author, first m.")
        
        self.assertEqual(ADSName.parse("author-name, first").full_name,
                         "author name, first")
        
        # A hyphen prefix should be stripped
        self.assertEqual(ADSName.parse("author, f. -m").full_name,
                         "author, f. m.")
        
        # Periods should be treated as spaces to handle typos
        self.assertEqual(ADSName.parse("author, f.m.").full_name,
                         "author, f. m.")
        
        # Diacritics should be stripped
        self.assertEqual(ADSName.parse("Áùthor, ñäme").full_name,
                         "author, name")
        
        # Additional commas should be ignored
        self.assertEqual(ADSName.parse("author, first m., jr.").full_name,
                         "author, first m. jr")
        
        # Extra spaces should be ignored
        self.assertEqual(ADSName.parse(" author ,   first   m.   ").full_name,
                         "author, first m.")
        
        # Extra internal spaces should be removed
        self.assertEqual(ADSName.parse("last      name, first").full_name,
                         "last name, first")
        self.assertEqual(ADSName.parse("last  name, first").full_name,
                         "last name, first")
        self.assertEqual(ADSName.parse("last.  name, first").full_name,
                         "last name, first")
        self.assertEqual(ADSName.parse("last name, first").full_name,
                         "last name, first")
    
    def test_errors(self):
        with self.assertRaises(InvalidName):
            ADSName.parse(",last, first")
        with self.assertRaises(InvalidName):
            ADSName.parse(",last")
    
    def test_preserve_case(self):
        # Ensure the parsing cache is populated
        for name in namesA:
            parsed = ADSName.parse(name.upper())
            self.assertEqual(parsed.full_name, name)
        
        for name in namesA:
            parsed = ADSName.parse(name.upper(), preserve=True)
            self.assertEqual(parsed.full_name, name.upper())
        
        for name in namesA:
            parsed = ADSName.parse(name.upper())
            parsed = ADSName.parse(parsed, preserve=True)
            self.assertEqual(parsed.full_name, name.upper())
    
    def test_synonyms(self):
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
        
        for syn in synonyms:
            names = syn.split(';')
            self.assertEqual(ADSName.parse(names[0]), ADSName.parse(names[1]))
            for other_synonyms in synonyms:
                if other_synonyms != syn:
                    other_names = other_synonyms.split(';')
                    for other_name in other_names:
                        self.assertNotEqual(ADSName.parse(names[0]),
                                            ADSName.parse(other_name))
                        self.assertNotEqual(ADSName.parse(names[1]),
                                            ADSName.parse(other_name))
        
        # A synonym without given names should work with given names provided
        self.assertEqual(
            ADSName.parse("test_synAA, a"),
            ADSName.parse("test_synAB, abc"))
        
        # A synonym with given names should work without given names provided
        self.assertEqual(
            ADSName.parse("test_synEA"),
            ADSName.parse("test_synEB"))
        
        # "test_synD, b c" should be selected as canonical.
        self.assertEqual(
            ADSName.parse("test_synD, a b c d"),
            ADSName.parse("test_synD, b"))
        self.assertEqual(
            ADSName.parse("test_synD, a b c d").synonym,
            ADSName.parse("test_synD, b c"))
        self.assertIsNone(ADSName.parse("test_synD, b c d").synonym)
        
        # Names not matching a synonym should be unaffected
        self.assertIsNone(ADSName.parse("test_synD, e").synonym)
        self.assertIsNone(ADSName.parse("test_synEA, f").synonym)
        self.assertIsNone(ADSName.parse("test_synEA, f").synonym)
        
        # Synonyms should be possibilities, not mandatory. So 'test_synFB, q',
        # which is not synonym-ized due to the differing initial, should still
        # be equal to 'test_synFB', which gets synonym-ized to 'test_synFA'
        self.assertEqual(ADSName.parse("test_synFB"),
                         ADSName.parse("test_synFB, q"))
        
        # Nothing should be changed when using the `preserve` flag
        self.assertIsNone(
            ADSName.parse("test_synEA, abc d.", preserve=True).synonym)
        self.assertIsNone(
            ADSName.parse("test_synEA, abc d.", preserve=True).synonym)
        self.assertNotEqual(
            ADSName.parse("test_synEA, abc d.", preserve=True),
            ADSName.parse("test_synEB, b", preserve=True))
        
        # Remove our test synonyms
        ads_name._name_cache.clear()
        ads_name._name_synonyms.clear()
        ads_name._load_synonyms()
