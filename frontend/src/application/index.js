import React from "react"; // eslint-disable-line no-unused-vars
import { createRoot } from "react-dom/client";
import App from "./app.tsx";

const root = document.getElementById('root');
const rootElement = createRoot(root);
rootElement.render(<App />);
