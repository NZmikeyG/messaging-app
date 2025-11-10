import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authstore';

export default function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return isAuthenticated ? children : <Navigate to="/login" />;
}
