import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 500000  # Set to 500 kHz
spi.mode = 0b00  # SPI Mode 0 (CPOL=0, CPHA=0)

def send_command(cmd):
    if len(cmd) != 8:
        raise ValueError("Command must be 8 bytes")

    print(f">> Sending: {cmd}")
    spi.xfer2(cmd)

    time.sleep(0.01)
    spi.xfer2([0xAA] * 8)  # Dummy read
    response = spi.xfer2([0xAA] * 8)
    print(f"<< Received: {response}")
    return response

def interactive_sequence():
    """Prompt user to select and send XCP commands one by one."""
    try:
        while True:
            print("\nAvailable XCP Commands:")
            print("1. DISCONNECT")
            print("2. CONNECT")
            print("3. SET_MTA (to 0x20000028)")
            print("4. UPLOAD (4 bytes)")
            print("5. WRITE (Set MTA + Download)")
            print("6. Exit")
            choice = input("Enter command number (1-6): ")

            if choice == "1":
                print("Sending XCP DISCONNECT...")
                send_command([0xFE] + [0x00]*7)

            elif choice == "2":
                print("Sending XCP CONNECT...")
                send_command([0xFF] + [0x00]*7)

            elif choice == "3":
                print("Sending SET_MTA to 0x20000028...")
                set_mta_cmd = [0xF6, 0x00, 0x00, 0x00, 0x28, 0x00, 0x00, 0x20]
                send_command(set_mta_cmd)

            elif choice == "4":
                print("Sending UPLOAD for 4 bytes...")
                upload_cmd = [0xF5, 0x04] + [0x00]*6
                response = send_command(upload_cmd)
                if response:
                    print(f"<< Upload Response: {response}")
                    print("Data:", response[1:5])

            elif choice == "5":
                print("Sending SET_MTA to 0x20000028...")
                set_mta = [0xF6, 0x00, 0x00, 0x00, 0x28, 0x00, 0x00, 0x20]
                response = send_command(set_mta)
                if response[0] != 0xFF:
                    raise RuntimeError("Failed to SET MTA")

                print("Enter 4 bytes to write (0-255), separated by space:")
                try:
                    user_input = input(">> ").strip().split()
                    if len(user_input) != 4:
                        raise ValueError("Please enter exactly 4 bytes.")

                    data_bytes = [int(b) & 0xFF for b in user_input]
                except ValueError as ve:
                    print(f"Input error: {ve}")
                    continue

                # DOWNLOAD 4 bytes
                download_cmd = [0xF0, 0x04] + data_bytes + [0x00] * (8 - 2 - len(data_bytes))
                print(f"Sending DOWNLOAD with data: {data_bytes}")
                response = send_command(download_cmd)
                if response[0] != 0xFF:
                    raise RuntimeError("DOWNLOAD failed!")

            elif choice == "6":
                print("Exiting...")
                break

            else:
                print("Invalid choice. Please enter a number between 1 and 6.")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        spi.close()

if __name__ == "__main__":
    interactive_sequence()
