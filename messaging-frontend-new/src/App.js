import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Channels from './pages/Channels';
import Messaging from './pages/Messaging'; // We will add this
import Calendar from './pages/Calendar';   // We will add this
import FileUpload from './pages/FileUpload'; // We will add this
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route 
          path="/channels" 
          element={
            <ProtectedRoute>
              <Channels />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/channels/:channelId" 
          element={
            <ProtectedRoute>
              <Messaging />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/calendar" 
          element={
            <ProtectedRoute>
              <Calendar />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/channels/:channelId/upload" 
          element={
            <ProtectedRoute>
              <FileUpload />
            </ProtectedRoute>
          } 
        />
        <Route path="/" element={<Navigate to="/channels" />} />
      </Routes>
    </Router>
  );
}

export default App;
