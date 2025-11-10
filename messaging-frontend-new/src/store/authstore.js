import { create } from 'zustand';
import Cookies from 'js-cookie';
import { authAPI } from '../services/api';

export const useAuthStore = create((set) => ({
  user: null,
  token: Cookies.get('token') || null,
  isAuthenticated: !!Cookies.get('token'),

  login: async (email, password) => {
    const { data } = await authAPI.login(email, password);
    Cookies.set('token', data.access_token);
    set({
      user: data.user,
      token: data.access_token,
      isAuthenticated: true,
    });
  },

  register: async (email, username, password) => {
    const { data } = await authAPI.register(email, username, password);
    return data;
  },

  logout: () => {
    Cookies.remove('token');
    set({ user: null, token: null, isAuthenticated: false });
  },

  setUser: (user) => set({ user }),
}));
