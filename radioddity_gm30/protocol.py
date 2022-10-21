import struct
from pathlib import Path
from datetime import timedelta

import serial


class Protocol:
    """
    Serial programming protocol.

    The protocol loosely follows a request/response flow with one-way or
    bi-directional acknowledgements. It relies on hardware flow control.

    Requests:
    - Command Requests
    - PSEARCH Request
    - PASSSTA Request (?)
    - SYSINFO Request (?)

    PSEARCH Request:
    - Send Bytes: 'PSEARCH' as ASCII
    - Read Ack:
      - 1x Byte: 0x06
    - Read Variable Length Response: Firmware variant name as ASCII
      - Known Variant: P13GMRS (US region GMRS firmware)

    Command Requests:
    - 1x Bytes: Request Type
    - 0x or 4x Bytes: Parameters

    Command Ack Request:
    - Type: 0x06
    - Parameters: N/A
    - Response: 0x06

    Command Read Request:
    - Radio must be in programming mode first.
    - Type: 0x52
    - Parameters:
      - 2x Bytes: Little-Endian Address
      - 1x Byte: 0x00 (?)
      - 1x Byte: Read Size
    - Response:
      - 1x Byte: 0x57
      - 2x Bytes: Little-Endian Address
      - 1x Byte: 0x00 (?)
      - 1x Byte: Read Size (Not Including 5x Byte Header)
      - Read Size x Bytes: Data
    - Requires Ack Request After

    Command Write Request:
    - Radio must be in programming mode first.
    - Type: 0x57
    - Parameters:
      - 2x Bytes: Little-Endian Address
      - 1x Byte: 0x00 (?)
      - 1x Byte: Write Size (Not Including 4x Byte Header)
      - Write Size x Bytes: Data
    - Response:
      - 1x Byte: 0x06
    """

    @staticmethod
    def open_port(device_path: Path) -> serial.Serial:
        return serial.Serial(
            port=str(device_path),
            baudrate=57600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=True,
            dsrdtr=True,
            timeout=None)

    def __init__(
        self,
        port: serial.Serial,
        timeout: timedelta = timedelta(seconds=1)
    ):
        self.port = port
        self.timeout = timeout

    def _reset(self):
        # XXX: log warning if buffers are not empty
        # XXX: not sure if this is actually necessary or useful
        self.port.reset_input_buffer()
        self.port.reset_output_buffer()

    def _fixed_write(self, data: bytes) -> int:
        self.port.write(data)
        self.port.flush()

    def _variable_read(self, max_count: int) -> bytes:
        self.port.timeout = self.timeout.total_seconds()
        return self.port.read(max_count)

    def _fixed_read(self, expected_count: int) -> bytes:
        response = self._variable_read(expected_count)
        if not response:
            self._reset()
            raise RuntimeError("No response received")

        if len(response) != expected_count:
            self._reset()
            raise RuntimeError("Unexpected read size")

        return response

    def send_ack(self):
        self._fixed_write(bytes([0x06]))

    def receive_ack(self):
        response = self._fixed_read(1)
        if response != bytes([0x06]):
            raise RuntimeError("Failed to receive ACK")

    def read_memory(self, address: int, size: int) -> bytes:
        # sanity check
        if size <= 0:
            raise RuntimeError("Memory read with non-positive size")

        # Request: 0x52 ADDRx2 0x00 SIZEx1
        request = bytearray([0x52, 0x00, 0x00, 0x00, 0x00])
        struct.pack_into('<HxB', request, 1, address, size)
        self._fixed_write(request)

        # Response: 0x57 ADDRx2 0x00 SIZEx1 [DATAx1 .. DATAx1]
        response = self._fixed_read(5 + size)
        if response[0] != 0x57 or response[1:5] != request[1:5]:
            raise RuntimeError("Read memory response invalid header")

        # Sync
        self.send_ack()
        self.receive_ack()

        return response[5:]

    def write_memory(self, address: int, data: bytes):
        # sanity check
        if not data:
            raise RuntimeError("Memory write with non-positive size")

        # Request: 0x57 ADDRx2 0x00 SIZEx1 [DATAx1 .. DATAx2]
        request = bytearray([0x57, 0x00, 0x00, 0x00, 0x00])
        struct.pack_into('<HxB', request, 1, address, len(data))
        self._fixed_write(request + data)

        # Sync
        self.receive_ack()

    def read_memory_range(
        self,
        address: int,
        size: int,
        chunk_size: int = 0x40
    ) -> bytes:
        # sanity check
        if size <= 0:
            raise RuntimeError("Memory read with non-positive size")

        data = bytearray()
        read_address = address
        read_bytes_remaining = size

        while read_bytes_remaining > 0:
            read_size = min(chunk_size, read_bytes_remaining)
            data += self.read_memory(read_address, read_size)

            read_bytes_remaining -= read_size
            read_address += read_size

        return bytes(data)

    def write_memory_range(
        self,
        address: int,
        data: bytes,
        chunk_size: int = 0x40
    ):
        # sanity check
        if not data:
            raise RuntimeError("Memory write with non-positive size")

        write_counter = 0
        while write_counter < len(data):
            write_size = min(chunk_size, len(data) - write_counter)
            write_data = data[write_counter:write_counter + write_size]
            self.write_memory(address + write_counter, write_data)

            write_counter += write_size

    def query_firmware_variant(self) -> str:
        # Request
        self._fixed_write(b'PSEARCH')
        self.receive_ack()

        # Response: firmware variant name
        # Known variants: P13GMRS
        response = self._variable_read(16)
        if not response:
            self._reset()
            raise RuntimeError(
                "Firmware variant query did not receive a response")

        return response.decode()

    # Not yet understood parts of the protocol.

    def unknown_passsta(self):
        self._fixed_write(b'PASSSTA')
        response = self._fixed_read(3)
        assert response[:1].decode() == 'P'
        assert response[1] == 0x00
        assert response[2] == 0x00

    def unknown_sysinfo(self):
        self._fixed_write(b'SYSINFO')
        self.receive_ack()

    def unknown_init(
        self,
        query_unknown_passsta: bool = True,
        query_unknown_sysinfo: bool = True
    ):
        # querying for use later on when entering programming mode
        # XXX not required to enter read/write mode
        fw_variant = self.query_firmware_variant()
        assert fw_variant == 'P13GMRS'

        # XXX checking whether a password is set?
        # XXX not required to enter programming mode
        if query_unknown_passsta:
            self.unknown_passsta()

        # XXX required to enter programming mode
        self.unknown_sysinfo()

        # XXX some kind of timestamp query or checksum calculation?
        # XXX seems to change based on the contents of radio memory
        # XXX does not seem to change over time on it's own
        # XXX requires sysinfo command to be sent first
        # XXX not required to enter programming mode
        if query_unknown_sysinfo:
            # XXX
            self._fixed_write(bytes([0x56, 0x00, 0x00, 0x0A, 0x0D]))
            response = self._fixed_read(5)
            assert response == bytes([0x56, 0x0D, 0x0A, 0x0A, 0x0D])

            response = self._fixed_read(8)
            print(response.hex(' '))

            self.send_ack()
            self.receive_ack()

            # XXX
            self._fixed_write(bytes([0x56, 0x00, 0x10, 0x0A, 0x0D]))
            response = self._fixed_read(5)
            assert response == bytes([0x56, 0x0D, 0x0A, 0x0A, 0x0D])

            response = self._fixed_read(8)
            print(response.hex(' '))

            self.send_ack()
            self.receive_ack()

            # XXX
            self._fixed_write(bytes([0x56, 0x00, 0x20, 0x0A, 0x0D]))
            response = self._fixed_read(5)
            assert response == bytes([0x56, 0x0D, 0x0A, 0x0A, 0x0D])

            response = self._fixed_read(8)
            print(response.hex(' '))

            self.send_ack()
            self.receive_ack()

            # XXX seems to be different variant then three queries above?
            self._fixed_write(bytes([0x56, 0x00, 0x00, 0x00, 0x0A]))
            response = self._fixed_read(5)
            assert response == bytes([0x56, 0x0A, 0x08, 0x00, 0x10])

            response = self._fixed_read(6)
            print(response.hex(' '))
            assert response == bytes([0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00])

            self.send_ack()
            self.receive_ack()

        # XXX: this seems to set a timeout where if no further commands are
        # received within a certain window the radio will reset
        # required to enter programming mode
        self._fixed_write(bytes([0xFF, 0xFF, 0xFF, 0xFF, 0x0C]))
        self._fixed_write(fw_variant.encode())  # XXX: b'P13GMRS'
        self.receive_ack()

        # XXX required to enter programming mode
        self._fixed_write(bytes([0x02]))
        response = self._fixed_read(8)
        assert response == bytes([0xFF] * 8)

        self.send_ack()
        self.receive_ack()
