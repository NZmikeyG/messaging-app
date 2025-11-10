import axios from 'axios';
import Cookies from 'js-cookie';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
});

// Add token to requests
API.interceptors.request.use((config) => {
  const token = Cookies.get('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  register: (email, username, password) =>
    API.post('/auth/register', { email, username, password }),
  login: (email, password) =>
    API.post('/auth/login', { email, password }),
  getMe: () => API.get('/auth/me'),
};

export const channelsAPI = {
  list: () => API.get('/channels/'),
  create: (name, description) =>
    API.post('/channels/', { name, description }),
  get: (channelId) => API.get(`/channels/${channelId}`),
  addMember: (channelId, userId) =>
    API.post(`/channels/${channelId}/members/${userId}`),
};

export const messagesAPI = {
  list: (channelId) => API.get(`/messages/${channelId}`),
  send: (channelId, content) =>
    API.post(`/messages/${channelId}`, { content }),
  delete: (channelId, messageId) =>
    API.delete(`/messages/${channelId}/${messageId}`),
};

export const usersAPI = {
  search: (query) => API.get(`/users/search?query=${query}`),
};

export const calendarAPI = {
  getMyEvents: () => API.get('/calendar/events'),
  getUserEvents: (userId) => API.get(`/calendar/events/${userId}`),
  createEvent: (event) => API.post('/calendar/events', event),
};

export default API;
