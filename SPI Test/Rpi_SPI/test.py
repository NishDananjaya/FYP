import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)  # SPI bus 0, device 0
spi.max_speed_hz = 500000
spi.mode = 0b00  # SPI Mode 0 (CPOL=0, CPHA=0)

# Fixed transmit pattern (never changes)
tx_data = [0x00, 0x02, 0x03, 0x04, 0xFE, 0xFD, 0xFC, 0xFB]

try:
    while True:
        # Create a new rx_data buffer for received data
        rx_data = spi.xfer2(tx_data.copy())  # Use .copy() to avoid modifying tx_data

        print(f"Sent     : {[hex(b) for b in tx_data]}")
        print(f"Received : {[hex(b) for b in rx_data]}")
        print("-" * 40)

        time.sleep(1)

except KeyboardInterrupt:
    print("Interrupted.")

finally:
    spi.close()
