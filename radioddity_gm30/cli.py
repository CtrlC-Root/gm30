import io
import argparse
import typing as t
from pathlib import Path

import serial
import serial.tools.list_ports

from .protocol import Protocol
from .radio_config import RadioConfig


CABLE_USB_VID_PID: t.List[t.Tuple[int, int]] = [
    (0x1A86, 0x7523)    # CH340 USB to Serial Adapter: Radioddity Cable
]


def detect_serial_port() -> t.Optional[str]:
    """
    Detect the default serial port by checking the USB vendor and product IDs
    against a known list of radio programming cables. Useful when you have a
    single cable connected to the computer otherwise this may not pick the
    right one.
    """

    for port_info in serial.tools.list_ports.comports():
        if (port_info.vid, port_info.pid) in CABLE_USB_VID_PID:
            return port_info.device

    return None


def read_memory(device_path: Path, data_file: t.BinaryIO):
    # truncate and initialize the data file with zeroes
    data_file.truncate(0)
    data_file.write(bytes([0x00] * 0xF000))
    data_file.seek(0)

    # initialize serial port and protocol
    with Protocol.open_port(device_path) as serial_port:
        protocol = Protocol(serial_port)
        protocol.unknown_init()

        # read all memory
        data_file.write(protocol.read_memory_range(0x1000, 0xF000))


def write_memory(device_path: Path, data_file: t.BinaryIO):
    # TODO: confirm with user they want to proceed
    print("Not safe to write to radio yet")
    import sys; sys.exit(1)  # noqa

    # sanity check data file size
    data_file_size = data_file.seek(0, io.SEEK_END)
    data_file.seek(0)

    if data_file_size != 0xF000:
        raise RuntimeError(f"Invalid data file size: {data_file_size}")

    # initialize serial port and protocol
    with Protocol.open_port(device_path) as serial_port:
        protocol = Protocol(serial_port)
        protocol.unknown_init()

        # TODO: we should limit this to only writing the memory segments we
        # know the CPS writes to instead of all memory, this is how I broke
        # one radio already

        # write data portion of each memory segment
        for i in range(15):
            data_file.seek(i * 0x1000)
            protocol.write_memory_range(
                (i + 1) * 0x1000,
                data_file.read(0xFFE))  # avoid overwriting the segment state byte


def read_config(device_path: Path, config_file: t.BinaryIO):
    # read config from radio
    radio_config = RadioConfig()
    radio_config.read_radio(device_path)

    # XXX dump memory
    print('\n')
    radio_config.hexdump()

    # save config to file
    radio_config.write_file(config_file)


def write_config(device_path: Path, config_file: t.BinaryIO):
    # TODO: read config from config file
    radio_config = RadioConfig()
    radio_config.read_file(config_file)

    # XXX dump memory
    radio_config.hexdump()
    print('\n')

    # TODO: confirm with user they want to proceed
    print("Not safe to write to radio yet")
    import sys; sys.exit(1)  # noqa

    # write config to radio
    radio_config.write_radio(device_path)


def main():
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--device', type=Path)

    subparsers = parser.add_subparsers()

    parser_read_memory = subparsers.add_parser('mr', help="read from radio memory")
    parser_read_memory.set_defaults(command='read_memory')
    parser_read_memory.add_argument(
        '-f', '--data-file',
        type=argparse.FileType('wb'),
        required=True)

    parser_write_memory = subparsers.add_parser('mw', help="write to radio memory")
    parser_write_memory.set_defaults(command='write_memory')
    parser_write_memory.add_argument(
        '-f', '--data-file',
        type=argparse.FileType('rb'),
        required=True)

    parser_read_config = subparsers.add_parser('read', help="read config from radio")
    parser_read_config.set_defaults(command='read_config')
    parser_read_config.add_argument(
        '-c', '--config-file',
        type=argparse.FileType('wb'),
        required=True)

    parser_write_config = subparsers.add_parser('write', help="write config to radio")
    parser_write_config.set_defaults(command='write_config')
    parser_write_config.add_argument(
        '-c', '--config-file',
        type=argparse.FileType('rb'),
        required=True)

    args = parser.parse_args()

    # determine serial port device path
    device_path = args.device or detect_serial_port()
    if not device_path:
        raise RuntimeError("Failed to automatically detect serial port")

    else:
        print(f"Using serial device: {device_path}")

    # run the requested command
    if args.command == 'read_memory':
        read_memory(device_path=device_path, data_file=args.data_file)

    elif args.command == 'write_memory':
        write_memory(device_path=device_path, data_file=args.data_file)

    elif args.command == 'read_config':
        read_config(device_path=device_path, config_file=args.config_file)

    elif args.command == 'write_config':
        write_config(device_path=device_path, config_file=args.config_file)
