const Websocket = require("ws");

//Create a websocket server on port 8080

const wss = new Websocket.Server({ port: 8080 });

wss.on('connection', function connection(ws) {
	console.log('New client connected');

	ws.on('message', function incoming(message) {
		console.log('Recieved from client:', message.toString())		//Example reply back to client
		ws.send('Server recieved: ${message}');
	});

	ws.on('close', () => {
		console.log('Client disconnected');
	});

	// Send a welcome message when connected
	ws.send('Hello from Raspberry Pi server!');
});

console.log('WebSocket server running at ws://172.20.114.198:8080');