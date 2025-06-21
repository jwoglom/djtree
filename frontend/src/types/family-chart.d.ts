declare module 'family-chart' {
  interface StoreOptions {
    data: any;
    main_id?: any;
    node_separation?: number;
    level_separation?: number;
    single_parent_empty_card?: boolean;
    is_horizontal?: boolean;
    one_level_rels?: boolean;
    sortChildrenFunction?: (a: any, b: any) => any;
    sortSpousesFunction?: (a: any, b: any) => any;
    ancestry_depth?: number;
    progeny_depth?: number;
    show_siblings_of_main?: boolean;
    modifyTreeHierarchy?: any;
    private_cards_config?: any;
    duplicate_branch_toggle?: boolean;
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