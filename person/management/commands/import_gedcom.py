import os
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Set
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.exceptions import ValidationError
from person.models import (
    Person, Name, PersonName, ParentChildRelationship,
    BirthEvent, DeathEvent, MarriageEvent, DivorceEvent,
    ImmigrationEvent, CitizenshipEvent, PersonAttachment
)


class GEDCOMParser:
    """Parser for GEDCOM files"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.individuals = {}
        self.families = {}
        self.current_record = None
        self.current_level = 0
        
    def parse(self) -> Tuple[Dict, Dict]:
        """Parse the GEDCOM file and return individuals and families"""
        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    self._parse_line(line, line_num)
                except Exception as e:
                    print(f"Warning: Error parsing line {line_num}: {e}")
                    
        return self.individuals, self.families
    
    def _parse_line(self, line: str, line_num: int):
        """Parse a single GEDCOM line"""
        # GEDCOM format: level @id@ tag value
        # or: level tag value
        parts = line.split(' ', 2)
        if len(parts) < 2:
            return
            
        level = int(parts[0])
        tag_or_id = parts[1]
        value = parts[2] if len(parts) > 2 else ""
        
        # Check if this is an ID (starts and ends with @)
        if tag_or_id.startswith('@') and tag_or_id.endswith('@'):
            record_id = tag_or_id
            tag = value
            value = ""
            if len(parts) > 2:
                value = parts[2]
        else:
            record_id = None
            tag = tag_or_id
            
        # Handle different record types
        if level == 0:
            if tag == 'INDI':
                self.current_record = {'id': record_id, 'type': 'INDI', 'data': {}}
                self.individuals[record_id] = self.current_record
            elif tag == 'FAM':
                self.current_record = {'id': record_id, 'type': 'FAM', 'data': {}}
                self.families[record_id] = self.current_record
            else:
                self.current_record = None
        elif self.current_record and level == 1:
            # Handle multi-value fields like CHIL
            if tag in ['CHIL', 'HUSB', 'WIFE']:
                if tag not in self.current_record['data']:
                    self.current_record['data'][tag] = []
                self.current_record['data'][tag].append(value)
            elif tag in ['BIRT', 'DEAT', 'MARR']:
                self.current_record['data'][tag] = {}
            else:
                self.current_record['data'][tag] = value
        elif self.current_record and level == 2:
            # Handle nested data like BIRT DATE, BIRT PLAC, etc.
            # Find the most recent level 1 tag that was a dict
            parent_tag = None
            for tag_name in list(self.current_record['data'].keys())[::-1]:
                if isinstance(self.current_record['data'][tag_name], dict):
                    parent_tag = tag_name
                    break
            
            if parent_tag:
                if tag not in self.current_record['data'][parent_tag]:
                    self.current_record['data'][parent_tag][tag] = value


class PersonMatcher:
    """Heuristic matching for finding existing people in the database"""
    
    @staticmethod
    def find_matching_person(gedcom_person: Dict, existing_people: List[Person], strict: bool = True) -> Optional[Person]:
        if not existing_people:
            return None
        name_info = gedcom_person.get('NAME', '')
        if not isinstance(name_info, str):
            name_info = ''
        first_name, middle_name, last_name = PersonMatcher._parse_name(name_info)
        birth_date = None
        birt = gedcom_person.get('BIRT')
        if isinstance(birt, dict):
            birth_date = PersonMatcher._parse_date(birt.get('DATE', ''))
        for person in existing_people:
            for person_name in person.names.all():
                # Strict: require exact first, last, and birth date if present
                if strict:
                    if (first_name and last_name and
                        first_name.lower() == person_name.first_name.lower() and
                        last_name.lower() == person_name.last_name.lower()):
                        if birth_date and person.birth and person.birth.date:
                            if birth_date == person.birth.date:
                                return person
                        elif not birth_date:
                            return person
                else:
                    name_match = (first_name.lower() in person_name.first_name.lower() or
                                  person_name.first_name.lower() in first_name.lower()) and \
                                 (last_name.lower() in person_name.last_name.lower() or
                                  person_name.last_name.lower() in last_name.lower())
                    if name_match:
                        if birth_date and person.birth and person.birth.date:
                            date_diff = abs((birth_date - person.birth.date).days)
                            if date_diff <= 366:
                                return person
                        else:
                            return person
        return None
    
    @staticmethod
    def _parse_name(name_str: str) -> Tuple[str, str, str]:
        """Parse GEDCOM name format: Given /Surname/ or Given Surname"""
        if not isinstance(name_str, str) or not name_str:
            return "", "", ""
        # Handle /Surname/ format (e.g., "John /Smith/" or "John Michael /Smith/")
        if '/' in name_str:
            # Split by '/' and remove empty parts
            parts = [part.strip() for part in name_str.split('/') if part.strip()]
            if len(parts) >= 2:
                # Everything before the first / is the given name
                given_part = parts[0]
                surname = parts[1]
                # Split given part to separate first and middle names
                given_names = given_part.split()
                if len(given_names) == 1:
                    return given_names[0], "", surname
                else:
                    return given_names[0], " ".join(given_names[1:]), surname
        # Handle space-separated format
        parts = name_str.strip().split()
        if len(parts) == 1:
            return parts[0], "", ""
        elif len(parts) == 2:
            return parts[0], "", parts[1]
        else:
            # For names with more than 2 parts, first is given, last is surname, rest is middle
            return parts[0], " ".join(parts[1:-1]), parts[-1]
    
    @staticmethod
    def _parse_date(date_str: str) -> Optional[date]:
        """Parse GEDCOM date format"""
        if not date_str:
            return None
            
        # Common GEDCOM date formats
        date_patterns = [
            r'(\d{1,2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{4})',
            r'(\d{4})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
        ]
        
        month_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
        }
        
        for pattern in date_patterns:
            match = re.match(pattern, date_str.upper())
            if match:
                if len(match.groups()) == 3:
                    if pattern == date_patterns[0]:  # DD MMM YYYY
                        day, month, year = match.groups()
                        return date(int(year), month_map[month], int(day))
                    else:  # MM/DD/YYYY
                        month, day, year = match.groups()
                        return date(int(year), int(month), int(day))
                elif len(match.groups()) == 1:  # YYYY
                    year = int(match.group(1))
                    return date(year, 1, 1)  # Use January 1st as default
        
        return None
    
    @staticmethod
    def _calculate_match_score(person: Person, first_name: str, middle_name: str, 
                             last_name: str, birth_date: Optional[date]) -> float:
        """Calculate a match score between 0 and 1"""
        score = 0.0
        total_weight = 0.0
        
        # Check names
        for person_name in person.names.all():
            name_score = 0.0
            
            # Last name match (highest weight)
            if last_name and person_name.last_name:
                if last_name.lower() == person_name.last_name.lower():
                    name_score += 0.4
                elif last_name.lower() in person_name.last_name.lower() or person_name.last_name.lower() in last_name.lower():
                    name_score += 0.2
            
            # First name match
            if first_name and person_name.first_name:
                if first_name.lower() == person_name.first_name.lower():
                    name_score += 0.3
                elif first_name.lower() in person_name.first_name.lower() or person_name.first_name.lower() in first_name.lower():
                    name_score += 0.15
            
            # Middle name match
            if middle_name and person_name.middle_name:
                if middle_name.lower() == person_name.middle_name.lower():
                    name_score += 0.2
                elif middle_name.lower() in person_name.middle_name.lower() or person_name.middle_name.lower() in middle_name.lower():
                    name_score += 0.1
            
            score = max(score, name_score)
        
        total_weight += 0.9  # Name weight
        
        # Check birth date
        if birth_date and person.birth and person.birth.date:
            date_diff = abs((birth_date - person.birth.date).days)
            if date_diff == 0:
                score += 0.1
            elif date_diff <= 365:  # Within a year
                score += 0.05
            total_weight += 0.1
        
        return score / total_weight if total_weight > 0 else 0.0


class GEDCOMImporter:
    """Import GEDCOM data into the database"""
    
    def __init__(self, pretend: bool = True, stdout=None):
        self.pretend = pretend
        self.stats = {
            'individuals_created': 0,
            'individuals_updated': 0,
            'families_created': 0,
            'relationships_created': 0,
            'events_created': 0,
            'errors': []
        }
        self.stdout = stdout
    def _write(self, msg):
        if self.stdout:
            self.stdout.write(msg + '\n')
            self.stdout.flush()
        else:
            print(msg, flush=True)
    def import_gedcom(self, file_path: str):
        """Import a GEDCOM file"""
        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")
        self._write(f"Parsing GEDCOM file: {file_path}")
        parser = GEDCOMParser(file_path)
        individuals, families = parser.parse()
        self._write(f"Found {len(individuals)} individuals and {len(families)} families")
        if self.pretend:
            self._write("PRETEND MODE: No changes will be made to the database")
        # Import individuals first
        person_map = {}  # GEDCOM ID -> Django Person
        existing_people = list(Person.objects.all())
        for gedcom_id, individual in individuals.items():
            try:
                person = self._import_individual(individual, existing_people)
                if person:
                    person_map[gedcom_id] = person
                    # Add to existing_people for future duplicate detection
                    if not self.pretend and person not in existing_people:
                        existing_people.append(person)
            except Exception as e:
                error_msg = f"Error importing individual {gedcom_id}: {e}"
                self.stats['errors'].append(error_msg)
                self._write(f"ERROR: {error_msg}")
        # Import families and relationships
        for family_id, family in families.items():
            try:
                self._import_family(family, person_map)
            except Exception as e:
                error_msg = f"Error importing family {family_id}: {e}"
                self.stats['errors'].append(error_msg)
                self._write(f"ERROR: {error_msg}")
        # Print summary
        self._print_summary()
    def _import_individual(self, individual: Dict, existing_people: List[Person]) -> Optional[Person]:
        gedcom_id = individual['id']
        data = individual['data']
        # Extract name
        name_info = data.get('NAME', '')
        if not isinstance(name_info, str):
            name_info = ''
        first_name, middle_name, last_name = PersonMatcher._parse_name(name_info)
        if not first_name and not last_name:
            self._write(f"Warning: Individual {gedcom_id} has no valid name")
            return None
        # Check for existing person
        existing_person = PersonMatcher.find_matching_person(data, existing_people, strict=True)
        if existing_person:
            self._write(f"Found existing person: {existing_person}")
            person = existing_person
            self.stats['individuals_updated'] += 1
        else:
            if not self.pretend:
                person = Person.objects.create()
                self.stats['individuals_created'] += 1
            else:
                person = Person()  # Dummy object for pretend mode
                self.stats['individuals_created'] += 1
            self._write(f"Creating new person: {first_name} {last_name}")
        # Create or update name
        if not self.pretend:
            name, created = Name.objects.get_or_create(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name
            )
            # Link name to person
            PersonName.objects.get_or_create(
                person=person,
                name=name,
                defaults={'name_type': PersonName.Type.BIRTH}
            )
        # Import events
        self._import_events(person, data)
        return person
    def _import_events(self, person: Person, data: Dict):
        """Import events for a person"""
        # Birth event
        if 'BIRT' in data:
            birth_data = data['BIRT']
            if not isinstance(birth_data, dict):
                birth_data = {}
            birth_date = PersonMatcher._parse_date(birth_data.get('DATE', ''))
            birth_location = birth_data.get('PLAC', '')
            if not self.pretend and birth_date:
                BirthEvent.objects.get_or_create(
                    person=person,
                    defaults={
                        'date': birth_date,
                        'location': birth_location
                    }
                )
                self.stats['events_created'] += 1
        # Death event
        if 'DEAT' in data:
            death_data = data['DEAT']
            if not isinstance(death_data, dict):
                death_data = {}
            death_date = PersonMatcher._parse_date(death_data.get('DATE', ''))
            death_location = death_data.get('PLAC', '')
            death_cause = death_data.get('CAUS', '')
            if not self.pretend and death_date:
                DeathEvent.objects.get_or_create(
                    person=person,
                    defaults={
                        'date': death_date,
                        'location': death_location,
                        'cause': death_cause
                    }
                )
                self.stats['events_created'] += 1
    def _import_family(self, family: Dict, person_map: Dict):
        """Import a family and its relationships"""
        data = family['data']
        # Get family members
        husband_id = data.get('HUSB', [''])[0] if isinstance(data.get('HUSB'), list) else data.get('HUSB', '')
        wife_id = data.get('WIFE', [''])[0] if isinstance(data.get('WIFE'), list) else data.get('WIFE', '')
        children_ids = data.get('CHIL', []) if isinstance(data.get('CHIL'), list) else [data.get('CHIL')] if data.get('CHIL') else []
        husband = person_map.get(husband_id)
        wife = person_map.get(wife_id)
        # Create marriage event if both spouses exist
        if husband and wife:
            marriage_data = data.get('MARR', {})
            if not isinstance(marriage_data, dict):
                marriage_data = {}
            marriage_date = PersonMatcher._parse_date(marriage_data.get('DATE', ''))
            marriage_location = marriage_data.get('PLAC', '')
            if not self.pretend and marriage_date:
                # Only create one marriage event per couple per date
                if not MarriageEvent.objects.filter(
                    person=husband, other_person=wife, date=marriage_date
                ).exists() and not MarriageEvent.objects.filter(
                    person=wife, other_person=husband, date=marriage_date
                ).exists():
                    MarriageEvent.objects.create(
                        person=husband,
                        other_person=wife,
                        date=marriage_date,
                        location=marriage_location
                    )
                    self.stats['events_created'] += 1
            # Create parent-child relationships
            for child_id in children_ids:
                if child_id:  # Skip empty child IDs
                    child = person_map.get(child_id)
                    if child:
                        if not self.pretend:
                            # Create parent-child relationships
                            if husband:
                                ParentChildRelationship.objects.get_or_create(
                                    parent=husband,
                                    child=child
                                )
                            if wife:
                                ParentChildRelationship.objects.get_or_create(
                                    parent=wife,
                                    child=child
                                )
                            self.stats['relationships_created'] += 1
    def _print_summary(self):
        self._write("\n" + "="*50)
        self._write("IMPORT SUMMARY")
        self._write("="*50)
        self._write(f"Individuals created: {self.stats['individuals_created']}")
        self._write(f"Individuals updated: {self.stats['individuals_updated']}")
        self._write(f"Events created: {self.stats['events_created']}")
        self._write(f"Relationships created: {self.stats['relationships_created']}")
        if self.stats['errors']:
            self._write(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors']:
                self._write(f"  - {error}")
        if self.pretend:
            self._write("\nThis was a pretend run. No changes were made to the database.")
            self._write("Use --no-pretend to actually import the data.")


class Command(BaseCommand):
    help = 'Import a GEDCOM file into the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the GEDCOM file'
        )
        parser.add_argument(
            '--no-pretend',
            action='store_true',
            help='Actually import the data (default is pretend mode)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )
    
    def handle(self, *args, **options):
        file_path = options['file_path']
        pretend = not options['no_pretend']
        verbose = options['verbose']
        
        if verbose:
            print(f"File path: {file_path}")
            print(f"Pretend mode: {pretend}")
        
        try:
            importer = GEDCOMImporter(pretend=pretend, stdout=self.stdout)
            importer.import_gedcom(file_path)
        except Exception as e:
            raise CommandError(f"Import failed: {e}") 