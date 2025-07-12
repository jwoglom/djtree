from datetime import date
from django.test import TestCase
from person.models import (
    Person, Name, PersonName, BirthEvent
)
from person.management.util.person_matcher import PersonMatcher


class PersonMatcherTestCase(TestCase):
    """Test the person matching functionality"""
    
    def setUp(self):
        # Create test people in the database
        self.person1 = Person.objects.create()
        self.name1 = Name.objects.create(
            first_name='John',
            middle_name='Michael',
            last_name='Smith'
        )
        PersonName.objects.create(
            person=self.person1,
            name=self.name1,
            name_type=PersonName.Type.BIRTH
        )
        BirthEvent.objects.create(
            person=self.person1,
            date=date(1980, 3, 15),
            location='New York, NY, USA'
        )
        
        self.person2 = Person.objects.create()
        self.name2 = Name.objects.create(
            first_name='Mary',
            last_name='Johnson'
        )
        PersonName.objects.create(
            person=self.person2,
            name=self.name2,
            name_type=PersonName.Type.BIRTH
        )
        BirthEvent.objects.create(
            person=self.person2,
            date=date(1985, 8, 22),
            location='Chicago, IL, USA'
        )
    
    def test_find_matching_person_exact_match(self):
        """Test finding an exact match"""
        gedcom_person = {
            'NAME': 'John /Smith/',
            'BIRT': {'DATE': '15 MAR 1980'}
        }
        
        existing_people = list(Person.objects.all())
        match = PersonMatcher.find_matching_person(gedcom_person, existing_people)
        
        self.assertEqual(match, self.person1)
    
    def test_find_matching_person_no_match(self):
        """Test when no match is found"""
        gedcom_person = {
            'NAME': 'Unknown /Person/',
            'BIRT': {'DATE': '01 JAN 1990'}
        }
        
        existing_people = list(Person.objects.all())
        match = PersonMatcher.find_matching_person(gedcom_person, existing_people)
        
        self.assertIsNone(match)
    
    def test_find_matching_person_partial_match(self):
        """Test finding a partial match"""
        gedcom_person = {
            'NAME': 'John /Smithson/',  # Similar but not exact
            'BIRT': {'DATE': '15 MAR 1980'}
        }
        
        existing_people = list(Person.objects.all())
        match = PersonMatcher.find_matching_person(gedcom_person, existing_people, strict=False)
        
        # Should NOT match because last names are different (Smith vs Smithson)
        # This is the expected behavior with simplified logic
        self.assertIsNone(match)
    
    def test_simple_matching_logic(self):
        """Test the simplified matching logic"""
        # Test exact match
        gedcom_person = {
            'NAME': 'John /Smith/',
            'BIRT': {'DATE': '15 MAR 1980'}
        }
        existing_people = [self.person1]
        match = PersonMatcher.find_matching_person(gedcom_person, existing_people, strict=True)
        self.assertEqual(match, self.person1)
        
        # Test nickname match in non-strict mode
        gedcom_person = {
            'NAME': 'Bob /Smith/',
            'BIRT': {'DATE': '15 MAR 1980'}
        }
        match = PersonMatcher.find_matching_person(gedcom_person, existing_people, strict=False)
        self.assertIsNone(match)  # Should not match because we don't have Robert in our test data
        
        # Test no match with different last name
        gedcom_person = {
            'NAME': 'John /Johnson/',
            'BIRT': {'DATE': '15 MAR 1980'}
        }
        match = PersonMatcher.find_matching_person(gedcom_person, existing_people, strict=True)
        self.assertIsNone(match)
    
    def test_nickname_matching(self):
        """Test matching of common nicknames with simplified logic"""
        # Test a few key nickname cases that should work
        test_cases = [
            # (existing_name, gedcom_name, should_match, description)
            ('William', 'Bill', True, 'Bill is common nickname for William'),
            ('Robert', 'Bob', True, 'Bob is common nickname for Robert'),
            ('Michael', 'Mike', True, 'Mike is common nickname for Michael'),
            ('Christopher', 'Chris', True, 'Chris is common nickname for Christopher'),
            ('Elizabeth', 'Liz', True, 'Liz is common nickname for Elizabeth'),
            ('Peter', 'Pete', True, 'Pete is common nickname for Peter'),
            ('Christina', 'Tina', True, 'Tina is common nickname for Christina'),
            # Test some cases that should NOT match (very different names)
            ('John', 'Jane', False, 'Completely different names John and Jane should not match'),
            ('Mary', 'Sarah', False, 'Completely different names Mary and Sarah should not match'),
        ]
        
        for existing_first, gedcom_first, should_match, description in test_cases:
            with self.subTest(description):
                # Create a test person with the existing name
                test_person = Person.objects.create()
                test_name = Name.objects.create(
                    first_name=existing_first,
                    last_name='Test'
                )
                PersonName.objects.create(
                    person=test_person,
                    name=test_name,
                    name_type=PersonName.Type.BIRTH
                )
                BirthEvent.objects.create(
                    person=test_person,
                    date=date(1980, 1, 1),
                    location='Test Location'
                )
                
                # Test matching
                gedcom_data = {
                    'NAME': f'{gedcom_first} /Test/',
                    'BIRT': {'DATE': '01 JAN 1980'}
                }
                
                existing_people = [test_person]
                match = PersonMatcher.find_matching_person(gedcom_data, existing_people, strict=False)
                
                if should_match:
                    self.assertIsNotNone(match, f"Should match: {description}")
                    self.assertEqual(match, test_person)
                else:
                    self.assertIsNone(match, f"Should not match: {description}")
    
    def test_birth_date_blocking(self):
        """Test that birth date differences block matches with simplified logic"""
        # Create a test person
        test_person = Person.objects.create()
        test_name = Name.objects.create(
            first_name='John',
            last_name='Smith'
        )
        PersonName.objects.create(
            person=test_person,
            name=test_name,
            name_type=PersonName.Type.BIRTH
        )
        BirthEvent.objects.create(
            person=test_person,
            date=date(1980, 1, 1),
            location='Test Location'
        )
        
        # Test cases with simplified date matching logic
        test_cases = [
            (date(1980, 1, 1), True, 'Same date should match'),
            (date(1980, 6, 15), True, 'Same year should match'),
            (date(1982, 1, 1), False, '2 years difference should not match in strict mode'),
            (date(1985, 1, 1), False, '5 years difference should not match in strict mode'),
            (date(1975, 1, 1), False, '5 years earlier should not match in strict mode'),
        ]
        
        for birth_date, should_match, description in test_cases:
            with self.subTest(description):
                gedcom_data = {
                    'NAME': 'John /Smith/',
                    'BIRT': {'DATE': birth_date.strftime('%d %b %Y').upper()}
                }
                
                existing_people = [test_person]
                # Test strict mode (same year only)
                match = PersonMatcher.find_matching_person(gedcom_data, existing_people, strict=True)
                
                if should_match:
                    self.assertIsNotNone(match, f"Should match: {description}")
                    self.assertEqual(match, test_person)
                else:
                    self.assertIsNone(match, f"Should not match: {description}")
        
        # Test lenient mode
        test_cases_lenient = [
            (date(1982, 1, 1), True, '2 years difference should match in lenient mode'),
            (date(1985, 1, 1), False, '5 years difference should not match even in lenient mode'),
        ]
        
        for birth_date, should_match, description in test_cases_lenient:
            with self.subTest(f"Lenient: {description}"):
                gedcom_data = {
                    'NAME': 'John /Smith/',
                    'BIRT': {'DATE': birth_date.strftime('%d %b %Y').upper()}
                }
                
                existing_people = [test_person]
                match = PersonMatcher.find_matching_person(gedcom_data, existing_people, strict=False)
                
                if should_match:
                    self.assertIsNotNone(match, f"Should match: {description}")
                    self.assertEqual(match, test_person)
                else:
                    self.assertIsNone(match, f"Should not match: {description}")
    
    def test_nickname_detection(self):
        """Test the simplified nickname detection"""
        # Test common nicknames
        self.assertTrue(PersonMatcher._is_nickname('william', 'bill'))
        self.assertTrue(PersonMatcher._is_nickname('robert', 'bob'))
        self.assertTrue(PersonMatcher._is_nickname('michael', 'mike'))
        self.assertTrue(PersonMatcher._is_nickname('christopher', 'chris'))
        
        # Test reverse direction
        self.assertTrue(PersonMatcher._is_nickname('bill', 'william'))
        self.assertTrue(PersonMatcher._is_nickname('bob', 'robert'))
        self.assertTrue(PersonMatcher._is_nickname('pete', 'peter'))
        self.assertTrue(PersonMatcher._is_nickname('tina', 'christina'))
        
        # Test non-nicknames
        self.assertFalse(PersonMatcher._is_nickname('john', 'jane'))
        self.assertFalse(PersonMatcher._is_nickname('mary', 'sarah'))
        self.assertFalse(PersonMatcher._is_nickname('john', 'johnny'))  # Not in our simplified list
    
    def test_full_name_nickname_matching(self):
        """Test that full names with nicknames match correctly"""
        # Test "Pete Gibson" matches "Peter Gibson"
        test_person = Person.objects.create()
        test_name = Name.objects.create(
            first_name='Peter',
            last_name='Gibson'
        )
        PersonName.objects.create(
            person=test_person,
            name=test_name,
            name_type=PersonName.Type.BIRTH
        )
        BirthEvent.objects.create(
            person=test_person,
            date=date(1980, 1, 1),
            location='Test Location'
        )
        
        # Test GEDCOM data with nickname
        gedcom_data = {
            'NAME': 'Pete /Gibson/',
            'BIRT': {'DATE': '01 JAN 1980'}
        }
        
        existing_people = [test_person]
        match = PersonMatcher.find_matching_person(gedcom_data, existing_people, strict=False)
        
        self.assertIsNotNone(match, "Pete Gibson should match Peter Douglas Gibson")
        self.assertEqual(match, test_person)
        
        # Test "Tina Gibson" matches "Christina Gibson"
        test_person2 = Person.objects.create()
        test_name2 = Name.objects.create(
            first_name='Christina',
            last_name='Gibson'
        )
        PersonName.objects.create(
            person=test_person2,
            name=test_name2,
            name_type=PersonName.Type.BIRTH
        )
        BirthEvent.objects.create(
            person=test_person2,
            date=date(1950, 6, 1),
            location='Test Location'
        )
        
        # Test GEDCOM data with nickname
        gedcom_data2 = {
            'NAME': 'Tina /Gibson/',
            'BIRT': {'DATE': '1 JUN 1950'}
        }
        
        existing_people = [test_person2]
        match = PersonMatcher.find_matching_person(gedcom_data2, existing_people, strict=False)
        
        self.assertIsNotNone(match, "Tina Gibson should match Christina Gibson")
        self.assertEqual(match, test_person2)
    
    def test_full_name_nickname_matching_strict_mode(self):
        """Test that nickname matching only works in non-strict mode"""
        # Create test person with full name
        test_person = Person.objects.create()
        test_name = Name.objects.create(
            first_name='Peter',
            last_name='Gibson'
        )
        PersonName.objects.create(
            person=test_person,
            name=test_name,
            name_type=PersonName.Type.BIRTH
        )
        BirthEvent.objects.create(
            person=test_person,
            date=date(1980, 1, 1),
            location='Test Location'
        )
        
        # Test GEDCOM data with nickname in strict mode (should not match)
        gedcom_data = {
            'NAME': 'Pete /Gibson/',
            'BIRT': {'DATE': '01 JAN 1980'}
        }
        
        existing_people = [test_person]
        match = PersonMatcher.find_matching_person(gedcom_data, existing_people, strict=True)
        
        self.assertIsNone(match, "Pete Gibson should NOT match Peter Douglas Gibson in strict mode")
        
        # Test in non-strict mode (should match)
        match = PersonMatcher.find_matching_person(gedcom_data, existing_people, strict=False)
        
        self.assertIsNotNone(match, "Pete Gibson should match Peter Douglas Gibson in non-strict mode")
        self.assertEqual(match, test_person)


