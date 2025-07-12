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
    GEDCOMParser, GEDCOMImporter
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
    



# PersonMatcherTestCase removed; see util/test_person_matcher.py for these tests


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
            
            # Should have 3 people total (1 existing + 2 new, since John Smith is detected as duplicate)
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


class GEDCOMAdvancedTestCase(TestCase):
    """Advanced GEDCOM import tests using canonical examples"""
    
    def test_import_multiple_marriages(self):
        """Test import with multiple marriages and divorce"""
        multiple_marriages_gedcom = """0 HEAD
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
1 NAME Jane /Wilson/
2 GIVN Jane
2 SURN Wilson
1 SEX F
1 BIRT
2 DATE 10 JAN 1982
2 PLAC Boston, MA, USA
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 MARR
2 DATE 05 JUN 2005
2 PLAC Las Vegas, NV, USA
1 DIV
2 DATE 15 JUL 2010
2 PLAC Los Angeles, CA, USA
0 @F2@ FAM
1 HUSB @I1@
1 WIFE @I3@
1 MARR
2 DATE 20 AUG 2012
2 PLAC San Francisco, CA, USA
0 TRLR"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(multiple_marriages_gedcom)
            temp_file = f.name
        
        try:
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Check people were created
            self.assertEqual(Person.objects.count(), 3)
            
            # Check marriages
            john = Person.objects.filter(names__first_name='John').first()
            mary = Person.objects.filter(names__first_name='Mary').first()
            jane = Person.objects.filter(names__first_name='Jane').first()
            
            # Should have 4 marriage events (2 marriages, each with 2 records for symmetry)
            self.assertEqual(MarriageEvent.objects.count(), 4)
            
            # Check divorce event
            divorce_events = DivorceEvent.objects.all()
            self.assertEqual(divorce_events.count(), 2)  # Symmetric divorce records
            
            # Check current spouse (should be Jane, the most recent marriage)
            self.assertEqual(john.spouse, jane)
            
        finally:
            os.unlink(temp_file)
    
    def test_import_immigration_citizenship(self):
        """Test import with immigration and citizenship events"""
        immigration_gedcom = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Maria /Garcia/
2 GIVN Maria
2 SURN Garcia
1 SEX F
1 BIRT
2 DATE 15 MAR 1980
2 PLAC Madrid, Spain
1 EMIG
2 DATE 10 JUN 2000
2 PLAC Madrid, Spain
3 PLAC_TO New York, NY, USA
1 IMMI
2 DATE 12 JUN 2000
2 PLAC New York, NY, USA
3 PLAC_FROM Madrid, Spain
1 NATU
2 DATE 15 JUL 2010
2 PLAC New York, NY, USA
0 TRLR"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(immigration_gedcom)
            temp_file = f.name
        
        try:
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Check person was created
            self.assertEqual(Person.objects.count(), 1)
            
            maria = Person.objects.filter(names__first_name='Maria').first()
            self.assertIsNotNone(maria)
            
            # Check immigration event
            immigration = ImmigrationEvent.objects.filter(person=maria).first()
            self.assertIsNotNone(immigration)
            self.assertEqual(immigration.from_country, 'Madrid, Spain')
            self.assertEqual(immigration.to_country, 'New York, NY, USA')
            
            # Check citizenship event
            citizenship = CitizenshipEvent.objects.filter(person=maria).first()
            self.assertIsNotNone(citizenship)
            self.assertEqual(citizenship.country, 'New York, NY, USA')
            
        finally:
            os.unlink(temp_file)
    
    def test_import_gender_handling(self):
        """Test import with different gender values"""
        gender_gedcom = """0 HEAD
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
0 @I2@ INDI
1 NAME Mary /Johnson/
2 GIVN Mary
2 SURN Johnson
1 SEX F
1 BIRT
2 DATE 22 AUG 1985
0 @I3@ INDI
1 NAME Alex /Taylor/
2 GIVN Alex
2 SURN Taylor
1 SEX U
1 BIRT
2 DATE 10 JAN 1990
0 TRLR"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(gender_gedcom)
            temp_file = f.name
        
        try:
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Check people were created
            self.assertEqual(Person.objects.count(), 3)
            
            john = Person.objects.filter(names__first_name='John').first()
            mary = Person.objects.filter(names__first_name='Mary').first()
            alex = Person.objects.filter(names__first_name='Alex').first()
            
            # Check gender values
            self.assertEqual(john.gender, Person.Gender.MALE)
            self.assertEqual(mary.gender, Person.Gender.FEMALE)
            self.assertEqual(alex.gender, Person.Gender.UNKNOWN)
            
        finally:
            os.unlink(temp_file)
    
    def test_import_complex_family_tree(self):
        """Test import with a complex multi-generation family tree"""
        complex_tree_gedcom = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME George /Washington/
