import socket
import threading
import json
import time
import numpy as np
# from gui_test import PARAMETER_DEFS  # Import parameter definitions
# from parameters import PARAMETER_DEFS  # Ensure parameter definitions are available

class WebSocketServer:
    def __init__(self, xcp_master=None, host='0.0.0.0', port=8000):
        self.xcp_master = xcp_master
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.running = False
        self.current_values = {}  # Store latest values
        self.value_callbacks = []  # For GUI updates
        self.connection_callbacks = []  # For connection status updates

    def register_value_callback(self, callback):
        """Register a callback for value updates"""
        self.value_callbacks.append(callback)

    def register_connection_callback(self, callback):
        """Register a callback for connection status changes"""
        self.connection_callbacks.append(callback)

    def start(self):
        """Start the JSON-over-TCP server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        self.running = True
        print(f"🟢 Server listening on {self.host}:{self.port}")
        threading.Thread(target=self._accept_clients, daemon=True).start()

    def _accept_clients(self):
        while self.running:
            try:
                client, addr = self.server_socket.accept()
                self.clients.append(client)
                print(f"➕ Client connected: {addr}")
                self._notify_connection_change(True)
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting new client: {e}")

    def _handle_client(self, client):
        addr = client.getpeername()
        try:
            while self.running:
                raw = client.recv(4096)
                if not raw:
                    break

                msg = raw.decode('utf-8')
                print(f"⬅️ {msg}")
                resp = self._process_message(msg)
                
                # If response contains values, store and notify
                if "value" in resp:
                    param_name = self._address_to_param_name(resp.get("address"))
                    if param_name:
                        self.current_values[param_name] = resp["value"]
                        self._notify_value_update(self.current_values)
                
                client.send(json.dumps(resp).encode('utf-8'))
        except Exception as e:
            print(f"Error with client {addr}: {e}")
        finally:
            client.close()
            if client in self.clients:
                self.clients.remove(client)
            print(f"➖ Client disconnected: {addr}")
            self._notify_connection_change(len(self.clients) > 0)

    def _process_message(self, message):
        try:
            data = json.loads(message)
            cmd = data.get("command")
            p = data.get("params", {})

            if cmd == "read":
                addr = p.get("address")
                size = p.get("size")
                if addr is None or size is None:
                    return {"error": "Missing address or size"}
                
                # Simulate response if no XCP master
                val = self._simulate_read(addr, size) if self.xcp_master is None else self.xcp_master.read_parameter(addr, size)
                return {"command": "read", "address": addr, "value": val, "ts": time.time()}

            elif cmd == "write":
                addr = p.get("address")
                val = p.get("value")
                size = p.get("size")
                if None in (addr, val, size):
                    return {"error": "Missing address, value or size"}
                
                # Simulate response if no XCP master
                ok = True if self.xcp_master is None else self.xcp_master.write_parameter(addr, val, size)
                return {"command": "write", "address": addr, "success": ok, "ts": time.time()}

            else:
                return {"error": "Unknown command"}

        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}
        except Exception as e:
            return {"error": str(e)}

    def _simulate_read(self, address, size):
        """Simulate reading a parameter value"""
        param = next((p for p in PARAMETER_DEFS if p["address"] == address), None)
        if param:
            if param["type"] == "float":
                return round(np.random.uniform(param["min"], param["max"]), 3)
            else:
                return np.random.randint(param["min"], param["max"])
        return 0

    def _address_to_param_name(self, address):
        """Convert address to parameter name"""
        for param in PARAMETER_DEFS:
            if param["address"] == address:
                return param["name"]
        return None

    def _notify_value_update(self, values):
        """Notify all registered callbacks of new values"""
        for callback in self.value_callbacks:
            callback(values)

    def _notify_connection_change(self, connected):
        """Notify all registered callbacks of connection changes"""
        for callback in self.connection_callbacks:
            callback(connected)

    def stop(self):
        """Shut down the server and all connections"""
        self.running = False
        for c in self.clients:
            try:
                c.close()
            except:
                pass
        try:
            self.server_socket.close()
        except:
            pass
        print("🛑 Server stopped")

# In websocket_server_test.py
# At the bottom of the file after WebSocketServer class definition:
if __name__ != '__main__':
    from gui_test import PARAMETER_DEFS