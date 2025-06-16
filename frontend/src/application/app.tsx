import React from "react";
// import f3 from "f3";

interface PersonData {
  "first name": string;
  "last name": string;
  birthday: string;
  avatar: string;
  gender: string;
}

interface PersonRelations {
  spouses: string[];
  father: string;
  mother: string;
  children: string[];
}

interface Person {
  id: string;
  data: PersonData;
  rels: PersonRelations;
}

const Tree: React.FC<{data: Person[]}> = ({data}: {data: Person[]}) => {
  // const store = f3.createStore({
  //   data,
  //   node_separation: 100,
  //   level_separation: 100,
  // });

  // const svg = f3.createSvg(document.querySelector('#tree'));
  // const Card = f3.elements.Card({
  //   store,
  //   svg,
  //   card_dim: {w:220,h:70,text_x:75,text_y:15,img_w:60,img_h:60,img_x:5,img_y:5},
  //   card_display: [i=>`${i.data["first name"]||""} ${i.data["last name"]||""}`,i=>`${i.data.birthday||""}`],
  //   mini_tree: true,
  //   link_break: false
  // });
  // store.setOnUpdate(props => f3.view(store.getTree(), svg, Card, props || {}));
  // store.updateTree({initial: true});

  return <div>Tree</div>;
};

const App: React.FC = () => {
  return <div>
    <Tree data={[]} />
  </div>;
};

export default App;