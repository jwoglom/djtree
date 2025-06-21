import { PersonData, RawPersonData } from '../types';

export const translateData = (data: RawPersonData[]): PersonData[] => {
  const people = data.map((person: RawPersonData) => {
    const name = person.name || person.names?.[0];
    const firstName = name?.first_name || "";
    const middleName = name?.middle_name || "";
    const lastName = name?.last_name || "";
    
    const birthDate = person.birth?.date ? new Date(person.birth.date).getFullYear().toString() : "";
    const deathDate = person.death?.date ? new Date(person.death.date).getFullYear().toString() : "";
    
    const rels: any = {
      spouses: [],
      children: person.children?.map((child: any) => child.id.toString()) || [],
      siblings: [] 
    };
    
    if (person.parents && person.parents.length > 0) {
      person.parents.forEach((parent: any) => {
        if (parent.gender === 'M') {
          rels.father = parent.id.toString();
        } else if (parent.gender === 'F') {
          rels.mother = parent.id.toString();
        }
      });
    }
    
    if (person.spouse) {
      rels.spouses = [person.spouse.id.toString()];
    }
    
    return {
      id: person.id.toString(),
      rels,
      data: {
        first_name: firstName,
        middle_name: middleName,
        last_name: lastName,
        birth_date: birthDate,
        death_date: deathDate,
        avatar: "",
        gender: person.gender || "U"
      }
    };
  });

  // Add siblings
  people.forEach(person => {
    if (person.rels.father || person.rels.mother) {
      const siblings = people.filter(p => {
        return p.id !== person.id && 
               (p.rels.father === person.rels.father && p.rels.mother === person.rels.mother);
      });
      person.rels.siblings = siblings.map(s => s.id);
    }
  });

  return people;
}; 