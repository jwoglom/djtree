import React, { useEffect } from 'react';
import { useFamilyTree } from '../hooks/useFamilyTree';
import { PersonDetailPanel } from './PersonDetailPanel';

export const FamilyTree: React.FC = () => {
  console.log('FamilyTree component rendering');
  const { treeRef, isLoading, selectedPersonId, setSelectedPersonId, navigateToPerson } = useFamilyTree();
  
  console.log('FamilyTree hook result:', { isLoading });
  console.log('treeRef in FamilyTree:', treeRef);
  console.log('treeRef.current in FamilyTree:', treeRef.current);

  useEffect(() => {
    console.log('FamilyTree useEffect - treeRef.current:', treeRef.current);
  }, [treeRef.current]);

  if (isLoading) {
    console.log('Showing loading state');
    return (
      <div style={{
        width: '100%', 
        height: '100vh', 
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#333',
        color: '#fff'
      }}>
        Loading family tree...
      </div>
    );
  }

  console.log('Rendering family tree');
  return (
    <div style={{
      width: '100%',
      height: '100vh',
      display: 'flex',
      backgroundColor: '#333',
      color: '#fff',
      overflow: 'hidden',
    }}>
      <div
        ref={treeRef}
        id="tree"
        className="f3"
        style={{
          flex: selectedPersonId ? '1' : '1',
          width: selectedPersonId ? 'calc(100% - 400px)' : '100%',
          height: '100%',
          backgroundColor: '#333',
          transition: 'width 0.3s ease',
          overflow: 'hidden',
          position: 'relative',
        }}
      />
      {selectedPersonId && (
        <PersonDetailPanel
          personId={selectedPersonId}
          onClose={() => setSelectedPersonId(null)}
          onNavigateToPerson={navigateToPerson}
        />
      )}
    </div>
  );
}; 