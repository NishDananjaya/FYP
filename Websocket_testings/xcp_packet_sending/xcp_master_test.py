# xcp_server_threaded.py
import threading
import queue
import struct
import time
from websocket_server import WebsocketServer

tx_queue = queue.Queue()

# Create XCP packet: PID (1 byte), timestamp (4 bytes), data (n bytes)
def create_xcp_packet(pid, data: bytes) -> bytes:
    timestamp = int(time.time())
    header = struct.pack(">BI", pid, timestamp)  # B=1 byte, I=4 bytes
    return header + data

def new_client(client, server):
    print(f"[+] Client connected: {client['id']}")

def client_left(client, server):
    print(f"[-] Client disconnected: {client['id']}")

def message_received(client, server, message):
    print(f"[←] Server RX (not used): {message}")

def tx_worker(server):
    while True:
        if not tx_queue.empty():
            packet = tx_queue.get()
            hex_packet = packet.hex()
            for client in server.clients:
                server.send_message(client, hex_packet)
                print(f"[→] Server TX: {hex_packet}")

def start_server():
    server = WebsocketServer(host='0.0.0.0', port=8000)
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)

    threading.Thread(target=tx_worker, args=(server,), daemon=True).start()
    print("🟢 XCP Server running on ws://0.0.0.0:8000")
    server.run_forever()

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()

    while True:
        try:
            raw_data = input("Enter hex data bytes (e.g. 11 22 33): ")
            data = bytes.fromhex(raw_data)
            pid = 0xF1  # Static PID for now
            packet = create_xcp_packet(pid, data)
            tx_queue.put(packet)
        except ValueError:
            print("Invalid input. Use hex bytes.")

