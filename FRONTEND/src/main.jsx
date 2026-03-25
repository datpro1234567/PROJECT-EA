import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<App initialMode="signIn" />} />
        <Route path="/signup" element={<App initialMode="signUp" />} />
        <Route path="/home" element={<App initialMode="home" />} />
        <Route path="/admin_home" element={<App initialMode="adminHome" />} />
        <Route path="/change-password" element={<App initialMode="changePassword" />} />
        <Route path="/change-password/:id" element={<App initialMode="changePasswordPhase2" />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
