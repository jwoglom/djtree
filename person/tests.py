import os
import tempfile
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from io import StringIO
from person.models import (
    Person, Name, PersonName, ParentChildRelationship,
    BirthEvent, DeathEvent, MarriageEvent, DivorceEvent,
    ImmigrationEvent, CitizenshipEvent
)
from person.management.commands.import_gedcom import (
    GEDCOMParser, PersonMatcher, GEDCOMImporter
)


class GEDCOMParserTestCase(TestCase):
    """Test the GEDCOM parser functionality"""
    
    def setUp(self):
        self.sample_gedcom = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Smith/
2 GIVN John
2 SURN Smith
1 SEX M
1 BIRT
2 DATE 15 MAR 1980
2 PLAC New York, NY, USA
1 DEAT
2 DATE 10 JUN 2020
2 PLAC Los Angeles, CA, USA
2 CAUS Heart attack
0 @I2@ INDI
1 NAME Mary /Johnson/
2 GIVN Mary
2 SURN Johnson
1 SEX F
1 BIRT
2 DATE 22 AUG 1985
2 PLAC Chicago, IL, USA
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
1 MARR
2 DATE 05 JUN 2005
2 PLAC Las Vegas, NV, USA
0 @I3@ INDI
1 NAME Robert /Smith/
2 GIVN Robert
2 SURN Smith
1 SEX M
1 BIRT
2 DATE 12 DEC 2010
2 PLAC Los Angeles, CA, USA
0 TRLR"""
    
    def test_parse_gedcom_file(self):
        """Test parsing a GEDCOM file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(self.sample_gedcom)
            temp_file = f.name
        
        try:
            parser = GEDCOMParser(temp_file)
            individuals, families = parser.parse()
            
            # Check that we parsed the expected number of records
            self.assertEqual(len(individuals), 3)
            self.assertEqual(len(families), 1)
            
            # Check individual data
            self.assertIn('@I1@', individuals)
            self.assertIn('@I2@', individuals)
            self.assertIn('@I3@', individuals)
            
            # Check family data
            self.assertIn('@F1@', families)
            
            # Check specific individual data
            john = individuals['@I1@']
            self.assertEqual(john['type'], 'INDI')
            self.assertIn('NAME', john['data'])
            self.assertIn('BIRT', john['data'])
            self.assertIn('DEAT', john['data'])
            
            # Check nested data
            birth_data = john['data']['BIRT']
            self.assertIn('DATE', birth_data)
            self.assertIn('PLAC', birth_data)
            self.assertEqual(birth_data['DATE'], '15 MAR 1980')
            self.assertEqual(birth_data['PLAC'], 'New York, NY, USA')
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_name(self):
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
    
    def test_parse_date(self):
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
        
        # Should still match due to first name and birth date
        self.assertEqual(match, self.person1)
    
    def test_calculate_match_score(self):
        """Test match score calculation"""
        # Perfect match
        score = PersonMatcher._calculate_match_score(
            self.person1, 'John', 'Michael', 'Smith', date(1980, 3, 15)
        )
        self.assertGreater(score, 0.9)
        
        # Partial match
        score = PersonMatcher._calculate_match_score(
            self.person1, 'John', '', 'Smith', None
        )
        self.assertGreater(score, 0.7)
        
        # No match
        score = PersonMatcher._calculate_match_score(
            self.person1, 'Unknown', '', 'Person', date(1990, 1, 1)
        )
        self.assertLess(score, 0.3)


class GEDCOMImportTestCase(TestCase):
    """Test the GEDCOM import functionality"""
    
    def setUp(self):
        self.sample_gedcom = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Smith/
