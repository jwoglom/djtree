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
        {data.rels.father && !visibleNodeIds.includes(data.rels.father) && (
          <div style={{
            position: 'absolute',
            top: '-10px',
            left: '10px',
            width: '16px',
            height: '8px',
            backgroundColor: getGenderColor('M'),
            borderRadius: '3px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
          }} />
        )}
        {data.rels.mother && !visibleNodeIds.includes(data.rels.mother) && (
          <div style={{
            position: 'absolute',
            top: '-10px',
            right: '10px',
            width: '16px',
            height: '8px',
            backgroundColor: getGenderColor('F'),
            borderRadius: '3px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
          }} />
        )}
        {data.rels.siblings && data.rels.siblings.some(id => !visibleNodeIds.includes(id)) && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '-15px',
            transform: 'translateY(-50%)',
            width: '8px',
            height: '16px',
            backgroundColor: 'rgba(255, 255, 255, 0.5)',
            borderRadius: '3px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
          }} />
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