class PersonMatcherUtilityTestCase(TestCase):
    """Test the utility methods of PersonMatcher"""
    
    def test_parse_name_gedcom_format(self):
        """Test name parsing functionality"""
        # Test GEDCOM format with slashes
        first, middle, last = PersonMatcher._parse_name('John /Smith/')
        self.assertEqual(first, 'John')
        self.assertEqual(middle, '')
        self.assertEqual(last, 'Smith')
        
        # Test with middle name
        first, middle, last = PersonMatcher._parse_name('John Michael /Smith/')
        self.assertEqual(first, 'John')
        self.assertEqual(middle, 'Michael')
        self.assertEqual(last, 'Smith')
        
        # Test space-separated format
        first, middle, last = PersonMatcher._parse_name('John Smith')
        self.assertEqual(first, 'John')
        self.assertEqual(middle, '')
        self.assertEqual(last, 'Smith')
        
        # Test empty name
        first, middle, last = PersonMatcher._parse_name('')
        self.assertEqual(first, '')
        self.assertEqual(middle, '')
        self.assertEqual(last, '')
        
        # Test complex name with multiple middle names
        first, middle, last = PersonMatcher._parse_name('John Michael David /Smith/')
        self.assertEqual(first, 'John')
        self.assertEqual(middle, 'Michael David')
        self.assertEqual(last, 'Smith')
        
        # Test space-separated with multiple parts
        first, middle, last = PersonMatcher._parse_name('John Michael David Smith')
        self.assertEqual(first, 'John')
        self.assertEqual(middle, 'Michael David')
        self.assertEqual(last, 'Smith')
    
    def test_parse_date_formats(self):
        """Test date parsing functionality"""
        # Test DD MMM YYYY format
        date_obj = PersonMatcher._parse_date('15 MAR 1980')
        self.assertEqual(date_obj, date(1980, 3, 15))
        
        # Test YYYY format
        date_obj = PersonMatcher._parse_date('1980')
        self.assertEqual(date_obj, date(1980, 1, 1))
        
        # Test MM/DD/YYYY format
        date_obj = PersonMatcher._parse_date('03/15/1980')
        self.assertEqual(date_obj, date(1980, 3, 15))
        
        # Test invalid date
        date_obj = PersonMatcher._parse_date('invalid date')
        self.assertIsNone(date_obj)
        
        # Test empty date
        date_obj = PersonMatcher._parse_date('')
        self.assertIsNone(date_obj)
        
        # Test different months
        date_obj = PersonMatcher._parse_date('25 DEC 1995')
        self.assertEqual(date_obj, date(1995, 12, 25))
        
        # Test single digit day
        date_obj = PersonMatcher._parse_date('5 JAN 2000')
        self.assertEqual(date_obj, date(2000, 1, 5))
    
    def test_names_match_logic(self):
        """Test the name matching logic"""
        # Test exact match
        self.assertTrue(PersonMatcher._names_match(
            'john', 'michael', 'smith',
            'john', 'michael', 'smith',
            strict=True
        ))
        
        # Test case insensitive
        self.assertTrue(PersonMatcher._names_match(
            'John', 'Michael', 'Smith',
            'john', 'michael', 'smith',
            strict=True
        ))
        
        # Test different last names
        self.assertFalse(PersonMatcher._names_match(
            'john', 'michael', 'smith',
            'john', 'michael', 'jones',
            strict=True
        ))
        
        # Test missing first name
        self.assertFalse(PersonMatcher._names_match(
            '', 'michael', 'smith',
            'john', 'michael', 'smith',
            strict=True
        ))
        
        # Test missing last name
        self.assertFalse(PersonMatcher._names_match(
            'john', 'michael', '',
            'john', 'michael', 'smith',
            strict=True
        ))
    
    def test_dates_match_logic(self):
        """Test the date matching logic"""
        # Test exact match
        self.assertTrue(PersonMatcher._dates_match(
            date(1980, 3, 15),
            date(1980, 3, 15),
            strict=True
        ))
        
        # Test same year, different month/day (strict mode)
        self.assertTrue(PersonMatcher._dates_match(
            date(1980, 3, 15),
            date(1980, 12, 25),
            strict=True
        ))
        
        # Test different years (strict mode)
        self.assertFalse(PersonMatcher._dates_match(
            date(1980, 3, 15),
            date(1981, 3, 15),
            strict=True
        ))
        
        # Test different years (lenient mode)
        self.assertTrue(PersonMatcher._dates_match(
            date(1980, 3, 15),
            date(1981, 3, 15),
            strict=False
        ))
        
        # Test too far apart (lenient mode)
        self.assertFalse(PersonMatcher._dates_match(
            date(1980, 3, 15),
            date(1985, 3, 15),
            strict=False
        )) 