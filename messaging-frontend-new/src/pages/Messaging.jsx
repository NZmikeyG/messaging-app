import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { messagesAPI } from '../services/api';
import { useAuthStore } from '../store/authstore';
import '../styles/Chat.css';

export default function Messaging() {
  const { channelId } = useParams();
  const user = useAuthStore((state) => state.user);
  const token = useAuthStore((state) => state.token);
  const [messages, setMessages] = useState([]);
  const [content, setContent] = useState('');
  const [ws, setWs] = useState(null);
  const [error, setError] = useState('');
  const scrollRef = useRef();

  // Fetch message history and connect to WebSocket when channelId changes
  useEffect(() => {
    fetchMessages();
    let socket;
    // Connect WebSocket
    if (token) {
      socket = new WebSocket(
        `ws://127.0.0.1:8000/api/ws/${channelId}?token=${token}`
      );
      socket.onopen = () => { console.log('WebSocket connected'); };
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'message') {
          setMessages((prev) => [...prev, message]);
          setTimeout(() => scrollRef.current?.scrollIntoView({ behavior: 'smooth' }), 200);
        }
      };
      socket.onerror = () => setError('WebSocket error');
      setWs(socket);
    }
    // Cleanup on exit
    return () => socket && socket.close();
    // eslint-disable-next-line
  }, [channelId, token]);

  // Fetch all previous messages (REST)
  const fetchMessages = async () => {
    try {
      const { data } = await messagesAPI.list(channelId);
      setMessages(data);
      setTimeout(() => scrollRef.current?.scrollIntoView({ behavior: 'smooth' }), 200);
    } catch (err) {
      setError('Failed to load messages');
    }
  };

  // Send new message over websocket
  const sendMessage = (e) => {
    e.preventDefault();
    if (!ws || ws.readyState !== 1) {
      setError('WebSocket unavailable!');
      return;
    }
    ws.send(JSON.stringify({ content }));
    setContent('');
  };

  return (
    <div className="chat-page">
      <h2>Channel Chat</h2>
      <div className="chat-container">
        {messages.map((msg, i) => (
          <div key={msg.id || i} className="chat-message">
            <b>{msg.sender?.username || (user && user.username) || "You"}:</b>&nbsp;
            <span>{msg.content}</span>
            <span className="timestamp">
              {msg.created_at && new Date(msg.created_at).toLocaleTimeString()}
            </span>
          </div>
        ))}
        <div ref={scrollRef}></div>
      </div>
      <form onSubmit={sendMessage} className="chat-form">
        <input
          type="text"
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="Type your message..."
          required
        />
        <button type="submit">Send</button>
      </form>
      {error && <div className="error">{error}</div>}
    </div>
  );
}
