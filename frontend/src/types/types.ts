export type Gender = 'U' | 'M' | 'F';

export type NameType = 'born as' | 'married as' | 'immigrated as';

export interface Name {
    id: number;
    first_name: string;
    middle_name: string;
    last_name: string;
}

export interface PersonName {
    id: number;
    person: number;  // Person ID
    name: number;    // Name ID
    name_type: NameType;
}

export interface Person {
    id: number;
    names: Name[];
    parents: Person[];
    children: Person[];
    gender: Gender;
    is_living: boolean;
    birth?: BirthEvent;
    death?: DeathEvent;
    siblings: Person[];
    spouses: Person[];
    spouse?: Person;
}

export interface ParentChildRelationship {
    id: number;
    parent: number;  // Person ID
    child: number;   // Person ID
}

export interface BaseEvent {
    id: number;
    date: string | null;  // ISO date string
    person: number;       // Person ID
    comment: string;
}

export interface CoupleEvent extends BaseEvent {
    other_person: number;  // Person ID
    location: string;
}

export interface MarriageEvent extends CoupleEvent {
    ended: boolean;
}

export interface DivorceEvent extends CoupleEvent {}

export interface BirthEvent extends BaseEvent {
    location: string;
}

export interface DeathEvent extends BaseEvent {
    location: string;
    cause: string;
}

export interface ImmigrationEvent extends BaseEvent {
    from_country: string;
    to_country: string;
    location: string;
}

export interface CitizenshipEvent extends BaseEvent {
    country: string;
    location: string;
} 