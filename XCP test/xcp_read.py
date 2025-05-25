import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 500000
spi.mode = 0b00

def xfer8(command):
    """Send 8-byte command and receive 8-byte response."""
    print(f"Sending: {command}")
    spi.xfer2(command)
    response = spi.xfer2([0xFF] * 8)  # Dummy send to receive response
    print(f"Received: {response}")
    return response

try:
    time.sleep(0.1)

    #  Disconnect existing session
    print("Sending XCP DISCONNECT...")
    response = xfer8([0xFE] + [0x00]*7)

    # Connect to XCP slave
    print("Sending XCP CONNECT...")
    response = xfer8([0xFF] + [0x00]*7)
    if response[0] != 0xFF:
        print("XCP CONNECT failed!")
        raise RuntimeError("Failed to CONNECT")

    # Send SET_MTA only if CONNECT successful
    print("Sending SET_MTA to 0x20000000...")
    set_mta_cmd = [0xF6, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20]  # Little endian 0x20000000
    response = xfer8(set_mta_cmd)
    if response[0] != 0xFF:
        print("SET_MTA failed!")
        raise RuntimeError("Failed to SET MTA")

    # UPLOAD command to read 4 bytes
    print("Sending UPLOAD for 4 bytes...")
    upload_cmd = [0xF5, 0x04] + [0x00]*6
    response = xfer8(upload_cmd)
    if response[0] == 0xFF:
        print("UPLOAD success. Data from 0x20000000:")
        print(response[1:1+4])  # print the 4 data bytes
    else:
        print("UPLOAD failed!")
        raise RuntimeError("Failed to UPLOAD")

    # Disconnect
    print("Sending XCP DISCONNECT...")
    xfer8([0xFE] + [0x00]*7)

finally:
    spi.close()
