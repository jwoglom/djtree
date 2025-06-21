import React from "react"; // eslint-disable-line no-unused-vars
import { createRoot } from "react-dom/client";
import App from "./app";
import "../styles/index.scss";

const root = document.getElementById('root');
if (root) {
  const rootElement = createRoot(root);
  rootElement.render(<App />);
} else {
  console.error('Root element not found');
}