2 GIVN George
2 SURN Washington
1 SEX M
1 BIRT
2 DATE 22 FEB 1732
2 PLAC Westmoreland County, VA, USA
1 DEAT
2 DATE 14 DEC 1799
2 PLAC Mount Vernon, VA, USA
0 @I2@ INDI
1 NAME Martha /Custis/
2 GIVN Martha
2 SURN Custis
1 SEX F
1 BIRT
2 DATE 13 JUN 1731
2 PLAC New Kent County, VA, USA
1 DEAT
2 DATE 22 MAY 1802
2 PLAC Mount Vernon, VA, USA
0 @I3@ INDI
1 NAME John /Washington/
2 GIVN John
2 SURN Washington
1 SEX M
1 BIRT
2 DATE 15 MAR 1755
2 PLAC Mount Vernon, VA, USA
1 DEAT
2 DATE 10 JUN 1800
2 PLAC Mount Vernon, VA, USA
0 @I4@ INDI
1 NAME Martha /Washington/
2 GIVN Martha
2 SURN Washington
1 SEX F
1 BIRT
2 DATE 20 JUL 1757
2 PLAC Mount Vernon, VA, USA
1 DEAT
2 DATE 25 SEP 1801
2 PLAC Mount Vernon, VA, USA
0 @I5@ INDI
1 NAME Eleanor /Washington/
2 GIVN Eleanor
2 SURN Washington
1 SEX F
1 BIRT
2 DATE 31 MAR 1759
2 PLAC Mount Vernon, VA, USA
1 DEAT
2 DATE 28 JUN 1799
2 PLAC Mount Vernon, VA, USA
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
1 CHIL @I4@
1 CHIL @I5@
1 MARR
2 DATE 06 JAN 1759
2 PLAC White House, VA, USA
0 TRLR"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(complex_tree_gedcom)
            temp_file = f.name
        
        try:
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Check all people were created
            self.assertEqual(Person.objects.count(), 5)
            
            # Check family relationships
            george = Person.objects.filter(names__first_name='George').first()
            martha = Person.objects.filter(names__first_name='Martha', names__last_name='Custis').first()
            
            # George should have 3 children
            self.assertEqual(george.children.count(), 3)
            
            # Martha should have 3 children
            self.assertEqual(martha.children.count(), 3)
            
            # Each child should have 2 parents
            for child in george.children.all():
                self.assertEqual(child.parents.count(), 2)
            
            # Check marriage
            self.assertEqual(george.spouse, martha)
            self.assertEqual(martha.spouse, george)
            
            # Check death events
            self.assertFalse(george.is_living)
            self.assertFalse(martha.is_living)
            
        finally:
            os.unlink(temp_file)
    
    def test_import_edge_cases(self):
        """Test import with various edge cases"""
        edge_cases_gedcom = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Unknown /Person/
