import enum
import typing as t
from pathlib import Path

from .protocol import Protocol
from .memory import (
    UnknownMemory,
    FrequencyMemory,
    ChannelMemory,
    GeneralMemory,
    PhoneMemory)


class RadioMemoryState(int, enum.Enum):
    AVAILABLE = 0x00       # 0x00: filled with 0x00
    UNKNOWN_DATA = 0x02    # 0x02: likely radio specific calibration data
    GENERAL_DATA = 0x04    # 0x04
    PHONE_DATA = 0x06      # 0x06
    FREQUENCY_DATA = 0x16  # 0x16
    CHANNEL_DATA = 0x24    # 0x24
    UNAVAILABLE = 0xFF     # 0xFF: filled with 0xFF

    # unknown memory types that are not read/written by the CPS
    UNKNOWN_A = 0x06    # seems to contain structured data
    UNKNOWN_B = 0x17    # seems to contain repeating test pattern
    UNKNOWN_C = 0x18    # seems to contain repeating test pattern
    UNKNOWN_D = 0x19    # seems to contain repeating test pattern
    UNKNOWN_E = 0x25    # seems to contain repeating test pattern
    UNKNOWN_F = 0x26    # seems to contain repeating test pattern


class RadioConfig:
    """
    Radio configuration.

    This class wraps memory segments that store the radio configuration data.
    It proxies public member attributes to the first matching field in memory
    segment blocks to make it easy to change relevant settings without knowing
    which segment they are contained in ahead of time.
    """

    MEMORY_SEGMENT_COUNT = 15
    CONFIG_FILE_ADDRESS = {
        RadioMemoryState.UNKNOWN_DATA: 0x2000,
        RadioMemoryState.FREQUENCY_DATA: 0x3000,
        RadioMemoryState.CHANNEL_DATA: 0x4000,
        RadioMemoryState.GENERAL_DATA: 0x5000,
        RadioMemoryState.PHONE_DATA: 0x6000}

    def __init__(self):
        self._memory_states = [None] * self.MEMORY_SEGMENT_COUNT
        self._memory_data = {
            RadioMemoryState.UNKNOWN_DATA: UnknownMemory(),
            RadioMemoryState.FREQUENCY_DATA: FrequencyMemory(),
            RadioMemoryState.CHANNEL_DATA: ChannelMemory(),
            RadioMemoryState.GENERAL_DATA: GeneralMemory(),
            RadioMemoryState.PHONE_DATA: PhoneMemory()}

    def __getattr__(self, key):
        try:
            # check if the attribute exists in this class and use the default
            # bahevior if it does
            return self.__getattribute__(key)

        except AttributeError as e:
            # ignore private attributes to prevent recursion
            if not key.startswith('_'):
                # proxy to memory data block field
                for memory in self._memory_data.values():
                    if hasattr(memory, key):
                        return getattr(memory, key)

            # re-raise original error
            raise e

    def __setattr__(self, key, value):
        # ignore private attributes to prevent recursion
        if not key.startswith('_'):
            # proxy to memory data block field
            for memory in self._memory_data.values():
                if hasattr(memory, key):
                    return setattr(memory, key, value)

        # fall back to default behavior
        return super().__setattr__(key, value)

    def _get_segment_base_address(self, index: int) -> int:
        # 0x1000 through 0xF000
        return (index + 1) * 0x1000

    def _get_segment_state_address(self, index: int) -> int:
        # last byte in each segment stores it's state
        return self._get_segment_base_address(index) + 0x0FFF

    def _detect_memory_segments(self, protocol: Protocol):
        for i in range(self.MEMORY_SEGMENT_COUNT):
            raw_data = protocol.read_memory(
                address=self._get_segment_state_address(i),
                size=0x01)

            self._memory_states[i] = RadioMemoryState(raw_data[0])

    def _locate_memory_segment(self, state: RadioMemoryState) -> int:
        matching_segments = [
            i for i in range(self.MEMORY_SEGMENT_COUNT)
            if self._memory_states[i] == state]

        if len(matching_segments) == 0:
            raise RuntimeError(
                f"Memory segment not found: {state.name}")

        elif len(matching_segments) > 1:
            raise RuntimeError(
                f"Multiple memory segments found: {state.name}")

        return matching_segments[0]

    def read_file(self, config_file: t.BinaryIO):
        config_file.seek(0)
        data = config_file.read()

        if len(data) != 0x7000:
            raise RuntimeError("Unexpected config file length")

        for state, base_address in self.CONFIG_FILE_ADDRESS.items():
            memory = self._memory_data[state]
            end_address = base_address + memory.get_size()
            memory.import_data(data[base_address:end_address])

    def write_file(self, config_file: t.BinaryIO):
        config_file.truncate(0)
        config_file.write(bytes([0x00] * 0x7000))
        config_file.seek(0)

        for state, base_address in self.CONFIG_FILE_ADDRESS.items():
            memory = self._memory_data[state]
            config_file.seek(base_address)
            config_file.write(memory.export_data())

    def read_radio(self, device_path: Path):
        with Protocol.open_port(device_path) as serial_port:
            protocol = Protocol(serial_port)

            print("Entering programming mode")
            protocol.unknown_init()

            print("Detecting memory segments")
            self._detect_memory_segments(protocol)

            # read memory segments
            for state, memory in self._memory_data.items():
                index = self._locate_memory_segment(state)
                base_address = self._get_segment_base_address(index)

                memory_name = state.name.lower().rstrip('_data')
                print(
                    f"Reading {memory_name} memory from segment "
                    f"{hex(index)} @ {hex(base_address)}")

                data = protocol.read_memory_range(
                    address=base_address,
                    size=memory.get_size())

                memory.import_data(data)

    def write_radio(self, device_path: Path):
        with Protocol.open_port(device_path) as serial_port:
            protocol = Protocol(serial_port)

            print("Entering programming mode")
            protocol.unknown_init()

            print("Detecting memory segments")
            self._detect_memory_segments(protocol)

            # write memory segments
            for state, memory in self._memory_data.items():
                memory_name = state.name.lower().rstrip('_data')
                index = self._locate_memory_segment(state)
                base_address = self._get_segment_base_address(index)

                # TODO: do not write the unknown data segment until we know
                # more about what is in there or we risk breaking the radio
                if state == RadioMemoryState.UNKNOWN_DATA:
                    print(
                        f"Skipping {memory_name} memory at segment "
                        f"{hex(index)} @ {hex(base_address)}")

                    continue

                # write memory segment
                print(
                    f"Writing {memory_name} memory to segment "
                    f"{hex(index)} @ {hex(base_address)}")

                protocol.write_memory_range(
                    address=base_address,
                    data=memory.export_data())

    def hexdump(self):
        for state, memory in self._memory_data.items():
            memory_name = state.name.lower().rstrip('_data')
            print(f"\n{memory_name.capitalize()} Memory:")
            print('-' * 86)
            memory.hexdump(minor_len=2, major_len=8)
            print(('-' * 86))
