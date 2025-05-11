const WebSocket = require('ws');
const express = require('express');
const http = require('http');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Store latest metrics
let latestMetrics = {};

// Store connected WebSocket clients
const clients = new Set();

wss.on('connection', (ws) => {
    console.log('New client connected');
    clients.add(ws);

    // Send initial metrics to the new client
    ws.send(JSON.stringify(latestMetrics));

    ws.on('message', (message) => {
        try {
            const metrics = JSON.parse(message);
            latestMetrics = metrics;
            console.log('Received metrics:', metrics);

            // Broadcast to all connected clients
            clients.forEach((client) => {
                if (client.readyState === WebSocket.OPEN) {
                    client.send(JSON.stringify(metrics));
                }
            });
        } catch (e) {
            console.error('Error processing message:', e);
        }
    });

    ws.on('close', () => {
        console.log('Client disconnected');
        clients.delete(ws);
    });
});

// Serve static files (e.g., index.html)
app.use(express.static(path.join(__dirname)));

// Endpoint for initial metrics
app.get('/metrics', (req, res) => {
    res.json(latestMetrics);
});

// Start the combined server
server.listen(8000, () => {
    console.log('Server running on http://0.0.0.0:8000');
    console.log('WebSocket server running on ws://0.0.0.0:8000');
});