2 GIVN Unknown
2 SURN Person
1 SEX U
0 @I2@ INDI
1 NAME John /Doe/
2 GIVN John
2 SURN Doe
1 SEX M
1 BIRT
2 DATE ABT 1900
0 @I3@ INDI
1 NAME Jane /Doe/
2 GIVN Jane
2 SURN Doe
1 SEX F
1 BIRT
2 DATE 1900
0 @I4@ INDI
1 NAME Bob /Smith/
2 GIVN Bob
2 SURN Smith
1 SEX M
1 BIRT
2 DATE 15 MAR 1980
1 DEAT
2 DATE 10 JUN 2020
0 TRLR"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(edge_cases_gedcom)
            temp_file = f.name
        
        try:
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Check people were created
            self.assertEqual(Person.objects.count(), 4)
            
            # Unknown person should be created
            unknown = Person.objects.filter(names__first_name='Unknown').first()
            self.assertIsNotNone(unknown)
            self.assertEqual(unknown.gender, Person.Gender.UNKNOWN)
            
            # Person with approximate birth date should be created
            john = Person.objects.filter(names__first_name='John').first()
            self.assertIsNotNone(john)
            
            # Person with death event should be marked as deceased
            bob = Person.objects.filter(names__first_name='Bob').first()
            self.assertIsNotNone(bob)
            self.assertFalse(bob.is_living)
            
        finally:
            os.unlink(temp_file)
    
    def test_import_large_dataset(self):
        """Test import with a larger dataset to check performance"""
        large_dataset = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8"""
        
        # Add 20 individuals
        for i in range(1, 21):
            large_dataset += f"""
0 @I{i}@ INDI
1 NAME Person{i} /Family{i}/
2 GIVN Person{i}
2 SURN Family{i}
1 SEX {'M' if i % 2 == 0 else 'F'}
1 BIRT
2 DATE {15 + (i % 15)} MAR {1980 + (i % 20)}
2 PLAC City{i}, State{i}, USA"""
        
        # Add 10 families
        for i in range(1, 11):
            large_dataset += f"""
