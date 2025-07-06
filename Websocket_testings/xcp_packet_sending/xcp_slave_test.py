# client.py
import websocket
import threading

rx_buffer = []

def on_message(ws, message):
    try:
        raw = bytes.fromhex(message)
        rx_buffer.append(raw)
        print(f"[←] Client RX Buffer: {[p.hex() for p in rx_buffer]}")
    except Exception as e:
        print(f"[!] Failed to decode: {e}")

def on_open(ws):
    print("[+] Connected to server")

ws = websocket.WebSocketApp("wss://evenly-pure-titmouse.ngrok-free.app",
                            on_message=on_message,
                            on_open=on_open)

threading.Thread(target=ws.run_forever, daemon=True).start()

while True:
    pass  # Keep running
