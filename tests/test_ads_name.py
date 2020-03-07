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
            nameB = ADSName(data[0])
            results = data[1:]
            for i, result in enumerate(results):
                if result:
                    self.assertEqual(nameB, namesA[i])
                else:
                    self.assertNotEqual(nameB, namesA[i])
        
        self.assertNotEqual(nameB, 1)
    
    def test_exact_equality(self):
        aname = ADSName("=" + namesA[0])
        self.assertEqual(aname, namesA[0])
        for name in namesA[1:]:
            self.assertNotEqual(name, aname)
            
    
    def test_repr(self):
        for name in namesA:
            self.assertEqual(name, repr(ADSName(name)))
        
        name = "=" + name
        self.assertEqual(name, repr(ADSName(name)))
    
    def test_creation(self):
        self.assertEqual(
            ADSName("murray, stephen s"),
            ADSName("murray", "stephen", "s.")
        )
        
        self.assertEqual(
            ADSName("murray, stephen"),
            ADSName("murray", "stephen")
        )
        
        self.assertEqual(
            ADSName("murray"),
            ADSName("murray")
        )
        
        with self.assertRaises(ValueError):
            ADSName("murray", middle_name="s")
