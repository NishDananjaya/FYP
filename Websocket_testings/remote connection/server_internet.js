const WebSocket = require("ws");

// Create a WebSocket server on port 8080
const wss = new WebSocket.Server({ port: 8080 });

// Handle new client connections
wss.on('connection', function connection(ws) {
    console.log('New client connected');

    // Handle incoming messages from clients
    ws.on('message', function incoming(message) {
        console.log('Received from client:', message.toString());
        // Reply back to the client
        ws.send(`Server received: ${message}`);
    });

    // Handle client disconnection
    ws.on('close', () => {
        console.log('Client disconnected');
    });

    // Send a welcome message to the client
    ws.send('Hello from Raspberry Pi server!');
});

// Log the server status
console.log('WebSocket server running on port 8080');