2 GIVN John
2 SURN Smith
1 SEX M
1 BIRT
2 DATE 15 MAR 1980
2 PLAC New York, NY, USA
1 DEAT
2 DATE 10 JUN 2020
2 PLAC Los Angeles, CA, USA
2 CAUS Heart attack
0 @I2@ INDI
1 NAME Mary /Johnson/
2 GIVN Mary
2 SURN Johnson
1 SEX F
1 BIRT
2 DATE 22 AUG 1985
2 PLAC Chicago, IL, USA
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
1 MARR
2 DATE 05 JUN 2005
2 PLAC Las Vegas, NV, USA
0 @I3@ INDI
1 NAME Robert /Smith/
2 GIVN Robert
2 SURN Smith
1 SEX M
1 BIRT
2 DATE 12 DEC 2010
2 PLAC Los Angeles, CA, USA
0 TRLR"""
    
    def test_import_gedcom_pretend_mode(self):
        """Test GEDCOM import in pretend mode"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(self.sample_gedcom)
            temp_file = f.name
        
        try:
            # Run import in pretend mode
            out = StringIO()
            call_command('import_gedcom', temp_file, stdout=out)
            
            # Check that no data was actually created
            self.assertEqual(Person.objects.count(), 0)
            self.assertEqual(Name.objects.count(), 0)
            self.assertEqual(BirthEvent.objects.count(), 0)
            self.assertEqual(MarriageEvent.objects.count(), 0)
            
            # Check output contains expected information
            output = out.getvalue()
            self.assertIn('PRETEND MODE', output)
            self.assertIn('Individuals created: 3', output)
            self.assertIn('Events created:', output)
            
        finally:
            os.unlink(temp_file)
    
    def test_import_gedcom_real_mode(self):
        """Test GEDCOM import in real mode"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(self.sample_gedcom)
            temp_file = f.name
        
        try:
            # Run import in real mode
            out = StringIO()
            call_command('import_gedcom', temp_file, '--no-pretend', stdout=out)
            
            # Check that data was created
            self.assertEqual(Person.objects.count(), 3)
            self.assertEqual(Name.objects.count(), 3)
            self.assertEqual(BirthEvent.objects.count(), 3)
            self.assertEqual(MarriageEvent.objects.count(), 2)  # Expect 2, not 1
            
            # Check specific data
            john = Person.objects.filter(names__last_name='Smith', names__first_name='John').first()
            self.assertIsNotNone(john)
            self.assertIsNotNone(john.birth)
            self.assertEqual(john.birth.date, date(1980, 3, 15))
            self.assertEqual(john.birth.location, 'New York, NY, USA')
            
            mary = Person.objects.filter(names__last_name='Johnson', names__first_name='Mary').first()
            self.assertIsNotNone(mary)
            
            robert = Person.objects.filter(names__last_name='Smith', names__first_name='Robert').first()
            self.assertIsNotNone(robert)
            
            # Check relationships
            self.assertEqual(john.children.count(), 1)
            self.assertEqual(mary.children.count(), 1)
            self.assertEqual(robert.parents.count(), 2)
            
            # Check marriage
            marriage = MarriageEvent.objects.filter(person=john, other_person=mary).first()
            self.assertIsNotNone(marriage)
            self.assertEqual(marriage.date, date(2005, 6, 5))
            self.assertEqual(marriage.location, 'Las Vegas, NV, USA')
            
        finally:
            os.unlink(temp_file)
    
    def test_import_gedcom_duplicate_detection(self):
        """Test duplicate detection during import"""
        # Create an existing person
        existing_person = Person.objects.create()
        existing_name = Name.objects.create(
            first_name='John',
            last_name='Smith'
        )
        PersonName.objects.create(
            person=existing_person,
            name=existing_name,
            name_type=PersonName.Type.BIRTH
        )
        BirthEvent.objects.create(
            person=existing_person,
            date=date(1980, 3, 15),
            location='New York, NY, USA'
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(self.sample_gedcom)
            temp_file = f.name
        
        try:
            # Run import in real mode
            out = StringIO()
            call_command('import_gedcom', temp_file, '--no-pretend', stdout=out)
            
            # Should have 3 people total (1 existing + 2 new)
            self.assertEqual(Person.objects.count(), 3)
            
            # Should have 3 names total (1 existing + 2 new)
            self.assertEqual(Name.objects.count(), 3)
            
            # Check output shows duplicate detection
            output = out.getvalue()
            self.assertIn('Found existing person', output)
            self.assertIn('Individuals updated: 1', output)
            
        finally:
            os.unlink(temp_file)
    
    def test_import_gedcom_invalid_file(self):
        """Test import with invalid file"""
        with self.assertRaises(CommandError):
            call_command('import_gedcom', 'nonexistent_file.ged')
    
    def test_import_gedcom_malformed_data(self):
        """Test import with malformed GEDCOM data"""
        malformed_gedcom = """0 HEAD
