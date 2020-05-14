from unittest import TestCase

from ads_name import ADSName

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
        Test different ways of instantiationg ADSNames
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
    
    def test_original_name(self):
        """Test that the original name is stored properly"""
        for n in namesA:
            name = ADSName.parse(n)
            self.assertEqual(name.original_name, n)
            
            name = ADSName.parse(n.upper())
            self.assertEqual(name.original_name, n.upper())
            self.assertNotEqual(name.original_name, n)
            self.assertEqual(name.full_name, n)
            
            for modifier in ['=', '<', '>', '<=', '>=', '=<', '=>', '<>=', '=><']:
                name = ADSName.parse(modifier + n)
                self.assertEqual(name.original_name, modifier + n)
                self.assertEqual(name.bare_original_name, n)
    
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
