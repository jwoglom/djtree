import { PersonData, RawPersonData } from '../types';

export const translateData = (data: RawPersonData[]): PersonData[] => {
  console.log('Raw API data:', data);
  
  const people = data.map((person: RawPersonData) => {
    const name = person.name || person.names?.[0];
    const firstName = name?.first_name || "";
    const middleName = name?.middle_name || "";
    const lastName = name?.last_name || "";
    
    const birthDate = person.birth?.date ? new Date(person.birth.date).getFullYear().toString() : "";
    const deathDate = person.death?.date ? new Date(person.death.date).getFullYear().toString() : "";
    
    const rels: any = {
      marriages: [],
      children: person.children?.map((child: any) => child.id.toString()) || [],
      siblings: person.siblings?.map((sibling: any) => ({
        id: sibling.id.toString(),
        gender: sibling.gender
      })) || []
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
    
    if (person.marriages && person.marriages.length > 0) {
      console.log('Marriages for person', person.id, ':', person.marriages);
      rels.marriages = person.marriages
        .filter((marriage: any) => marriage.other_person != null)
        .map((marriage: any) => ({
          id: marriage.other_person.id.toString(),
          gender: marriage.other_person.gender
        }));
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

  return people;
}; 