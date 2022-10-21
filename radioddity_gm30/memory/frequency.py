import enum
import struct

from mrcrowbar import models as mrc


# 00003010: 0025 5043 ffff ffff 00ff ffff ff06 1100  .%PC............
# VFO A: 435.02500, High, Wide, PTT Off, Busy Lock Off
# CTCSS Decode None, CTCSS Encode None, Freq Split Off
# Signaling Code 1, Freq Step 2.5k, Scan Add Greyed Out On, Freq Hopping: Off

# 00003020: 0025 5015 ffff ffff 00ff ffff ff06 1100  .%P.............
# VFO B: 155.02500, High, Wide, PTT Off, Busy Lock Off
# CTCSS Decode None, CTCSS Encode None, Freq Split Off
# Signaling Code 1, Freq Step 2.5k, Scan Add Greyed Out On, Freq Hopping: Off

# 00003030: 5062 2546 5062 2546 00ff ffff ff06 1100  Pb%FPb%F........
# CH1, RX: 462.56250, TX: 462.56250, Rx QD: None, Tx QD: None, Bw: Wide
# Power: High, PTT-ID: Off, Busy Lock: No, Scan Add: Yes
# Signaling Code 1, Freq Hopping: Off

# 000030a0: 5062 7546|5062 7546|00ff ffff ff00 1100  PbuFPbuF........
# CH8, RX: 467.56250, TX: 467.56250, Bw: Narrow, Power: Low
# 46 75 62 50 | 46 75 62 50 | 00 ff ff ff ff | 00 | 11 00
# RX          | TX          | ?? ?? ?? ?? ?? |  BW + Power | ?? ??

# 00003190: 0050 2546|0050 7546|00ff ffff ff06 1100  .P%F.PuF........
# CH23, RX: 462.55000, TX: 467.55000
#               0x25+0x50=0x75
# 46 25 50 00 | 46 75 50 00 | 00 ff ff ff ff | 06 | 11 00


