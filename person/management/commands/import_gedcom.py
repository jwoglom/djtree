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
from person.management.util.person_matcher import PersonMatcher


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
            elif tag in ['BIRT', 'DEAT', 'MARR', 'DIV', 'EMIG', 'IMMI', 'NATU']:
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
        elif self.current_record and level == 3:
            # Handle level 3 tags like PLAC_TO, PLAC_FROM
            # Find the most recent level 1 tag that was a dict
            parent_tag = None
            for tag_name in list(self.current_record['data'].keys())[::-1]:
                if isinstance(self.current_record['data'][tag_name], dict):
                    parent_tag = tag_name
                    break
            
            if parent_tag:
                if tag not in self.current_record['data'][parent_tag]:
                    self.current_record['data'][parent_tag][tag] = value


class GEDCOMImporter:
    """Import GEDCOM data into the database"""
    
    def __init__(self, pretend: bool = True, strict: bool = True, stdout=None):
        self.pretend = pretend
        self.strict = strict
        self.stats = {
            'individuals_created': 0,
            'individuals_updated': 0,
            'families_created': 0,
            'relationships_created': 0,
            'events_created': 0,
            'names_created': 0,
            'names_linked': 0,
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
            self._write("Showing what would be imported:")
            self._write("="*50)
        
        # Import individuals first
        person_map = {}  # GEDCOM ID -> Django Person
        existing_people = list(Person.objects.all())
        
        self._write(f"\nProcessing {len(individuals)} individuals...")
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
        self._write(f"\nProcessing {len(families)} families...")
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
        
        self._write(f"Processing individual {gedcom_id}: {first_name} {middle_name} {last_name}")
        
        # Check for existing person
        existing_person = PersonMatcher.find_matching_person(data, existing_people, strict=self.strict)
        if existing_person:
            self._write(f"  Found existing person: {existing_person}")
            person = existing_person
            self.stats['individuals_updated'] += 1
        else:
            if self.pretend:
                self._write(f"  Would create new person: {first_name} {last_name}")
                # Create a mock person object with a fake ID for pretend mode
                person = type('MockPerson', (), {'id': f"mock_{gedcom_id}", '__str__': lambda self: f"<MockPerson: {first_name} {last_name}>"})()
            else:
                person = Person.objects.create()
                self._write(f"  Created new person: {first_name} {last_name}")
            self.stats['individuals_created'] += 1
        
        # Create or update name
        if self.pretend:
            self._write(f"  Would check for existing name: {first_name} {middle_name} {last_name}")
            self._write(f"  Would add name with type 'OTHER' if not already linked to person")
            self.stats['names_created'] += 1
            self.stats['names_linked'] += 1
        else:
            # Check if this name already exists
            name, name_created = Name.objects.get_or_create(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name
            )
            
            if name_created:
                self._write(f"  Created new name: {first_name} {middle_name} {last_name}")
                self.stats['names_created'] += 1
            else:
                self._write(f"  Found existing name: {first_name} {middle_name} {last_name}")
            
            # Only link the name to the person if it's not already linked
            person_name, relationship_created = PersonName.objects.get_or_create(
                person=person,
                name=name,
                defaults={'name_type': PersonName.Type.OTHER}
            )
            
            if relationship_created:
                self._write(f"  Linked name to person with type 'OTHER'")
                self.stats['names_linked'] += 1
            else:
                self._write(f"  Name already linked to person (skipping)")
        
        # Import events
        self._import_events(person, data)
        # Import gender
        self._import_gender(person, data)
        return person
    
    def _import_gender(self, person: Person, data: Dict):
        """Import gender from GEDCOM SEX field"""
        sex = data.get('SEX', '')
        if sex:
            gender_map = {'M': Person.Gender.MALE, 'F': Person.Gender.FEMALE, 'U': Person.Gender.UNKNOWN}
            gender = gender_map.get(sex, Person.Gender.UNKNOWN)
            
            if self.pretend:
                self._write(f"  Would set gender to: {gender} (from SEX: {sex})")
            else:
                person.gender = gender
                person.save(update_fields=['gender'])
                self._write(f"  Set gender to: {gender} (from SEX: {sex})")
    
    def _import_events(self, person: Person, data: Dict):
        """Import events for a person"""
        # Birth event
        if 'BIRT' in data:
            birth_data = data['BIRT']
            if not isinstance(birth_data, dict):
                birth_data = {}
            birth_date = PersonMatcher._parse_date(birth_data.get('DATE', ''))
            birth_location = birth_data.get('PLAC', '')
            if birth_date:
                if self.pretend:
                    self._write(f"  Would create BirthEvent: date={birth_date}, location='{birth_location}'")
                    self.stats['events_created'] += 1
                else:
                    birth_event, created = BirthEvent.objects.get_or_create(
                        person=person,
                        defaults={
                            'date': birth_date,
                            'location': birth_location
                        }
                    )
                    if created:
                        self._write(f"  Created BirthEvent: date={birth_date}, location='{birth_location}'")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  BirthEvent already exists for {person}")
            elif birth_location:
                if self.pretend:
                    self._write(f"  Would create BirthEvent: location='{birth_location}' (no date)")
                    self.stats['events_created'] += 1
                else:
                    birth_event, created = BirthEvent.objects.get_or_create(
                        person=person,
                        defaults={'location': birth_location}
                    )
                    if created:
                        self._write(f"  Created BirthEvent: location='{birth_location}' (no date)")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  BirthEvent already exists for {person}")
        
        # Death event
        if 'DEAT' in data:
            death_data = data['DEAT']
            if not isinstance(death_data, dict):
                death_data = {}
            death_date = PersonMatcher._parse_date(death_data.get('DATE', ''))
            death_location = death_data.get('PLAC', '')
            death_cause = death_data.get('CAUS', '')
            if death_date:
                if self.pretend:
                    self._write(f"  Would create DeathEvent: date={death_date}, location='{death_location}', cause='{death_cause}'")
                    self.stats['events_created'] += 1
                else:
                    death_event, created = DeathEvent.objects.get_or_create(
                        person=person,
                        defaults={
                            'date': death_date,
                            'location': death_location,
                            'cause': death_cause
                        }
                    )
                    if created:
                        self._write(f"  Created DeathEvent: date={death_date}, location='{death_location}', cause='{death_cause}'")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  DeathEvent already exists for {person}")
            elif death_location or death_cause:
                if self.pretend:
                    self._write(f"  Would create DeathEvent: location='{death_location}', cause='{death_cause}' (no date)")
                    self.stats['events_created'] += 1
                else:
                    death_event, created = DeathEvent.objects.get_or_create(
                        person=person,
                        defaults={
                            'location': death_location,
                            'cause': death_cause
                        }
                    )
                    if created:
                        self._write(f"  Created DeathEvent: location='{death_location}', cause='{death_cause}' (no date)")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  DeathEvent already exists for {person}")
        
        # Immigration event
        if 'IMMI' in data:
            immi_data = data['IMMI']
            if not isinstance(immi_data, dict):
                immi_data = {}
            immi_date = PersonMatcher._parse_date(immi_data.get('DATE', ''))
            immi_location = immi_data.get('PLAC', '')
            from_place = immi_data.get('PLAC_FROM', '')
            to_place = immi_data.get('PLAC_TO', '')
            if immi_date:
                if self.pretend:
                    self._write(f"  Would create ImmigrationEvent: date={immi_date}, from='{from_place}', to='{immi_location}', location='{immi_location}'")
                    self.stats['events_created'] += 1
                else:
                    # For IMMI, the PLAC is the destination, PLAC_FROM is the origin
                    immi_event, created = ImmigrationEvent.objects.get_or_create(
                        person=person,
                        date=immi_date,
                        defaults={
                            'from_country': from_place,
                            'to_country': immi_location,  # Use PLAC as destination
                            'location': immi_location
                        }
                    )
                    if created:
                        self._write(f"  Created ImmigrationEvent: date={immi_date}, from='{from_place}', to='{immi_location}', location='{immi_location}'")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  ImmigrationEvent already exists for {person}")
            elif immi_location or from_place:
                if self.pretend:
                    self._write(f"  Would create ImmigrationEvent: from='{from_place}', to='{immi_location}', location='{immi_location}' (no date)")
                    self.stats['events_created'] += 1
                else:
                    immi_event, created = ImmigrationEvent.objects.get_or_create(
                        person=person,
                        defaults={
                            'from_country': from_place,
                            'to_country': immi_location,
                            'location': immi_location
                        }
                    )
                    if created:
                        self._write(f"  Created ImmigrationEvent: from='{from_place}', to='{immi_location}', location='{immi_location}' (no date)")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  ImmigrationEvent already exists for {person}")
        
        # Emigration event (also immigration-related)
        if 'EMIG' in data:
            emig_data = data['EMIG']
            if not isinstance(emig_data, dict):
                emig_data = {}
            emig_date = PersonMatcher._parse_date(emig_data.get('DATE', ''))
            emig_location = emig_data.get('PLAC', '')
            to_place = emig_data.get('PLAC_TO', '')
            if emig_date:
                if self.pretend:
                    self._write(f"  Would create ImmigrationEvent (emigration): date={emig_date}, from='{emig_location}', to='{to_place}', location='{emig_location}'")
                    self.stats['events_created'] += 1
                else:
                    emig_event, created = ImmigrationEvent.objects.get_or_create(
                        person=person,
                        date=emig_date,
                        defaults={
                            'from_country': emig_location,
                            'to_country': to_place,
                            'location': emig_location
                        }
                    )
                    if created:
                        self._write(f"  Created ImmigrationEvent (emigration): date={emig_date}, from='{emig_location}', to='{to_place}', location='{emig_location}'")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  ImmigrationEvent (emigration) already exists for {person}")
            elif emig_location or to_place:
                if self.pretend:
                    self._write(f"  Would create ImmigrationEvent (emigration): from='{emig_location}', to='{to_place}', location='{emig_location}' (no date)")
                    self.stats['events_created'] += 1
                else:
                    emig_event, created = ImmigrationEvent.objects.get_or_create(
                        person=person,
                        defaults={
                            'from_country': emig_location,
                            'to_country': to_place,
                            'location': emig_location
                        }
                    )
                    if created:
                        self._write(f"  Created ImmigrationEvent (emigration): from='{emig_location}', to='{to_place}', location='{emig_location}' (no date)")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  ImmigrationEvent (emigration) already exists for {person}")
        
        # Citizenship event
        if 'NATU' in data:
            natu_data = data['NATU']
            if not isinstance(natu_data, dict):
                natu_data = {}
            natu_date = PersonMatcher._parse_date(natu_data.get('DATE', ''))
            natu_location = natu_data.get('PLAC', '')
            if natu_date:
                if self.pretend:
                    self._write(f"  Would create CitizenshipEvent: date={natu_date}, country='{natu_location}', location='{natu_location}'")
                    self.stats['events_created'] += 1
                else:
                    natu_event, created = CitizenshipEvent.objects.get_or_create(
                        person=person,
                        date=natu_date,
                        defaults={
                            'country': natu_location,
                            'location': natu_location
                        }
                    )
                    if created:
                        self._write(f"  Created CitizenshipEvent: date={natu_date}, country='{natu_location}', location='{natu_location}'")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  CitizenshipEvent already exists for {person}")
            elif natu_location:
                if self.pretend:
                    self._write(f"  Would create CitizenshipEvent: country='{natu_location}', location='{natu_location}' (no date)")
                    self.stats['events_created'] += 1
                else:
                    natu_event, created = CitizenshipEvent.objects.get_or_create(
                        person=person,
                        defaults={
                            'country': natu_location,
                            'location': natu_location
                        }
                    )
                    if created:
                        self._write(f"  Created CitizenshipEvent: country='{natu_location}', location='{natu_location}' (no date)")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  CitizenshipEvent already exists for {person}")
    def _import_family(self, family: Dict, person_map: Dict):
        """Import a family and its relationships"""
        data = family['data']
        family_id = family['id']
        
        # Get family members
        husband_id = data.get('HUSB', [''])[0] if isinstance(data.get('HUSB'), list) else data.get('HUSB', '')
        wife_id = data.get('WIFE', [''])[0] if isinstance(data.get('WIFE'), list) else data.get('WIFE', '')
        children_ids = data.get('CHIL', []) if isinstance(data.get('CHIL'), list) else [data.get('CHIL')] if data.get('CHIL') else []
        
        husband = person_map.get(husband_id)
        wife = person_map.get(wife_id)
        
        self._write(f"Processing family {family_id}:")
        self._write(f"  Husband: {husband_id} -> {husband}")
        self._write(f"  Wife: {wife_id} -> {wife}")
        self._write(f"  Children: {children_ids}")
        
        # Create marriage event if both spouses exist
        if husband and wife:
            marriage_data = data.get('MARR', {})
            if not isinstance(marriage_data, dict):
                marriage_data = {}
            marriage_date = PersonMatcher._parse_date(marriage_data.get('DATE', ''))
            marriage_location = marriage_data.get('PLAC', '')
            
            if marriage_date:
                if self.pretend:
                    self._write(f"  Would create MarriageEvent: {husband} + {wife}, date={marriage_date}, location='{marriage_location}'")
                    self.stats['events_created'] += 1
                else:
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
                        self._write(f"  Created MarriageEvent: {husband} + {wife}, date={marriage_date}, location='{marriage_location}'")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  MarriageEvent already exists for {husband} + {wife} on {marriage_date}")
            elif marriage_location:
                if self.pretend:
                    self._write(f"  Would create MarriageEvent: {husband} + {wife}, location='{marriage_location}' (no date)")
                    self.stats['events_created'] += 1
                else:
                    MarriageEvent.objects.get_or_create(
                        person=husband,
                        other_person=wife,
                        defaults={'location': marriage_location}
                    )
                    self._write(f"  Created MarriageEvent: {husband} + {wife}, location='{marriage_location}' (no date)")
                    self.stats['events_created'] += 1
            
            # Create divorce event if present
            divorce_data = data.get('DIV', {})
            if not isinstance(divorce_data, dict):
                divorce_data = {}
            divorce_date = PersonMatcher._parse_date(divorce_data.get('DATE', ''))
            divorce_location = divorce_data.get('PLAC', '')
            
            if divorce_date:
                if self.pretend:
                    self._write(f"  Would create DivorceEvent: {husband} + {wife}, date={divorce_date}, location='{divorce_location}'")
                    self.stats['events_created'] += 1
                else:
                    # Only create one divorce event per couple per date
                    if not DivorceEvent.objects.filter(
                        person=husband, other_person=wife, date=divorce_date
                    ).exists() and not DivorceEvent.objects.filter(
                        person=wife, other_person=husband, date=divorce_date
                    ).exists():
                        DivorceEvent.objects.create(
                            person=husband,
                            other_person=wife,
                            date=divorce_date,
                            location=divorce_location
                        )
                        self._write(f"  Created DivorceEvent: {husband} + {wife}, date={divorce_date}, location='{divorce_location}'")
                        self.stats['events_created'] += 1
                    else:
                        self._write(f"  DivorceEvent already exists for {husband} + {wife} on {divorce_date}")
            elif divorce_location:
                if self.pretend:
                    self._write(f"  Would create DivorceEvent: {husband} + {wife}, location='{divorce_location}' (no date)")
                    self.stats['events_created'] += 1
                else:
                    DivorceEvent.objects.get_or_create(
                        person=husband,
                        other_person=wife,
                        defaults={'location': divorce_location}
                    )
                    self._write(f"  Created DivorceEvent: {husband} + {wife}, location='{divorce_location}' (no date)")
                    self.stats['events_created'] += 1
            
            # Create parent-child relationships
            for child_id in children_ids:
                if child_id:  # Skip empty child IDs
                    child = person_map.get(child_id)
                    if child:
                        if self.pretend:
                            if husband:
                                self._write(f"  Would create parent-child relationship: {husband} -> {child}")
                            if wife:
                                self._write(f"  Would create parent-child relationship: {wife} -> {child}")
                            self.stats['relationships_created'] += 1
                        else:
                            # Create parent-child relationships
                            if husband:
                                relationship, created = ParentChildRelationship.objects.get_or_create(
                                    parent=husband,
                                    child=child
                                )
                                if created:
                                    self._write(f"  Created parent-child relationship: {husband} -> {child}")
                                    self.stats['relationships_created'] += 1
                                else:
                                    self._write(f"  Parent-child relationship already exists: {husband} -> {child}")
                            if wife:
                                relationship, created = ParentChildRelationship.objects.get_or_create(
                                    parent=wife,
                                    child=child
                                )
                                if created:
                                    self._write(f"  Created parent-child relationship: {wife} -> {child}")
                                    self.stats['relationships_created'] += 1
                                else:
                                    self._write(f"  Parent-child relationship already exists: {wife} -> {child}")
                    else:
                        self._write(f"  Warning: Child {child_id} not found in person map")
                else:
                    self._write(f"  Warning: Empty child ID in family {family_id}")
        else:
            if not husband and not wife:
                self._write(f"  Warning: No spouses found for family {family_id}")
            elif not husband:
                self._write(f"  Warning: Husband {husband_id} not found for family {family_id}")
            elif not wife:
                self._write(f"  Warning: Wife {wife_id} not found for family {family_id}")
    def _print_summary(self):
        self._write("\n" + "="*50)
        self._write("IMPORT SUMMARY")
        self._write("="*50)
        self._write(f"Individuals created: {self.stats['individuals_created']}")
        self._write(f"Individuals updated: {self.stats['individuals_updated']}")
        self._write(f"Names created: {self.stats['names_created']}")
        self._write(f"Names linked: {self.stats['names_linked']}")
        self._write(f"Events created: {self.stats['events_created']}")
        self._write(f"Relationships created: {self.stats['relationships_created']}")
        
        if self.pretend:
            self._write("\n" + "="*50)
            self._write("PRETEND MODE SUMMARY")
            self._write("="*50)
            self._write("The following would be created/updated:")
            self._write(f"  • {self.stats['individuals_created']} new individuals")
            self._write(f"  • {self.stats['individuals_updated']} existing individuals updated")
            self._write(f"  • {self.stats['names_created']} new names")
            self._write(f"  • {self.stats['names_linked']} name-person links")
            self._write(f"  • {self.stats['events_created']} events (birth, death, marriage, etc.)")
            self._write(f"  • {self.stats['relationships_created']} parent-child relationships")
            self._write("\nThis was a pretend run. No changes were made to the database.")
            self._write("Use --no-pretend to actually import the data.")
        
        if self.stats['errors']:
            self._write(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors']:
                self._write(f"  - {error}")


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
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Use strict matching (no nicknames)'
        )
    
    def handle(self, *args, **options):
        file_path = options['file_path']
        pretend = not options['no_pretend']
        verbose = options['verbose']
        strict = options['strict']  # Default to non-strict
        
        if verbose:
            print(f"File path: {file_path}")
            print(f"Pretend mode: {pretend}")
            print(f"Strict matching: {strict}")
        
        try:
            importer = GEDCOMImporter(pretend=pretend, strict=strict, stdout=self.stdout)
            importer.import_gedcom(file_path)
        except Exception as e:
            raise CommandError(f"Import failed: {e}") 