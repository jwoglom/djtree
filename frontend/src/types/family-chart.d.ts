declare module 'family-chart' {
  interface StoreOptions {
    data: any;
    node_separation?: number;
    level_separation?: number;
  }

  interface CardOptions {
    store: Store;
    svg: any;
    card_dim: {
      w: number;
      h: number;
      text_x: number;
      text_y: number;
      img_w: number;
      img_h: number;
      img_x: number;
      img_y: number;
    };
    card_display: ((item: any) => string)[];
    mini_tree?: boolean;
    link_break?: boolean;
  }

  interface Store {
    getTree: () => any;
    setOnUpdate: (callback: (props: any) => void) => void;
    updateTree: (options: { initial: boolean }) => void;
  }

  const f3: {
    createStore: (options: StoreOptions) => Store;
    createSvg: (element: HTMLElement, options?: { onZoom?: (e: any) => void }) => any;
    view: (tree: any, svg: any, Card: any, props?: any) => void;
    CalculateTree: (options: { data: any; main_id?: any }) => any;
    elements: {
      Card: (options: CardOptions) => any;
    };
  };

  export default f3;
} 