class FrequencyTransform(mrc.Transform):
    def import_data(self, buffer, parent=None):
        # corner case: not enough input data
        assert len(buffer) >= 4

        # extract relevant bytes
        input_data = buffer[:4]

        # corner case: undefined frequency
        if set(input_data) == set([0xFF]):
            return mrc.TransformResult(
                payload=bytes([0xFF] * 4),
                end_offset=4)

        # decode individual digits in little endian order
        digits = []
        for byte in reversed(input_data):
            digits.extend([
                (byte & 0xF0) >> 4,
                (byte & 0x0F) >> 0])

        if len(digits) != 8:
            raise RuntimeError("Failed to parse frequency value")

        # convert digits to frequency value
        value = sum([
            v * pow(10, 2 + 3 + 3 - i)
            for i, v in enumerate(digits)])

        # encode frequency as little endian 32-bit unsigned integer (Hz)
        return mrc.TransformResult(
            payload=struct.pack('<L', value),
            end_offset=4)

    def export_data(self, buffer, parent=None):
        # corner case: not enough input data
        assert len(buffer) >= 4

        # retrieve input data
        input_data = buffer[:4]

        # corner case: undefined frequency
        if set(input_data) == set([0xFF]):
            return mrc.TransformResult(
                payload=bytes([0xFF] * 4),
                end_offset=4)

        # decode frequency as little endian 32-bit unsigned integer (Hz)
        value = struct.unpack('<L', input_data)[0]

        # extract digits from numeric value
        digits = []
        counter = value
        while counter > 0:
            digit = int(counter % 10)
            digits.append(digit)
            counter = int(counter // 10)

        digits = digits[-8:]  # value in Hz but we want MHz, discard zeroes

        # pack digits into bytes
        output = bytearray()
        pairwise_iterator = zip(*([iter(digits)] * 2), strict=True)
        for upper_digit, lower_digit in pairwise_iterator:
            output.append(
                ((lower_digit & 0x0F) << 4) + (upper_digit & 0x0F))

        return mrc.TransformResult(payload=bytes(output), end_offset=4)


class Frequency(mrc.Block):
    # actually 4x bytes that store 2x digits each in BCD like format but this
    # is always used with the FrequencyTransform above to convert that value
    # to a more useful double field
    value = mrc.UInt32_LE(offset=0x00)


class Bandwidth(int, enum.Enum):
    NARROW = 0
    WIDE = 1


class Power(int, enum.Enum):
    LOW = 0
    HIGH = 1


class PttId(int, enum.Enum):
    OFF = 0b00
    BOT = 0b01
    EOT = 0b10
    BOTH = 0b11


class BusyLock(int, enum.Enum):
    OFF = 0
    ON = 1


class Signal(int, enum.Enum):
    NONE = 0x0
    ONE = 0x1
    TWO = 0x2
    THREE = 0x3
    FOUR = 0x4
    FIVE = 0x5
    SIX = 0x6
    SEVEN = 0x7
    EIGHT = 0x8
    NINE = 0x9
    TEN = 0xA
    ELEVEN = 0xB
    TWELVE = 0xC
    THIRTEEN = 0xD
    FOURTEEN = 0xE
    FIFTEEN = 0xF


class Scan(int, enum.Enum):
    NO = 0
    YES = 1


class FrequencyEntry(mrc.Block):
    receive_frequency = mrc.BlockField(
        Frequency,
        offset=0x0,
        transform=FrequencyTransform())
        # noqa: XXX: [0xFF] * 4 will be interpreted as max value of unsigned long
        # noqa: fill=bytes([0xFF] * 4))

    transmit_frequency = mrc.BlockField(
        Frequency,
        offset=0x4,
        transform=FrequencyTransform())
        # noqa: XXX: [0xFF] * 4 will be interpreted as max value of unsigned long
        # noqa: fill=bytes([0xFF] * 4))

    # TODO: 0x08 UInt8
    # XXX sometimes 0x00 but mostly 0xFF
    unknown_flag = mrc.Bytes(
        offset=0x8,
        length=1,
        default=bytes([0xFF]))

    # 00003210: 0050 2546 0050 7546 ff|70 06|70 06|06 1000  .P%F.PuF.p.p....
    # CTCSS 67.0                       06 70 06 70

    # 00003220: 0075 2546 0075 7546 ff|35 10|35 10|06 1000  .u%F.uuF.5.5....
    # CTCSS 103.5                      10 35 10 35

    # ctcss_decode = mrc.BlockField(
    #     CtcssCode,
    #     offset=0x9,
    #     transform=DigitString(bytes=2),
    #     fill=bytes([0xFF] * 2))

    # ctcss_encode = mrc.BlockField(
    #     CtcssCode,
    #     offset=0xB,
    #     transform=DigitString(bytes=2),
    #     fill=bytes([0xFF] * 2))

    bandwidth = mrc.Bits(
        offset=0xD,
        bits=0b00000100,
        enum=Bandwidth,
        default=Bandwidth.WIDE)

    power = mrc.Bits(
        offset=0xD,
        bits=0b00000010,
        enum=Power,
        default=Power.HIGH)

    ptt_id = mrc.Bits(
        offset=0xD,
        bits=0b00110000,
        enum=PttId,
        default=PttId.OFF)

    busy_lock = mrc.Bits(
        offset=0xD,
        bits=0b01000000,
        enum=BusyLock,
        default=BusyLock.OFF)

    # XXX: signal is which dtmf code to use?
    signal = mrc.Bits(
        offset=0xE,
        bits=0b11110000,
        enum=Signal,
        default=Signal.ONE)

    scan = mrc.Bits(
        offset=0xE,
        bits=0b00001000,
        enum=Scan,
        default=Scan.NO)

    # XXX: seems to be 0x00 for all cases
    # XXX: maybe frequency hopping code in CPS?
    unused_data = mrc.Bytes(
        offset=0xF,
        length=1,
        default=bytes([0x00]))


class FrequencyMemory(mrc.Block):
    # XXX: [0xFF, 0xFF] stock but often [0xFA, 0x00] after CPS write
    unknown_frequency_data1 = mrc.Bytes(
        offset=0x00,
        length=2,
        default=bytes([0xFA, 0x00]))

    # XXX: 1-based index into (frequency, channel) entries
    channel_a = mrc.UInt8(
        offset=0x02,
        default=1,
        range=range(1, 250))

    unknown_frequency_data2 = mrc.Const(
        mrc.Bytes(offset=0x03, length=1, default=bytes([0x00])),
        bytes([0x00]))

    # XXX: 1-based index into (frequency, channel) entries
    channel_b = mrc.UInt8(
        offset=0x04,
        default=1,
        range=range(1, 250))

    unknown_frequency_data3 = mrc.Const(
        mrc.Bytes(offset=0x05, length=1, default=bytes([0x00])),
        bytes([0x00]))

    # XXX: 0x00 or 0xFF
    unknown_frequency_data4 = mrc.Bytes(
        offset=0x06,
        length=0xA,
        default=bytes([0x00] * 0xA))

    vfo_a = mrc.BlockField(
        FrequencyEntry,
        offset=0x10,
        # XXX: we really should only consider the frequency value bytes here
        # XXX: also this will never be unset
        fill=bytes([
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x06, 0x11, 0x00]))

    vfo_b = mrc.BlockField(
        FrequencyEntry,
        offset=0x20,
        # XXX: we really should only consider the frequency value bytes here
        # XXX: also this will never be unset
        fill=bytes([
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x06, 0x11, 0x00]))

    frequency_entries = mrc.BlockField(
        FrequencyEntry,
        offset=0x30,
        count=249,
        # XXX: we really should only consider the frequency value bytes here
        fill=bytes([
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x06, 0x11, 0x00]))

    # XXX: this is required otherwise memory.size() will return 0x30 because
    # the frequency_entries field above is variable length and I guess by
    # default the block uses the minimum array size when computing the length
    # XXX: content seems to vary based on what was written here before
    trailing_space_frequency = mrc.Bytes(
        offset=0xFC0,
        length=0x20,
        default=bytes([0x00] * 0x20))

    def hexdump(self, *args, **kwargs):
        # only show the non-empty part of the block
        kwargs['length'] = self.get_size() - len(self.trailing_space_frequency)
        super().hexdump(*args, **kwargs)
