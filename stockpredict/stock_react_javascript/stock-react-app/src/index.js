import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import './theme.css';
import './i18n';
import App from './App';
import reportWebVitals from './reportWebVitals';

// Strip dev-only console output from production builds. Backlog #16 added
// this when ~188 console.log/debug/info calls were scattered across
// components; those were removed 2026-11-01 and the eslint no-console rule
// (package.json) now flags new ones. Kept as a backstop for dependencies.
// console.error / console.warn intentionally pass through so genuine
// error reporting still surfaces.
if (process.env.NODE_ENV === 'production') {
  const noop = () => {};
  // eslint-disable-next-line no-console
  console.log = noop;
  // eslint-disable-next-line no-console
  console.debug = noop;
  // eslint-disable-next-line no-console
  console.info = noop;
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