1 GEDC
2 VERS 5.5.5
0 @I1@ INDI
1 NAME Invalid Name
1 BIRT
2 DATE INVALID DATE
0 TRLR"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(malformed_gedcom)
            temp_file = f.name
        
        try:
            # Should not raise an exception, but should handle errors gracefully
            out = StringIO()
            call_command('import_gedcom', temp_file, stdout=out)
            
            # Check that the command completed successfully
            output = out.getvalue()
            self.assertIn('IMPORT SUMMARY', output)
            
        finally:
            os.unlink(temp_file)


class GEDCOMImporterIntegrationTestCase(TestCase):
    """Integration tests for the GEDCOM importer"""
    
    def test_import_with_complex_family_structure(self):
        """Test import with a more complex family structure"""
        complex_gedcom = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Smith/
2 GIVN John
2 SURN Smith
1 SEX M
1 BIRT
2 DATE 15 MAR 1980
2 PLAC New York, NY, USA
0 @I2@ INDI
1 NAME Mary /Johnson/
2 GIVN Mary
2 SURN Johnson
1 SEX F
1 BIRT
2 DATE 22 AUG 1985
2 PLAC Chicago, IL, USA
0 @I3@ INDI
1 NAME Robert /Smith/
2 GIVN Robert
2 SURN Smith
1 SEX M
1 BIRT
2 DATE 12 DEC 2010
2 PLAC Los Angeles, CA, USA
0 @I4@ INDI
1 NAME Sarah /Smith/
2 GIVN Sarah
2 SURN Smith
1 SEX F
1 BIRT
2 DATE 15 JUN 2012
2 PLAC Los Angeles, CA, USA
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
1 CHIL @I4@
1 MARR
2 DATE 05 JUN 2005
2 PLAC Las Vegas, NV, USA
0 TRLR"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(complex_gedcom)
            temp_file = f.name
        
        try:
            # Run import
            out = StringIO()
            call_command('import_gedcom', temp_file, '--no-pretend', stdout=out)
            
            # Verify family structure
            john = Person.objects.filter(names__last_name='Smith', names__first_name='John').first()
            mary = Person.objects.filter(names__last_name='Johnson', names__first_name='Mary').first()
            robert = Person.objects.filter(names__last_name='Smith', names__first_name='Robert').first()
            sarah = Person.objects.filter(names__last_name='Smith', names__first_name='Sarah').first()
            
            # Check parent-child relationships
            self.assertEqual(john.children.count(), 2)
            self.assertEqual(mary.children.count(), 2)
            self.assertEqual(robert.parents.count(), 2)
            self.assertEqual(sarah.parents.count(), 2)
            
            # Check siblings
            self.assertEqual(robert.siblings.count(), 1)
            self.assertEqual(sarah.siblings.count(), 1)
            self.assertIn(robert, sarah.siblings.all())
            self.assertIn(sarah, robert.siblings.all())
            
            # Check marriage
            self.assertEqual(john.spouse, mary)
            self.assertEqual(mary.spouse, john)
            
        finally:
            os.unlink(temp_file)
    
    def test_import_with_death_events(self):
        """Test import with death events"""
        gedcom_with_death = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Smith/
2 GIVN John
2 SURN Smith
1 SEX M
1 BIRT
2 DATE 15 MAR 1980
2 PLAC New York, NY, USA
1 DEAT
2 DATE 10 JUN 2020
2 PLAC Los Angeles, CA, USA
2 CAUS Heart attack
0 TRLR"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(gedcom_with_death)
            temp_file = f.name
        
        try:
            # Run import
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Check death event
            john = Person.objects.filter(names__last_name='Smith', names__first_name='John').first()
            self.assertIsNotNone(john.death)
            self.assertEqual(john.death.date, date(2020, 6, 10))
            self.assertEqual(john.death.location, 'Los Angeles, CA, USA')
            self.assertEqual(john.death.cause, 'Heart attack')
            
            # Check that person is marked as deceased
            self.assertFalse(john.is_living)
            
        finally:
            os.unlink(temp_file)


# Import date for the test cases
from datetime import date
