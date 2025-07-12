import re
from datetime import date
from typing import List, Optional, Tuple
from person.models import Person


class PersonMatcher:
    """Simple matching for finding existing people in the database"""
    
    @staticmethod
    def find_matching_person(gedcom_person: dict, existing_people: List[Person], strict: bool = True) -> Optional[Person]:
        """Find a matching person using simple, predictable logic"""
        if not existing_people:
            return None
            
        # Parse GEDCOM data
        name_info = gedcom_person.get('NAME', '')
        if not isinstance(name_info, str):
            name_info = ''
        first_name, middle_name, last_name = PersonMatcher._parse_name(name_info)
        
        birth_date = None
        birt = gedcom_person.get('BIRT')
        if isinstance(birt, dict):
            birth_date = PersonMatcher._parse_date(birt.get('DATE', ''))
        
        # Simple matching logic
        for person in existing_people:
            if PersonMatcher._is_match(person, first_name, middle_name, last_name, birth_date, strict):
                return person
        
        return None
    
    @staticmethod
    def _is_match(person: Person, first_name: str, middle_name: str, last_name: str, 
                  birth_date: Optional[date], strict: bool) -> bool:
        """Simple boolean match check - much easier to debug than scoring"""
        
        # Check names against all person names
        for person_name in person.names.all():
            if PersonMatcher._names_match(
                first_name, middle_name, last_name,
                person_name.first_name, person_name.middle_name, person_name.last_name,
                strict
            ):
                # If names match, check birth date if available
                if birth_date and person.birth and person.birth.date:
                    if not PersonMatcher._dates_match(birth_date, person.birth.date, strict):
                        continue  # Names match but dates don't - skip this person
                
                return True  # Found a match!
        
        return False
    
    @staticmethod
    def _names_match(first1: str, middle1: str, last1: str,
                    first2: str, middle2: str, last2: str, strict: bool) -> bool:
        """Simple name matching logic"""
        
        # Normalize names
        first1, first2 = first1.lower().strip(), first2.lower().strip()
        last1, last2 = last1.lower().strip(), last2.lower().strip()
        
        # Must have first and last names
        if not first1 or not first2 or not last1 or not last2:
            return False
        
        # Last names must match exactly
        if last1 != last2:
            return False
        
        # First name matching
        if first1 == first2:
            # Exact first name match - always good
            return True
        
        if not strict:
            # In non-strict mode, check for common nicknames
            if PersonMatcher._is_nickname(first1, first2):
                return True
        
        return False
    
    @staticmethod
    def _is_nickname(name1: str, name2: str) -> bool:
        """Check if two names are common nicknames of each other"""
        # Only the most common, widely recognized nicknames
        common_nicknames = {
            'william': ['bill', 'billy'],
            'robert': ['bob', 'bobby'],
            'richard': ['dick', 'rick'],
            'james': ['jim', 'jimmy'],
            'joseph': ['joe', 'joey'],
            'michael': ['mike', 'mikey'],
            'christopher': ['chris'],
            'daniel': ['dan', 'danny'],
            'matthew': ['matt'],
            'andrew': ['andy'],
            'jonathan': ['jon'],
            'benjamin': ['ben', 'benny'],
            'nicholas': ['nick'],
            'alexander': ['alex'],
            'elizabeth': ['liz', 'beth'],
            'margaret': ['maggie'],
            'patricia': ['pat'],
            'jennifer': ['jen'],
            'stephanie': ['steph'],
            'catherine': ['cathy'],
            'peter': ['pete'],
            'christina': ['tina']
        }
        
        # Check if either name is a known nickname for the other
        for full_name, nicknames in common_nicknames.items():
            if name1 == full_name and name2 in nicknames:
                return True
            if name2 == full_name and name1 in nicknames:
                return True
        
        return False
    
    @staticmethod
    def _dates_match(date1: date, date2: date, strict: bool) -> bool:
        """Simple date matching logic"""
        if date1 == date2:
            return True
        
        # Calculate year difference
        year_diff = abs(date1.year - date2.year)
        
        if strict:
            # Strict: same year only
            return year_diff == 0
        else:
            # Lenient: within 2 years
            return year_diff <= 2
    
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