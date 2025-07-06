#!/usr/bin/env python3
"""
XCP Master Implementation in Python

This script implements an XCP master for communication with an XCP slave device.
It provides functions to connect, read, and write parameters using the XCP protocol.
"""

import socket
import struct
import time
import threading
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# XCP Protocol Constants
class XcpCmd(Enum):
    CONNECT = 0xFF
    DISCONNECT = 0xFE
    GET_STATUS = 0xFD
    SYNCH = 0xFC
    GET_ID = 0xFA
    GET_SEED = 0xF8
    UNLOCK = 0xF7
    SET_MTA = 0xF6
    UPLOAD = 0xF5
    SHORT_UPLOAD = 0xF4
    BUILD_CHECKSUM = 0xF3
    TRANSPORT_LAYER_CMD = 0xF2
    USER_CMD = 0xF1
    DOWNLOAD = 0xF0
    DOWNLOAD_NEXT = 0xEF
    DOWNLOAD_MAX = 0xEE
    SHORT_DOWNLOAD = 0xED
    MODIFY_BITS = 0xEC
    SET_CAL_PAGE = 0xEB
    GET_CAL_PAGE = 0xEA
    GET_PAG_PROCESSOR_INFO = 0xE9
    GET_SEGMENT_INFO = 0xE8
    GET_PAGE_INFO = 0xE7
    SET_SEGMENT_MODE = 0xE6
    GET_SEGMENT_MODE = 0xE5
    COPY_CAL_PAGE = 0xE4
    CLEAR_DAQ_LIST = 0xE3
    SET_DAQ_PTR = 0xE2
    WRITE_DAQ = 0xE1
    SET_DAQ_LIST_MODE = 0xE0
    GET_DAQ_LIST_MODE = 0xDF
    START_STOP_DAQ_LIST = 0xDE
    START_STOP_SYNCH = 0xDD
    GET_DAQ_CLOCK = 0xDC
    READ_DAQ = 0xDB
    GET_DAQ_PROCESSOR_INFO = 0xDA
    GET_DAQ_RESOLUTION_INFO = 0xD9
    GET_DAQ_LIST_INFO = 0xD8
    GET_DAQ_EVENT_INFO = 0xD7
    FREE_DAQ = 0xD6
    ALLOC_DAQ = 0xD5
    ALLOC_ODT = 0xD4
    ALLOC_ODT_ENTRY = 0xD3
    PROGRAM_START = 0xD2
    PROGRAM_CLEAR = 0xD1
    PROGRAM = 0xD0
    PROGRAM_RESET = 0xCF
    GET_PGM_PROCESSOR_INFO = 0xCE
    GET_SECTOR_INFO = 0xCD
    PROGRAM_PREPARE = 0xCC
    PROGRAM_FORMAT = 0xCB
    PROGRAM_NEXT = 0xCA
    PROGRAM_MAX = 0xC9
    PROGRAM_VERIFY = 0xC8

# XCP Response Packet IDs
class XcpPid(Enum):
    RES = 0xFF  # Positive response
    ERR = 0xFE  # Error
    EV = 0xFD   # Event
    SERV = 0xFC # Service request

# XCP Error Codes
class XcpError(Enum):
    CMD_SYNC = 0x00
    CMD_BUSY = 0x10
    DAQ_ACTIVE = 0x11
    PGM_ACTIVE = 0x12
    CMD_UNKNOWN = 0x20
    CMD_SYNTAX = 0x21
    OUT_OF_RANGE = 0x22
    WRITE_PROTECTED = 0x23
    ACCESS_DENIED = 0x24
    ACCESS_LOCKED = 0x25
    PAGE_NOT_VALID = 0x26
    PAGE_MODE_NOT_VALID = 0x27
    SEGMENT_NOT_VALID = 0x28
    SEQUENCE = 0x29
    DAQ_CONFIG = 0x2A
    MEMORY_OVERFLOW = 0x30
    GENERIC = 0x31
    VERIFY = 0x32
    RESOURCE_TEMP_NOT_ACCESSIBLE = 0x33
    
