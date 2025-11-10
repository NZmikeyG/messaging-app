import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { channelsAPI } from '../services/api';
import { useAuthStore } from '../store/authstore';
import '../styles/Channels.css';

export default function Channels() {
  const [channels, setChannels] = useState([]);
  const [newChannelName, setNewChannelName] = useState('');
  const [newChannelDesc, setNewChannelDesc] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  useEffect(() => {
    fetchChannels();
  }, []);

  const fetchChannels = async () => {
    try {
      const { data } = await channelsAPI.list();
      setChannels(data);
    } catch (error) {
      console.error('Error fetching channels:', error);
    }
    setLoading(false);
  };

  const handleCreateChannel = async (e) => {
    e.preventDefault();
    try {
      await channelsAPI.create(newChannelName, newChannelDesc);
      setNewChannelName('');
      setNewChannelDesc('');
      fetchChannels();
    } catch (error) {
      console.error('Error creating channel:', error);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="channels-container">
      <div className="header">
        <h1>💬 Channels</h1>
        <button className="logout-btn" onClick={handleLogout}>Logout</button>
      </div>

      <form className="create-channel-form" onSubmit={handleCreateChannel}>
        <h2>Create New Channel</h2>
        <input
          type="text"
          placeholder="Channel name"
          value={newChannelName}
          onChange={(e) => setNewChannelName(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder="Description"
          value={newChannelDesc}
          onChange={(e) => setNewChannelDesc(e.target.value)}
        />
        <button type="submit">Create</button>
      </form>

      <div className="channels-list">
        <h2>Your Channels</h2>
        {loading ? (
          <p>Loading...</p>
        ) : channels.length > 0 ? (
          channels.map((channel) => (
            <div 
              key={channel.id} 
              className="channel-item"
              onClick={() => navigate(`/channels/${channel.id}`)}
              style={{cursor: "pointer"}}
            >
              <h3>#{channel.name}</h3>
              <p>{channel.description}</p>
              <small>👥 {channel.members.length} members</small>
              <button 
                style={{
                  marginTop: 10, 
                  padding: "6px 16px", 
                  background: "#667eea", 
                  color: "#fff", 
                  borderRadius: 5, 
                  border: "none"
                }}
                onClick={(e) => {
                  e.stopPropagation(); // Prevent parent click
                  navigate(`/channels/${channel.id}`);
                }}>
                Open Chat
              </button>
            </div>
          ))
        ) : (
          <p>No channels yet. Create one!</p>
        )}
      </div>
    </div>
  );
}
