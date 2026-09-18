import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import { applyTheme, readTheme } from './components/Theme.jsx';

import './styles/tokens.css';
import './styles/base.css';
import './styles/views.css';

// Antes de montar: si no, el primer pintado sale con el tema del sistema y salta al
// elegido una milésima después.
applyTheme(readTheme());

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
