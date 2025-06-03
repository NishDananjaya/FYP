# xcp_ws_server.py
import asyncio
import websockets

# Example XCP DAQ packet components
pid = 0xF1
timestamp = 0x1234
data = bytes([0x00, 0x10, 0x00, 0x20])

def build_daq_packet(pid: int, timestamp: int, data: bytes) -> bytes:
    # PID: 1 byte
    pid_byte = pid.to_bytes(1, 'big')

    # Timestamp: assuming 2 bytes (16-bit)
    timestamp_bytes = timestamp.to_bytes(2, 'big')

    # Data: already in bytes
    packet = pid_byte + timestamp_bytes + data
    return packet

async def handler(websocket):
    print(f"[+] Client connected: {websocket.remote_address}")

    # Build and send DAQ packet
    daq_packet = build_daq_packet(pid, timestamp, data)
    await websocket.send(daq_packet)
    print(f"[→] Sent XCP DAQ Packet: {daq_packet.hex()}")

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                print(f"[←] Received binary from client: {message.hex()}")
            else:
                print(f"[←] Received text from client: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("[-] Client disconnected")

async def main():
    print("[*] Starting WebSocket server on port 8000...")
    async with websockets.serve(handler, "0.0.0.0", 8000):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
