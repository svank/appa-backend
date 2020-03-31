from unittest import TestCase

from ads_name import ADSName

namesA = [
    "murray",
    "murray, s.",
    "murray, s. s.",
    "murray, stephen",
    "murray, stephen s.",
    "murray, stephen steve"
]

# Names and whether they should be equal to each name in namesA
namesB = [
    ("murray", True, True, True, True, True, True),
    ("Murray", True, True, True, True, True, True),
    ("murrayer", False, False, False, False, False, False),
    ("M", False, False, False, False, False, False),
    ("murray, s", True, True, True, True, True, True),
    ("Murray, S.", True, True, True, True, True, True),
    ("Burray, s.", False, False, False, False, False, False),
    ("murray, e", True, False, False, False, False, False),
    ("murray, e.", True, False, False, False, False, False),
    ("murray, s s", True, True, True, True, True, True),
    ("Murray, S. s.", True, True, True, True, True, True),
    ("Burray, s. s.", False, False, False, False, False, False),
    ("murray, e s", True, False, False, False, False, False),
    ("murray, s e", True, True, False, True, False, False),
    ("murray, stephen", True, True, True, True, True, True),
    ("burray, stephen", False, False, False, False, False, False),
    ("murray, eva", True, False, False, False, False, False),
    ("murray, stephen s", True, True, True, True, True, True),
    ("murray, stephen e", True, True, False, True, False, False),
    ("burray, stephen s", False, False, False, False, False, False),
    ("murray, eva s", True, False, False, False, False, False),
    ("murray, stephen steve", True, True, True, True, True, True),
    ("murray, stephen eva", True, True, False, True, False, False),
    ("burray, stephen steve", False, False, False, False, False, False),
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
    
    def test_exact_equality(self):
        aname = ADSName.parse("=" + namesA[0])
        self.assertEqual(aname, namesA[0])
        for name in namesA[1:]:
            self.assertNotEqual(name, aname)
    
    def test_detail_equality(self):
        for i, name1 in enumerate(namesA):
            name1_lt = ADSName.parse("<" + name1)
            name1_gt = ADSName.parse(">" + name1)
            self.assertEqual(name1_lt, name1_lt)
            self.assertEqual(name1_gt, name1_gt)
            self.assertEqual(name1_lt, name1_gt)
            self.assertEqual(name1_gt, name1_lt)
            
            for j, name2 in enumerate(namesA):
                name2 = ADSName.parse(name2)
                if i > j:
                    self.assertEqual(name1_lt, name2)
                    self.assertEqual(name2, name1_lt)
                    self.assertNotEqual(name1_gt, name2)
                    self.assertNotEqual(name2, name1_gt)
                elif i < j:
                    self.assertNotEqual(name1_lt, name2)
                    self.assertNotEqual(name2, name1_lt)
                    self.assertEqual(name1_gt, name2)
                    self.assertEqual(name2, name1_gt)
                else:
                    self.assertEqual(name1_lt, name2)
                    self.assertEqual(name2, name1_lt)
                    self.assertEqual(name1_gt, name2)
                    self.assertEqual(name2, name1_gt)
    
    def test_repr(self):
        for name in namesA:
            self.assertEqual(name, repr(ADSName.parse(name)))
        
        name_ = "=" + name
        self.assertEqual(name_, repr(ADSName.parse(name_)))
        
        name_ = ">" + name
        self.assertEqual(name_, repr(ADSName.parse(name_)))
        
        name_ = "<" + name
        self.assertEqual(name_, repr(ADSName.parse(name_)))
    
    def test_creation(self):
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
        
        with self.assertRaises(ValueError):
            ADSName.parse("murray", middle_name="s")
    
    def test_original_name(self):
        for n in namesA:
            name = ADSName.parse(n)
            self.assertEqual(name.original_name, n)
            
            name = ADSName.parse(n.upper())
            self.assertEqual(name.original_name, n.upper())
            self.assertNotEqual(name.original_name, n)
            self.assertEqual(name.full_name, n)
            
            for modifier in ['=', '<', '>']:
                name = ADSName.parse(modifier + n)
                self.assertEqual(name.original_name, modifier + n)
                self.assertEqual(name.bare_original_name, n)
    
    def test_full_name_formatting(self):
        for n in namesA:
            name1 = ADSName.parse(n)
            name2 = ADSName.parse(n.replace(", ", ",").replace(".", ""))
            self.assertEqual(str(name1), str(name2))
            self.assertEqual(name1, name2)

            for modifier in ['=', '<', '>']:
                name1 = ADSName.parse(modifier + n)
                name2 = ADSName.parse((modifier + n).replace(", ", ",").replace(".", ""))
                self.assertEqual(str(name1), str(name2))
                self.assertEqual(name1, name2)
