export const getGenderIcon = (gender: string): string => {
  switch (gender) {
    case 'F': return '♀';
    case 'M': return '♂';
    default: return '?';
  }
};

export const getGenderColor = (gender: string): string => {
  switch (gender) {
    case 'F': return '#c48a92';
    case 'M': return '#789fac';
    default: return '#d3d3d3';
  }
};

export const getGenderLabel = (gender: string): string => {
  switch (gender) {
    case 'F': return 'Female';
    case 'M': return 'Male';
    default: return 'Unknown';
  }
};
