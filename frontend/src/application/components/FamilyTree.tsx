import React, { useEffect } from 'react';
import { useFamilyTree } from '../hooks/useFamilyTree';

export const FamilyTree: React.FC = () => {
  console.log('FamilyTree component rendering');
  const { treeRef, isLoading } = useFamilyTree();
  
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
      position: 'relative',
      backgroundColor: '#333',
      color: '#fff'
    }}>
      <div 
        ref={treeRef} 
        id="tree" 
        className="f3"
        style={{
          width: '100%', 
          height: '100%', 
          position: 'absolute', 
          top: 0, 
          left: 0,
          backgroundColor: '#333'
        }}
      />
    </div>
  );
}; 