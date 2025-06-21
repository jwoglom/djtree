import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { FamilyTree } from "./components/FamilyTree";
import "../../../node_modules/family-chart/dist/styles/family-chart.css";

const App: React.FC = () => {
  console.log('App component rendering');
  
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<FamilyTree />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;