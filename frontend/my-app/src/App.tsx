import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import { AppRouter } from './router';
import './App.css';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <WebSocketProvider>
          <AppRouter />
        </WebSocketProvider>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
