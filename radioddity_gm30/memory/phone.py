import enum

from mrcrowbar import models as mrc


class DtmfCode(mrc.Block):
    # XXX: 0x01 - 0x0D bytes for [0-9A-D] digits, 0xFF right padded to length
    value = mrc.Bytes(
        offset=0x0,
        length=5,
        default=bytes([0xFF] * 5))


class PttReleaseSend(int, enum.Enum):
    OFF = 0
    ON = 1


class PttPressSend(int, enum.Enum):
    OFF = 0
    ON = 1


class PhoneMemory(mrc.Block):
    dtmf_codes = mrc.BlockField(
        DtmfCode,
        offset=0x00,
        count=15,
        fill=bytes([0xFF] * 5))

    # XXX: fixed-length ID code same encoding as above
    # XXX: default seems to be [0x01, 0x02, 0x03, 0x04, 0x05]
    id_code = mrc.BlockField(
        DtmfCode,
        offset=0x50,
        # XXX: this field must always be set
        fill=bytes([0xFF] * 5))

    # XXX seems unused
    unknown_magic_phone_56 = mrc.Const(
        mrc.Bytes(offset=0x56, length=9, default=b''),
        bytes([0x00] * 9))

    ptt_release_send = mrc.Bits(
        offset=0x60,
        bits=0b00000010,
        enum=PttReleaseSend,
        default=PttReleaseSend.OFF)

    ptt_press_send = mrc.Bits(
        offset=0x60,
        bits=0b00000001,
        enum=PttPressSend,
        default=PttPressSend.OFF)

    dtmf_delay_time = mrc.UInt8(
        offset=0x61,
        default=0x00,
        range=range(0x00, 0x13))

    @property
    def dtmf_delay_time_seconds(self):
        return 0.1 + (self.dtmf_delay_time * 0.05)

    @dtmf_delay_time_seconds.setter
    def dtmf_delay_time_seconds(self, value):
        self.dtmf_delay_time = ((value - 0.1) / 0.05)

    dtmf_digit_duration = mrc.UInt8(
        offset=0x62,
        default=0x00,
        range=range(0x00, 0xC1))

    @property
    def dtmf_digit_duration_seconds(self):
        return 0.08 + (self.dtmf_digit_duration * 0.01)

    @dtmf_digit_duration_seconds.setter
    def dtmf_digit_duration_seconds(self, value):
        self.dtmf_digit_duration = ((value - 0.08) / 0.01)

    dtmf_interval_duration = mrc.UInt8(
        offset=0x63,
        default=0x00,
        range=range(0x00, 0xC1))

    @property
    def dtmf_interval_duration_seconds(self):
        return 0.08 + (self.dtmf_interval_duration * 0.01)

    @dtmf_interval_duration_seconds.setter
    def dtmf_interval_duration_seconds(self, value):
        self.dtmf_interval_duration = ((value - 0.08) / 0.01)

    # XXX: content seems to vary based on what was written here before
    trailing_space_phone = mrc.Bytes(
        offset=0x70,
        length=0xF50,
        default=bytes([0x00] * 0xF50))

    def hexdump(self, *args, **kwargs):
        # only show the non-empty part of the block
        kwargs['length'] = self.get_size() - len(self.trailing_space_phone)
        super().hexdump(*args, **kwargs)