class XcpMaster:
    def __init__(self, host='localhost', port=5555):
        """
        Initialize XCP master
        
        Args:
            host: Host address of XCP slave
            port: Port number of XCP slave
        """
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        self.timeout = 1.0  # Default timeout in seconds
        self.max_retries = 3
        self.lock = threading.Lock()
        self.callback = None
        self.dto_queue = []
        self.float_params = set()
        
    def connect_to_slave(self):
        """
        Connect to XCP slave via TCP
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to XCP slave at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to XCP slave: {e}")
            return False
            
    def disconnect_from_slave(self):
        """
        Disconnect from XCP slave
        """
        if self.sock:
            self.sock.close()
            self.sock = None
            self.connected = False
            logger.info("Disconnected from XCP slave")
            
    def send_command(self, command, data=None):
        """
        Send XCP command to slave
        
        Args:
            command: XCP command code
            data: Command data (optional)
            
        Returns:
            tuple: (success, response)
        """
        if not self.sock:
            logger.error("Not connected to XCP slave")
            return False, None
            
        # Build command packet
        if isinstance(command, XcpCmd):
            command = command.value
            
        packet = bytearray([command])
        if data:
            if isinstance(data, (list, tuple)):
                packet.extend(data)
            else:
                packet.append(data)
                
        # Send packet
        with self.lock:
            try:
                self.sock.send(packet)
                
                # Receive response
                response = self.sock.recv(1024)
                
                if not response:
                    logger.error("No response received from slave")
                    return False, None
                    
                # Check response PID
                pid = response[0]
                if pid == XcpPid.RES.value:
                    # Positive response
                    return True, response[1:]
                elif pid == XcpPid.ERR.value:
                    # Error response
                    error_code = response[1]
                    logger.error(f"XCP Error: {XcpError(error_code).name if error_code in [e.value for e in XcpError] else hex(error_code)}")
                    return False, error_code
                else:
                    # Other response (event, service request)
                    logger.warning(f"Unexpected response PID: {hex(pid)}")
                    return False, response
                    
            except socket.timeout:
                logger.error("Timeout waiting for slave response")
                return False, None
            except Exception as e:
                logger.error(f"Error communicating with slave: {e}")
                return False, None
                
    def xcp_connect(self, mode=0):
        """
        Establish XCP connection with slave
        
        Args:
            mode: Connection mode (0 = normal mode)
            
        Returns:
            bool: True if successful, False otherwise
        """
        success, response = self.send_command(XcpCmd.CONNECT, [mode])
        if success and response:
            self.connected = True
            
            # Parse response
            resource = response[0]
            comm_mode_basic = response[1]
            max_cto = response[2]
            max_dto = response[3] | (response[4] << 8)
            protocol_version = response[5]
            transport_version = response[6]
            
            logger.info(f"XCP Connected - Resource: {hex(resource)}, Max CTO: {max_cto}, Max DTO: {max_dto}")
            logger.debug(f"Protocol version: {protocol_version}, Transport version: {transport_version}")
            
            return True
        return False
        
    def xcp_disconnect(self):
        """
        Terminate XCP connection with slave
        
        Returns:
            bool: True if successful, False otherwise
        """
        success, _ = self.send_command(XcpCmd.DISCONNECT)
        if success:
            self.connected = False
            logger.info("XCP Disconnected")
            return True
        return False
        
    def xcp_get_status(self):
        """
        Get current status from slave
        
        Returns:
            tuple: (success, status_info)
        """
        success, response = self.send_command(XcpCmd.GET_STATUS)
        if success and response:
            status = {
                'session_status': response[0],
                'resource': response[1],
                'protection': response[2]
            }
            return True, status
        return False, None
        
    def xcp_set_mta(self, address, address_ext=0):
        """
        Set Memory Transfer Address
        
        Args:
            address: 32-bit address
            address_ext: Address extension
            
        Returns:
            bool: True if successful, False otherwise
        """
        data = [0, 0, address_ext]
        data.extend(struct.pack("<I", address))
        
        success, _ = self.send_command(XcpCmd.SET_MTA, data)
        return success
        
    def xcp_upload(self, size):
        """
        Upload data from slave memory (read from MTA)
        
        Args:
            size: Number of bytes to upload
            
        Returns:
            tuple: (success, data)
        """
        success, response = self.send_command(XcpCmd.UPLOAD, [size])
        if success:
            return True, response
        return False, None
        
    def xcp_download(self, data):
        """
        Download data to slave memory (write to MTA)
        
        Args:
            data: Bytes to download
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not isinstance(data, (bytes, bytearray)):
            if isinstance(data, (int, float)):
                # Convert single value to bytes
                if isinstance(data, int):
                    data = struct.pack("<I", data)
                else:  # float
                    data = struct.pack("<f", data)
            else:
                data = bytes(data)
                
        packet = [len(data)]
        packet.extend(data)
        
        success, _ = self.send_command(XcpCmd.DOWNLOAD, packet)
        return success
        
    def xcp_short_upload(self, address, address_ext, size):
        """
        Upload data from specific address
        
        Args:
            address: 32-bit address
            address_ext: Address extension
            size: Number of bytes to upload
            
        Returns:
            tuple: (success, data)
        """
        data = [size, 0, address_ext]
        data.extend(struct.pack("<I", address))
        
        success, response = self.send_command(XcpCmd.SHORT_UPLOAD, data)
        if success:
            return True, response
        return False, None
        
    def xcp_short_download(self, address, address_ext, data):
        """
        Download data to specific address
        
        Args:
            address: 32-bit address
            address_ext: Address extension
            data: Bytes to download
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not isinstance(data, (bytes, bytearray)):
            if isinstance(data, (int, float)):
                # Convert single value to bytes
                if isinstance(data, int):
                    data = struct.pack("<I", data)
                else:  # float
                    data = struct.pack("<f", data)
            else:
                data = bytes(data)
                
        packet = [len(data), 0, address_ext]
        packet.extend(struct.pack("<I", address))
        packet.extend(data)
        
        success, _ = self.send_command(XcpCmd.SHORT_DOWNLOAD, packet)
        return success
        
    def read_parameter(self, address, size):
        """
        Read parameter value from memory
        
        Args:
            address: Parameter address
            size: Parameter size in bytes
            
        Returns:
            Value read from memory, or None if failed
        """
        success, data = self.xcp_short_upload(address, 0, size)
        if not success or not data:
            return None
            
        # Convert bytes to appropriate type based on size
        if size == 1:
            return data[0]
        elif size == 2:
            return struct.unpack("<H", data[:2])[0]
        elif size == 4:
            if address in self.float_params:
                return struct.unpack("<f", data[:4])[0]
            else:
                return struct.unpack("<I", data[:4])[0]
        else:
            return data
            
    def write_parameter(self, address, value, size):
        """
        Write parameter value to memory
        
        Args:
            address: Parameter address
            value: Value to write
            size: Parameter size in bytes
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Convert value to bytes based on size
        if size == 1:
            data = bytes([value & 0xFF])
        elif size == 2:
            data = struct.pack("<H", value)
        elif size == 4:
            if address in self.float_params:
                data = struct.pack("<f", value)
            else:
                data = struct.pack("<I", value)
        else:
            if not isinstance(value, (bytes, bytearray)):
                return False
            data = value
            
        return self.xcp_short_download(address, 0, data)
        
    def set_float_parameters(self, addresses):
        """
        Set which parameter addresses contain float values
        
        Args:
            addresses: List of addresses containing float values
        """
        self.float_params = set(addresses)
        
    def register_dto_callback(self, callback):
        """
        Register callback for DTO packets
        
        Args:
            callback: Function to call when DTO packet is received
        """
        self.callback = callback
        
    def start_dto_reception(self):
        """
        Start thread to receive DTO packets
        """
        self.dto_thread = threading.Thread(target=self._dto_receiver)
        self.dto_thread.daemon = True
        self.dto_thread.start()
        
    def _dto_receiver(self):
        """
        Thread function to receive DTO packets
        """
        while self.connected:
            try:
                if self.sock:
                    # Set socket to non-blocking mode for this check
                    self.sock.setblocking(0)
                    
                    try:
                        data = self.sock.recv(1024)
                        if data:
                            # Process DTO packet
                            if self.callback:
                                self.callback(data)
                            else:
                                self.dto_queue.append(data)
                    except socket.error:
                        # No data available
                        pass
                        
                    # Set socket back to blocking mode
                    self.sock.setblocking(1)
                    
                time.sleep(0.01)  # Small delay to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in DTO receiver: {e}")
                time.sleep(0.1)  # Delay before retry
                
    def get_dto_packets(self):
        """
        Get received DTO packets
        
        Returns:
            list: List of received DTO packets
        """
        packets = self.dto_queue.copy()
        self.dto_queue.clear()
        return packets