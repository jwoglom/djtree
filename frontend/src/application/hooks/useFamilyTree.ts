import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import f3 from 'family-chart';
import * as d3 from 'd3';
import { createRoot } from 'react-dom/client';
import { translateData } from '../utils/dataTranslator';
import { PersonData } from '../types';
import { FamilyCard } from '../components/FamilyCard';

export const useFamilyTree = () => {
  const treeRef = useRef<HTMLDivElement>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [isLoading, setIsLoading] = useState(true);
  const [data, setData] = useState<PersonData[]>([]);
  const isTreeSetup = useRef(false);

  console.log('useFamilyTree hook called');

  // Fetch data first
  useEffect(() => {
    const fetchData = async () => {
      console.log('Fetching data...');
      try {
        const response = await fetch('/api/people/');
        const rawData = await response.json();
        const translatedData = translateData(rawData);
        setData(translatedData);
        setIsLoading(false);
        console.log('Data fetched and translated:', translatedData);
      } catch (error) {
        console.error('Error fetching data:', error);
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Set up tree when data is ready and DOM element exists
  useEffect(() => {
    if (isLoading || !data.length || !treeRef.current || isTreeSetup.current) {
      return;
    }

    console.log('Setting up tree with data and DOM element');
    let cleanup: (() => void) | undefined;
    
    const setupTree = () => {
      let tree: any;
      let main_id: any;
      let store: any;
      let isInitializing = true;
      const roots = new Map(); // Track React roots for each card
      
      console.log('Tree ref exists, setting up family-chart');
      try {
        // Clean up any existing containers
        const existingHtmlSvg = treeRef.current!.querySelector('#htmlSvg');
        if (existingHtmlSvg) {
          existingHtmlSvg.remove();
        }
        
        const onZoom = (e: any) => {
          const t = e.transform;
          const view_el = d3.select(svg).select('.view');
          view_el.style('transform', `translate(${t.x}px, ${t.y}px) scale(${t.k})`);
          cardHtml.select('.cards_view').style('transform', `translate(${t.x}px, ${t.y}px) scale(${t.k})`);
        };
        
        console.log('Creating SVG...');
        const svg = f3.createSvg(treeRef.current!, { onZoom });
        console.log('SVG created:', svg);
        
        console.log('Setting up D3 container...');
        const cont = d3.select(treeRef.current!);
        cont.style('position', 'relative').style('overflow', 'hidden');
        
        console.log('Creating card HTML container...');
        const cardHtml = cont.append('div')
          .attr('id', 'htmlSvg')
          .attr('style', 'position: absolute; width: 100%; height: 100%; z-index: 10; top: 0; left: 0; pointer-events: none;');
        
        cardHtml.append('div')
          .attr('class', 'cards_view')
          .style('transform-origin', '0 0')
          .style('pointer-events', 'auto');
        
        console.log('Creating store...');
        store = f3.createStore({ 
          data, 
          node_separation: 350,
          level_separation: 120
        });
        console.log('Store created:', store);
        
        if (data && data.length > 0) {
          const urlPersonId = searchParams.get('person_id');
          if (urlPersonId) {
            main_id = urlPersonId;
          } else {
            main_id = data[0].id;
            setSearchParams({ person_id: main_id });
          }
        }
        
        const Card = (tree: any, svg: any) => {
          return function (d: any) {
            this.innerHTML = '';
            
            // Check if we already have a root for this element
            let root = roots.get(this);
            if (!root) {
              root = createRoot(this);
              roots.set(this, root);
            }
            
            const visibleNodeIds = tree.data.map((node: any) => String(node.data.id));

            const cardElement = React.createElement(FamilyCard, {
              data: d.data,
              onClick: onCardClick,
              visibleNodeIds: visibleNodeIds
            });
            root.render(cardElement);
          };
        };
        
        const updateTree = (props: any) => {
          console.log('updateTree called with props:', props);
          if (!store) {
            console.warn('Store is undefined, skipping update');
            return;
          }
          
          // Clear the roots Map before updating to avoid stale references
          roots.clear();
          
          tree = store.getTree();
          console.log('Tree from store:', tree);
          if (!tree || !tree.data) {
            console.warn('Tree or tree.data is undefined, skipping update');
            return;
          }
          
          props = Object.assign({}, props || {}, { 
            cardHtml: cardHtml.node(),
            card_dim: { w: 280, h: 80, text_x: 75, text_y: 15, img_w: 60, img_h: 60, img_x: 5, img_y: 5 },
            transition_time: 500
          });
          console.log('Calling f3.view with props:', props);
          f3.view(tree, svg, Card(tree, svg), props || {});
          console.log('f3.view completed');
        };
        
        const updateMainId = (_main_id: any) => {
          main_id = _main_id;
          store.updateMainId(main_id);
          store.updateTree({ initial: false });
          setSearchParams({ person_id: _main_id });
        };
        
        const onCardClick = (e: any, d: PersonData) => {
          updateMainId(d.id);
        };
        
        // Handle window resize
        const handleResize = () => {
          if (store && tree) {
            console.log('Window resized, updating tree');
            store.updateTree({ initial: false });
          }
        };
        
        // Add resize listener
        window.addEventListener('resize', handleResize);
        
        if (main_id) {
          store.updateMainId(main_id);
        }
        store.updateTree({ initial: true });
        tree = store.getTree();
        console.log('Initial tree:', tree);
        updateTree({ initial: true });
        
        store.setOnUpdate((props: any) => {
          if (!isInitializing && tree && store) {
            console.log('Store update triggered');
            updateTree(props);
          }
        });
        
        isInitializing = false;
        isTreeSetup.current = true;
        console.log('Tree setup complete');
        
        // Return cleanup function
        cleanup = () => {
          window.removeEventListener('resize', handleResize);
        };
      } catch (error) {
        console.error('Error setting up family tree:', error);
      }
    };

    setupTree();
    
    // Return cleanup function
    return () => {
      if (cleanup) {
        cleanup();
      }
    };
  }, [isLoading, data]);

  return { treeRef, isLoading };
}; 