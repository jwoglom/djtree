export interface PersonData {
  id: string;
  rels: {
    marriages: Array<{
      id: string;
      gender: 'M' | 'F' | 'U';
    }>;
    children: string[];
    father?: string;
    mother?: string;
    siblings: Array<{
      id: string;
      gender: 'M' | 'F' | 'U';
    }>;
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

// Detailed person data from the API
export interface DetailedPersonData {
  id: number;
  name?: {
    first_name: string;
    middle_name: string;
    last_name: string;
    name_type: string | null;
  };
  names: Array<{
    first_name: string;
    middle_name: string;
    last_name: string;
    name_type: string | null;
  }>;
  gender: 'M' | 'F' | 'U';
  is_living: boolean;
  birth?: {
    id: number;
    date: string;
    location: string;
    comment: string;
  };
  death?: {
    id: number;
    date: string;
    location: string;
    cause: string;
    comment: string;
  };
  marriages: Array<{
    id: number;
    date: string;
    location: string;
    comment: string;
    ended: boolean;
    other_person: {
      id: number;
      name?: {
        first_name: string;
        middle_name: string;
        last_name: string;
      };
      names: Array<{
        first_name: string;
        middle_name: string;
        last_name: string;
      }>;
      gender: 'M' | 'F' | 'U';
      url: string;
    };
  }>;
  divorces: Array<{
    id: number;
    date: string;
    location: string;
    comment: string;
    other_person: {
      id: number;
      name?: {
        first_name: string;
        middle_name: string;
        last_name: string;
      };
      names: Array<{
        first_name: string;
        middle_name: string;
        last_name: string;
      }>;
      gender: 'M' | 'F' | 'U';
      url: string;
    };
  }>;
  immigrations: Array<{
    id: number;
    date: string;
    from_country: string;
    to_country: string;
    location: string;
    comment: string;
  }>;
  citizenships: Array<{
    id: number;
    date: string;
    country: string;
    location: string;
    comment: string;
  }>;
  parents: Array<{
    id: number;
    name?: {
      first_name: string;
      middle_name: string;
      last_name: string;
    };
    names: Array<{
      first_name: string;
      middle_name: string;
      last_name: string;
    }>;
    gender: 'M' | 'F' | 'U';
    url: string;
  }>;
  children: Array<{
    id: number;
    name?: {
      first_name: string;
      middle_name: string;
      last_name: string;
    };
    names: Array<{
      first_name: string;
      middle_name: string;
      last_name: string;
    }>;
    gender: 'M' | 'F' | 'U';
    url: string;
  }>;
  siblings: Array<{
    id: number;
    name?: {
      first_name: string;
      middle_name: string;
      last_name: string;
    };
    names: Array<{
      first_name: string;
      middle_name: string;
      last_name: string;
    }>;
    gender: 'M' | 'F' | 'U';
    url: string;
  }>;
  attachment_count: number;
  attachment_folder_path: string;
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
  siblings?: Array<{
    id: number;
    gender: 'M' | 'F' | 'U';
  }>;
  marriages?: Array<{
    other_person: {
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
      gender: 'M' | 'F' | 'U';
      url: string;
    };
    date?: string;
    ended?: boolean;
  }>;
} 