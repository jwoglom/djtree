import React, { useEffect, useRef, useState } from "react";
import f3 from "family-chart";
import "../../../node_modules/family-chart/dist/styles/family-chart.css";
import * as d3 from "d3";

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

  useEffect(() => {
    const setupTree = async () => {
      const response = await fetch('/api/people/');
      const rawData = await response.json();
      const data = translateData(rawData);
      
      let tree: any;
      let main_id: any;
      let store: any; // Add store variable
      let isInitializing = true; // Add flag to prevent callback during init
      
      if (treeRef.current) {
        const onZoom = (e: any) => {
          const t = e.transform;
          const view_el = d3.select(svg).select('.view');
          view_el.style('transform', `translate(${t.x}px, ${t.y}px) scale(${t.k})`);
          cardHtml.select('.cards_view').style('transform', `translate(${t.x}px, ${t.y}px) scale(${t.k})`);
        };
        
        const svg = f3.createSvg(treeRef.current, { onZoom });
        const cont = d3.select(treeRef.current);
        cont.style('position', 'relative').style('overflow', 'hidden');
        
        const cardHtml = cont.append('div')
          .attr('id', 'htmlSvg')
          .attr('style', 'position: absolute; width: 100%; height: 100%; z-index: 10; top: 0; left: 0; pointer-events: none;');
        
        cardHtml.append('div')
          .attr('class', 'cards_view')
          .style('transform-origin', '0 0')
          .style('pointer-events', 'auto');
        
        const view_el = d3.select(svg).select('.view');
        
        // Create store once
        store = f3.createStore({ 
          data, 
          node_separation: 320,  // Horizontal separation between nodes
          level_separation: 100  // Vertical separation between levels
        });
        
        console.log('Store created:', store);
        console.log('Initial data:', data);
        
        // Set initial main_id to the first person
        if (data && data.length > 0) {
          main_id = data[0].id;
          console.log('Setting initial main_id:', main_id);
        }
        
        const Card = (tree: any, svg: any) => {
          const card_dim = { w: 280, h: 80, text_x: 75, text_y: 15, img_w: 60, img_h: 60, img_x: 5, img_y: 5 };
          
          return function (d: any) {
            this.innerHTML = '';
            
            const div = d3.select(this).append('div')
              .style('transform', `translate(${-card_dim.w / 2}px, ${-card_dim.h / 2}px)`)
              .style('pointer-events', 'auto')
              .style('z-index', '1');
            
            const div_inner = div.append('div')
              .attr('style', `
                width: ${card_dim.w}px; 
                height: ${card_dim.h}px; 
                background-color: ${d.data.data.gender === 'F' ? '#c48a92' : d.data.data.gender === 'M' ? '#789fac' : '#d3d3d3'}; 
                color: #fff; 
                border-radius: 8px; 
                cursor: pointer;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                display: flex;
                align-items: center;
                padding: 10px;
                font-family: 'Roboto', sans-serif;
              `)
              .on('click', (e: any) => onCardClick(e, d));
            
            // Avatar/icon area
            const avatarDiv = div_inner.append('div')
              .attr('style', `
                width: ${card_dim.img_w}px; 
                height: ${card_dim.img_h}px; 
                border-radius: 50%; 
                background-color: rgba(255,255,255,0.2); 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                margin-right: 15px;
                font-size: 24px;
              `);
            
            // Gender icon
            avatarDiv.append('span')
              .text(d.data.data.gender === 'F' ? '♀' : d.data.data.gender === 'M' ? '♂' : '?')
              .style('color', '#fff');
            
            // Text content area
            const textDiv = div_inner.append('div')
              .attr('style', 'flex: 1; display: flex; flex-direction: column; justify-content: center;');
            
            // Name
            textDiv.append('div')
              .attr('style', 'font-weight: bold; font-size: 16px; margin-bottom: 4px;')
              .text(`${d.data.data.first_name} ${d.data.data.middle_name} ${d.data.data.last_name}`.trim());
            
            // Birth/death dates
            const dateText = d.data.data.birth_date 
              ? `${d.data.data.birth_date}${d.data.data.death_date ? ` - ${d.data.data.death_date}` : ''}`
              : '';
            
            if (dateText) {
              textDiv.append('div')
                .attr('style', 'font-size: 12px; opacity: 0.8;')
                .text(dateText);
            }
          };
        };
        
        const updateTree = (props: any) => {
          // Safety check - ensure store exists
          if (!store) {
            console.warn('Store is undefined, skipping update');
            return;
          }
          
          tree = store.getTree();
          
          // Safety check - ensure tree exists and has data
          if (!tree || !tree.data) {
            console.warn('Tree or tree.data is undefined, skipping update');
            return;
          }
          
          props = Object.assign({}, props || {}, { 
            cardHtml: cardHtml.node(),
            card_dim: { w: 300, h: 80, text_x: 75, text_y: 15, img_w: 60, img_h: 60, img_x: 5, img_y: 5 }
          });
          f3.view(tree, svg, Card(tree, svg), props || {});
        };
        
        const updateMainId = (_main_id: any) => {
          main_id = _main_id;
          store.updateMainId(main_id); // Update the store's main_id
          store.updateTree({ initial: false }); // Trigger tree update
        };
        
        const onCardClick = (e: any, d: any) => {
          console.log('Card clicked!', d.data.id, d.data.data);
          updateMainId(d.data.id);
        };
        
        // Initialize the tree first, then set up the callback
        if (main_id) {
          store.updateMainId(main_id); // Set the main_id first
        }
        store.updateTree({ initial: true }); // Initialize the store first
        tree = store.getTree();
        console.log('Initial tree:', tree);
        updateTree({ initial: true });
        
        // Set up store update callback after tree is initialized
        store.setOnUpdate((props: any) => {
          if (!isInitializing && tree && store) {
            console.log('Store update triggered, updating view');
            updateTree(props);
          }
        });
        
        // Mark initialization as complete
        isInitializing = false;
      }
    };

    setupTree();
  }, []);

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