import React from 'react';
import {createRoot} from 'react-dom/client';
import './auth';
import App from './App';
import '@fontsource/montserrat/600.css';
import '@fontsource/montserrat/700.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import './styles.css';

const root = createRoot(document.getElementById('root'));
root.render(<App />);