0 @F{i}@ FAM
1 HUSB @I{i*2-1}@
1 WIFE @I{i*2}@
1 CHIL @I{i*2+1}@
1 MARR
2 DATE {10 + (i % 20)} JUN {2000 + (i % 10)}
2 PLAC Wedding{i}, USA"""
        
        large_dataset += "\n0 TRLR"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(large_dataset)
            temp_file = f.name
        
        try:
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Check all people were created
            self.assertEqual(Person.objects.count(), 20)
            
            # Check all names were created
            self.assertEqual(Name.objects.count(), 20)
            
            # Check birth events were created
            self.assertEqual(BirthEvent.objects.count(), 20)
            
            # Check marriage events were created (10 families * 2 records each)
            self.assertEqual(MarriageEvent.objects.count(), 20)
            
        finally:
            os.unlink(temp_file)


# Import date for the test cases
from datetime import date


class GEDCOMDuplicateImportTestCase(TestCase):
    """Test that duplicate imports don't create additional records"""
    
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
    
    def test_duplicate_import_no_changes(self):
        """Test that running the same import twice creates no additional records"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(self.sample_gedcom)
            temp_file = f.name
        
        try:
            # First import
            out1 = StringIO()
            call_command('import_gedcom', temp_file, '--no-pretend', stdout=out1)
            
            # Record counts after first import
            people_count_1 = Person.objects.count()
            names_count_1 = Name.objects.count()
            person_names_count_1 = PersonName.objects.count()
            birth_events_count_1 = BirthEvent.objects.count()
            death_events_count_1 = DeathEvent.objects.count()
            marriage_events_count_1 = MarriageEvent.objects.count()
            relationships_count_1 = ParentChildRelationship.objects.count()
            
            # Second import with same file
            out2 = StringIO()
            call_command('import_gedcom', temp_file, '--no-pretend', stdout=out2)
            
            # Record counts after second import
            people_count_2 = Person.objects.count()
            names_count_2 = Name.objects.count()
            person_names_count_2 = PersonName.objects.count()
            birth_events_count_2 = BirthEvent.objects.count()
            death_events_count_2 = DeathEvent.objects.count()
            marriage_events_count_2 = MarriageEvent.objects.count()
            relationships_count_2 = ParentChildRelationship.objects.count()
            
            # Verify no additional records were created
            self.assertEqual(people_count_1, people_count_2, "Person count should not change")
            self.assertEqual(names_count_1, names_count_2, "Name count should not change")
            self.assertEqual(person_names_count_1, person_names_count_2, "PersonName count should not change")
            self.assertEqual(birth_events_count_1, birth_events_count_2, "BirthEvent count should not change")
            self.assertEqual(death_events_count_1, death_events_count_2, "DeathEvent count should not change")
            self.assertEqual(marriage_events_count_2, marriage_events_count_1, "MarriageEvent count should not change")
            self.assertEqual(relationships_count_1, relationships_count_2, "ParentChildRelationship count should not change")
            
            # Check output shows duplicate detection
            output2 = out2.getvalue()
            self.assertIn('Found existing person', output2)
            self.assertIn('Individuals updated: 3', output2)  # All 3 individuals should be detected as existing
            self.assertIn('Individuals created: 0', output2)
            self.assertIn('Names created: 0', output2)
            self.assertIn('Names linked: 0', output2)
            self.assertIn('Events created: 0', output2)
            self.assertIn('Relationships created: 0', output2)
            
        finally:
            os.unlink(temp_file)
    
    def test_duplicate_import_name_reuse(self):
        """Test that names are properly reused and not duplicated"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(self.sample_gedcom)
            temp_file = f.name
        
        try:
            # First import
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Get the specific name objects
            john_smith_name = Name.objects.filter(first_name='John', last_name='Smith').first()
            mary_johnson_name = Name.objects.filter(first_name='Mary', last_name='Johnson').first()
            robert_smith_name = Name.objects.filter(first_name='Robert', last_name='Smith').first()
            
            self.assertIsNotNone(john_smith_name)
            self.assertIsNotNone(mary_johnson_name)
            self.assertIsNotNone(robert_smith_name)
            
            # Record the IDs
            john_smith_id = john_smith_name.id
            mary_johnson_id = mary_johnson_name.id
            robert_smith_id = robert_smith_name.id
            
            # Second import
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Verify the same name objects are still used (same IDs)
            john_smith_name_after = Name.objects.filter(first_name='John', last_name='Smith').first()
            mary_johnson_name_after = Name.objects.filter(first_name='Mary', last_name='Johnson').first()
            robert_smith_name_after = Name.objects.filter(first_name='Robert', last_name='Smith').first()
            
            self.assertEqual(john_smith_name_after.id, john_smith_id)
            self.assertEqual(mary_johnson_name_after.id, mary_johnson_id)
            self.assertEqual(robert_smith_name_after.id, robert_smith_id)
            
            # Verify only one Name object exists for each name
            self.assertEqual(Name.objects.filter(first_name='John', last_name='Smith').count(), 1)
            self.assertEqual(Name.objects.filter(first_name='Mary', last_name='Johnson').count(), 1)
            self.assertEqual(Name.objects.filter(first_name='Robert', last_name='Smith').count(), 1)
            
        finally:
            os.unlink(temp_file)
    
    def test_duplicate_import_event_reuse(self):
        """Test that events are not duplicated on second import"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(self.sample_gedcom)
            temp_file = f.name
        
        try:
            # First import
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Get specific people
            john = Person.objects.filter(names__first_name='John', names__last_name='Smith').first()
            mary = Person.objects.filter(names__first_name='Mary', names__last_name='Johnson').first()
            
            # Record event IDs
            john_birth_id = john.birth.id
            john_death_id = john.death.id
            marriage_id = MarriageEvent.objects.filter(person=john, other_person=mary).first().id
            
            # Second import
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Verify the same event objects are still used (same IDs)
            john_after = Person.objects.filter(names__first_name='John', names__last_name='Smith').first()
            mary_after = Person.objects.filter(names__first_name='Mary', names__last_name='Johnson').first()
            
            self.assertEqual(john_after.birth.id, john_birth_id)
            self.assertEqual(john_after.death.id, john_death_id)
            
            marriage_after = MarriageEvent.objects.filter(person=john_after, other_person=mary_after).first()
            self.assertEqual(marriage_after.id, marriage_id)
            
            # Verify only one event of each type per person
            self.assertEqual(BirthEvent.objects.filter(person=john_after).count(), 1)
            self.assertEqual(DeathEvent.objects.filter(person=john_after).count(), 1)
            self.assertEqual(MarriageEvent.objects.filter(person=john_after, other_person=mary_after).count(), 1)
            
        finally:
            os.unlink(temp_file)
    
    def test_duplicate_import_relationship_reuse(self):
        """Test that relationships are not duplicated on second import"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(self.sample_gedcom)
            temp_file = f.name
        
        try:
            # First import
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Get specific people
            john = Person.objects.filter(names__first_name='John', names__last_name='Smith').first()
            mary = Person.objects.filter(names__first_name='Mary', names__last_name='Johnson').first()
            robert = Person.objects.filter(names__first_name='Robert', names__last_name='Smith').first()
            
            # Record relationship IDs
            john_robert_relationship = ParentChildRelationship.objects.filter(parent=john, child=robert).first()
            mary_robert_relationship = ParentChildRelationship.objects.filter(parent=mary, child=robert).first()
            
            john_robert_id = john_robert_relationship.id
            mary_robert_id = mary_robert_relationship.id
            
            # Second import
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Verify the same relationship objects are still used (same IDs)
            john_after = Person.objects.filter(names__first_name='John', names__last_name='Smith').first()
            mary_after = Person.objects.filter(names__first_name='Mary', names__last_name='Johnson').first()
            robert_after = Person.objects.filter(names__first_name='Robert', names__last_name='Smith').first()
            
            john_robert_after = ParentChildRelationship.objects.filter(parent=john_after, child=robert_after).first()
            mary_robert_after = ParentChildRelationship.objects.filter(parent=mary_after, child=robert_after).first()
            
            self.assertEqual(john_robert_after.id, john_robert_id)
            self.assertEqual(mary_robert_after.id, mary_robert_id)
            
            # Verify only one relationship between each parent-child pair
            self.assertEqual(ParentChildRelationship.objects.filter(parent=john_after, child=robert_after).count(), 1)
            self.assertEqual(ParentChildRelationship.objects.filter(parent=mary_after, child=robert_after).count(), 1)
            
        finally:
            os.unlink(temp_file)
    
    def test_duplicate_import_name_type_verification(self):
        """Test that imported names use the correct 'OTHER' type"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(self.sample_gedcom)
            temp_file = f.name
        
        try:
            # First import
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Get people and verify their names use 'OTHER' type
            john = Person.objects.filter(names__first_name='John', names__last_name='Smith').first()
            mary = Person.objects.filter(names__first_name='Mary', names__last_name='Johnson').first()
            robert = Person.objects.filter(names__first_name='Robert', names__last_name='Smith').first()
            
            # Check that all imported names use 'OTHER' type
            john_name_relationship = PersonName.objects.filter(person=john).first()
            mary_name_relationship = PersonName.objects.filter(person=mary).first()
            robert_name_relationship = PersonName.objects.filter(person=robert).first()
            
            self.assertEqual(john_name_relationship.name_type, PersonName.Type.OTHER)
            self.assertEqual(mary_name_relationship.name_type, PersonName.Type.OTHER)
            self.assertEqual(robert_name_relationship.name_type, PersonName.Type.OTHER)
            
            # Second import should not change the name types
            call_command('import_gedcom', temp_file, '--no-pretend')
            
            # Verify name types are still 'OTHER'
            john_after = Person.objects.filter(names__first_name='John', names__last_name='Smith').first()
            mary_after = Person.objects.filter(names__first_name='Mary', names__last_name='Johnson').first()
            robert_after = Person.objects.filter(names__first_name='Robert', names__last_name='Smith').first()
            
            john_name_relationship_after = PersonName.objects.filter(person=john_after).first()
            mary_name_relationship_after = PersonName.objects.filter(person=mary_after).first()
            robert_name_relationship_after = PersonName.objects.filter(person=robert_after).first()
            
            self.assertEqual(john_name_relationship_after.name_type, PersonName.Type.OTHER)
            self.assertEqual(mary_name_relationship_after.name_type, PersonName.Type.OTHER)
            self.assertEqual(robert_name_relationship_after.name_type, PersonName.Type.OTHER)
            
        finally:
            os.unlink(temp_file)