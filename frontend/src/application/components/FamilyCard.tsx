import React from 'react';
import { PersonData } from '../types';

interface FamilyCardProps {
  data: PersonData;
  onClick: (e: React.MouseEvent, data: PersonData) => void;
  visibleNodeIds: string[];
}

export const FamilyCard: React.FC<FamilyCardProps> = ({ data, onClick, visibleNodeIds }) => {
  const getGenderIcon = (gender: string) => {
    switch (gender) {
      case 'F': return '♀';
      case 'M': return '♂';
      default: return '?';
    }
  };

  const getGenderColor = (gender: string) => {
    switch (gender) {
      case 'F': return '#c48a92';
      case 'M': return '#789fac';
      default: return '#d3d3d3';
    }
  };

  const fullName = `${data.data.first_name} ${data.data.middle_name} ${data.data.last_name}`.trim();
  const dateText = data.data.birth_date 
    ? `${data.data.birth_date}${data.data.death_date ? ` - ${data.data.death_date}` : ''}`
    : '';

  return (
    <div
      style={{
        transform: `translate(${-140}px, ${-40}px)`,
        pointerEvents: 'auto',
        zIndex: 1
      }}
      onClick={(e) => onClick(e, data)}
    >
      <div
        style={{
          width: '280px',
          height: '80px',
          backgroundColor: getGenderColor(data.data.gender),
          color: '#fff',
          borderRadius: '8px',
          cursor: 'pointer',
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
          display: 'flex',
          alignItems: 'center',
          padding: '10px',
          fontFamily: 'Roboto, sans-serif',
          position: 'relative',
        }}
      >
        {((data.rels.father && !visibleNodeIds.includes(data.rels.father)) || (data.rels.mother && !visibleNodeIds.includes(data.rels.mother))) && (
          <div style={{
            position: 'absolute',
            top: '4px',
            right: '4px',
            display: 'flex',
            gap: '2px',
          }}>
            {data.rels.father && !visibleNodeIds.includes(data.rels.father) && <div style={{ width: '10px', height: '10px', backgroundColor: getGenderColor('M'), borderRadius: '2px' }} />}
            {data.rels.mother && !visibleNodeIds.includes(data.rels.mother) && <div style={{ width: '10px', height: '10px', backgroundColor: getGenderColor('F'), borderRadius: '2px' }} />}
          </div>
        )}
        <div
          style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            backgroundColor: 'rgba(255,255,255,0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: '15px',
            fontSize: '24px'
          }}
        >
          {getGenderIcon(data.data.gender)}
        </div>
        
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}
        >
          <div
            style={{
              fontWeight: 'bold',
              fontSize: '16px',
              marginBottom: '4px'
            }}
          >
            {fullName}
          </div>
          
          {dateText && (
            <div
              style={{
                fontSize: '12px',
                opacity: 0.8
              }}
            >
              {dateText}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}; 