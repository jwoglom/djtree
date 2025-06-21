import React, { useEffect, useRef, useState } from "react";
import f3 from "family-chart";
import "../../../node_modules/family-chart/dist/styles/family-chart.css";

const translateData = (data: any) => {
  return data.map((person: any) => {
    // Extract name information
    const name = person.name || person.names?.[0] || {};
    const firstName = name.first_name || "";
    const middleName = name.middle_name || "";
    const lastName = name.last_name || "";
    
    // Extract birth information
    const birthDate = person.birth?.date ? new Date(person.birth.date).getFullYear().toString() : "";
    const deathDate = person.death?.date ? new Date(person.death.date).getFullYear().toString() : "";
    // Build relationships - family-chart expects specific structure
    const rels: any = {
      spouses: [], // We'll populate this if we have spouse data
      children: person.children?.map((child: any) => child.id.toString()) || []
    };
    
    // Add parents - family-chart expects father and mother as separate properties
    if (person.parents && person.parents.length > 0) {
      person.parents.forEach((parent: any) => {
        if (parent.gender === 'M') {
          rels.father = parent.id.toString();
        } else if (parent.gender === 'F') {
          rels.mother = parent.id.toString();
        }
      });
    }
    
    // Add spouse if available
    if (person.spouse) {
      rels.spouses = [person.spouse.id.toString()];
    }
    
    return {
      id: person.id.toString(),
      rels,
      data: {
        "first_name": firstName,
        "middle_name": middleName,
        "last_name": lastName,
        "birth_date": birthDate,
        "death_date": deathDate,
        "avatar": "",
        "gender": person.gender || "U"
      }
    };
  });
};

const Tree = () => {
  const treeRef = useRef<HTMLDivElement>(null);
  const [store, setStore] = useState<any>(null);

  useEffect(() => {
    const setupTree = async () => {
      const response = await fetch('/api/people/');
      const rawData = await response.json();
      const data = translateData(rawData);
      
      const newStore = f3.createStore({
        data,
        node_separation: 350,
        level_separation: 200,
      });

      if (treeRef.current) {
        const svg = f3.createSvg(treeRef.current);
        const Card = f3.elements.Card({
          store: newStore,
          svg,
          card_dim: {w:300,h:80,text_x:75,text_y:15,img_w:60,img_h:60,img_x:5,img_y:5},
          card_display: [(d: any) => {
            return `${d.data["first_name"]} ${d.data["middle_name"]} ${d.data["last_name"]}`;
          }, (d: any) => {
            return `${d.data["birth_date"]} - ${d.data["death_date"] || 'present'}`;
          }],
          mini_tree: true,
          link_break: false
        });

        newStore.setOnUpdate((props: any) => {
          f3.view(newStore.getTree(), svg, Card, props || {});
        });
        
        newStore.updateTree({initial: true});
        setStore(newStore);
      }
    };

    setupTree();
  }, []);

  return (
    <div style={{
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
      ></div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <div style={{width: '100%', height: '100vh'}}>
      <Tree />
    </div>
  );
};

export default App;