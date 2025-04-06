import React, { useEffect, useState } from 'react';
import io from 'socket.io-client';

const socket = io('http://192.168.59.150:5000');

function IncidentList() {
  const [incidents, setIncidents] = useState([]); 
  const [notifications, setNotifications] = useState([]); 

  
  const fetchIncidents = async () => {
    const url = 'http://192.168.59.150:5000/incidents'; 
    const username = 'admin'; 
    const password = 'password'; 

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': 'Basic ' + btoa(`${username}:${password}`),
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setIncidents(data); 
      } else {
        console.error('Failed to fetch incidents:', response.statusText);
      }
    } catch (error) {
      console.error('Error fetching incidents:', error);
    }
  };

  useEffect(() => {
    
    if (Notification.permission !== 'granted') {
      Notification.requestPermission();
    }

    
    fetchIncidents();

   
    socket.on('new_incident', (data) => {
      console.log('New incident received:', data);

      setNotifications((prevNotifications) => [data, ...prevNotifications]);

      
      if (Notification.permission === 'granted') {
        new Notification('New Incident', {
          body: `Location: ${data.location}\nKeywords: ${data.keywords.join(', ')}`,
          icon: '/favicon.ico',
        });
      }
    });


    return () => {
      socket.off('new_incident');
    };
  }, []);

  return (
    <div>
      <h1>Incidents List</h1>
      <div>
        <h2>Live Notifications</h2>
        {notifications.length === 0 ? (
  <p>No notifications yet.</p>
) : (
  notifications.map((notification, index) => (
    <div
      key={index}
      style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '15px',
        width: '300px',
        boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
      }}
    >
      <h3>{notification.emergency}</h3>
      <p><strong>Location:</strong> {notification.location}</p>
      <p><strong>Keywords:</strong> {notification.keywords?.join(', ')}</p>
      <p>
        <strong>Decision:</strong>{' '}
        <button
          style={{
            backgroundColor: notification.decision === 'emergency' ? 'red' : 'green',
            color: 'white',
            border: 'none',
            padding: '5px 10px',
            borderRadius: '4px',
          }}
        >
          {notification.decision}
        </button>
      </p>
      {notification.image && (
        <img
          src={notification.image.startsWith('data:') ? notification.image : 'data:image/jpeg;base64,' + notification.image}
          alt="Incident"
          style={{ maxWidth: '100%', marginTop: '10px', borderRadius: '4px' }}
        />
      )}
    </div>
  ))
)}
      </div>
      <div>
        <h2>All Incidents</h2>
        {incidents.length === 0 ? (
          <p>No incidents yet.</p>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
            {incidents.map((incident, index) => (
              <div
                key={index}
                style={{
                  border: '1px solid #ddd',
                  borderRadius: '8px',
                  padding: '15px',
                  width: '300px',
                  boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
                }}
              >
                <h3>{incident.emergency}</h3>
                <p><strong>Location:</strong> {incident.location}</p>
                <p><strong>Keywords:</strong> {incident.keywords.join(', ')}</p>
                <p>
                  <strong>Decision:</strong>{' '}
                  <button
                    style={{
                      backgroundColor: incident.decision === 'emergency' ? 'red' : 'green',
                      color: 'white',
                      border: 'none',
                      padding: '5px 10px',
                      borderRadius: '4px',
                    }}
                  >
                    {incident.decision}
                  </button>
                </p>
                {incident.image && (
                  <img
                    src={incident.image.startsWith('data:') ? incident.image : 'data:image/jpeg;base64,' + incident.image}
                    alt="Incident"
                    style={{ maxWidth: '100%', marginTop: '10px', borderRadius: '4px' }}
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default IncidentList;