export interface PersonData {
  id: string;
  rels: {
    spouses: string[];
    children: string[];
    father?: string;
    mother?: string;
  };
  data: {
    first_name: string;
    middle_name: string;
    last_name: string;
    birth_date: string;
    death_date: string;
    avatar: string;
    gender: 'M' | 'F' | 'U';
  };
}

export interface RawPersonData {
  id: number;
  name?: {
    first_name: string;
    middle_name: string;
    last_name: string;
  };
  names?: Array<{
    first_name: string;
    middle_name: string;
    last_name: string;
  }>;
  birth?: {
    date: string;
  };
  death?: {
    date: string;
  };
  gender: 'M' | 'F' | 'U';
  parents?: Array<{
    id: number;
    gender: 'M' | 'F';
  }>;
  children?: Array<{
    id: number;
  }>;
  spouse?: {
    id: number;
  };
} 