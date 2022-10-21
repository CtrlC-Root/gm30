import enum

from mrcrowbar import models as mrc


class BootscreenMode(int, enum.Enum):
    LOGO = 0
    MESSAGE = 1
    VOLTAGE = 2


class BatterySaver(int, enum.Enum):
    OFF = 0
    ONE_TO_ONE = 1
    ONE_TO_TWO = 2
    ONE_TO_THREE = 3
    ONE_TO_FOUR = 4


class WorkMode(int, enum.Enum):
    FREQUENCY = 0
    CHANNEL = 1


class VoiceAlert(int, enum.Enum):
    OFF = 0
    ON = 1


class BeepTone(int, enum.Enum):
    OFF = 0
    ON = 1


class AutoKeyLock(int, enum.Enum):
    OFF = 0
    ON = 1


class CtcssTailRevert(int, enum.Enum):
    OFF = 0
    ON = 1


class ScanType(int, enum.Enum):
    TIME = 0b00
    CARRIER = 0b01
    SEARCH = 0b10


class DtmfSideTone(int, enum.Enum):
    OFF = 0b00
    DT_ONLY = 0b01
    ANI_ONLY = 0b10
    DT_ANI_BOTH = 0b11


class DualStandby(int, enum.Enum):
    OFF = 0
    ON = 1


class RogerBeep(int, enum.Enum):
    OFF = 0
    ON = 1


class AlarmMode(int, enum.Enum):
    ON_SITE = 0b00
    SEND_SOUND = 0b01
    SEND_CODE = 0b10


class AlarmSound(int, enum.Enum):
    OFF = 0
    ON = 1


class FmRadio(int, enum.Enum):
    DISABLED = 0
    ENABLED = 1


class ToneBurst(int, enum.Enum):
    FREQ_1000_HZ = 0
    FREQ_1450_HZ = 1
    FREQ_1750_HZ = 2
    FREQ_2100_HZ = 3


class ChannelDisplay(int, enum.Enum):
    NAME_NUMBER = 0
    FREQUENCY_NUMBER = 1


class GeneralMemory(mrc.Block):
    bootscreen_mode = mrc.UInt8(
        offset=0x00,
        default=BootscreenMode.LOGO,
        enum=BootscreenMode)

    bootscreen_line1 = mrc.CStringN(
        offset=0x10,
        default='WELCOME',
        element_length=10,
        encoding='ascii')

    bootscreen_line2 = mrc.CStringN(
        offset=0x20,
        default='Radioddity',
        element_length=10,
        encoding='ascii')

    # XXX what is this data?
    unknown_magic_general_30 = mrc.Const(
        mrc.Bytes(offset=0x30, length=16, default=b''),
        bytes([
            0x00, 0x00, 0x00, 0x40,
            0x00, 0x00, 0x00, 0x52,
            0x00, 0x00, 0x60, 0x13,
            0x00, 0x00, 0x40, 0x17]))

    transmit_timeout = mrc.UInt8(
        offset=0x40,
        default=0x07,
        range=range(0x00, 0x29))

    @property
    def transmit_timeout_seconds(self):
        return self.transmit_timeout * 15

    @transmit_timeout_seconds.setter
    def transmit_timeout_seconds(self, value):
        self.transmit_timeout = value / 15

    squelch_level = mrc.UInt8(
        offset=0x41,
        default=0x03,
        range=range(0x00, 0x0A))

    vox_level = mrc.UInt8(
        offset=0x42,
        default=0x00,
        range=range(0x00, 0x0A))

    battery_saver = mrc.Bits(
        offset=0x43,
        bits=0b11110000,
        default=BatterySaver.ONE_TO_TWO,
        enum=BatterySaver)

    unknown_flag_general_43 = mrc.Const(
        mrc.Bits(offset=0x43, bits=0b00000010, default=0x1),
        0x1)

    work_mode = mrc.Bits(
        offset=0x43,
        bits=0b00000100,
        default=WorkMode.CHANNEL,
        enum=WorkMode)

    voice_alert = mrc.Bits(
        offset=0x43,
        bits=0b00000001,
        default=VoiceAlert.ON,
        enum=VoiceAlert)

    backlight_timeout_seconds = mrc.UInt8(
        offset=0x44,
        default=0x05,
        range=range(0x00, 0x0B))

    beep_tone = mrc.Bits(
        offset=0x45,
        bits=0b10000000,
        default=BeepTone.ON,
        enum=BeepTone)

    auto_key_lock = mrc.Bits(
        offset=0x45,
        bits=0b01000000,
        default=AutoKeyLock.OFF,
        enum=AutoKeyLock)

    ctcss_tail_revert = mrc.Bits(
        offset=0x45,
        bits=0b00010000,
        default=CtcssTailRevert.ON,
        enum=CtcssTailRevert)

    scan_type = mrc.Bits(
        offset=0x45,
        bits=0b00001100,
        default=ScanType.CARRIER,
        enum=ScanType)

    dtmf_side_tone = mrc.Bits(
        offset=0x45,
        bits=0b00000011,
        default=DtmfSideTone.OFF,
        enum=DtmfSideTone)

    dual_standby = mrc.Bits(
        offset=0x46,
        bits=0b01000000,
        default=DualStandby.OFF,
        enum=DualStandby)

    roger_beep = mrc.Bits(
        offset=0x46,
        bits=0b00100000,
        default=RogerBeep.ON,
        enum=RogerBeep)

    alarm_mode = mrc.Bits(
        offset=0x46,
        bits=0b00011000,
        default=AlarmMode.ON_SITE,
        enum=AlarmMode)

    alarm_sound = mrc.Bits(
        offset=0x46,
        bits=0b00000100,
        default=AlarmSound.ON,
        enum=AlarmSound)

    fm_radio = mrc.Bits(
        offset=0x46,
        bits=0b00000010,
        default=FmRadio.ENABLED,
        enum=FmRadio)

    repeat_tail_revert = mrc.UInt8(
        offset=0x47,
        default=0x02,
        range=range(0x00, 0x0B))

    @property
    def repeat_tail_revert_seconds(self):
        return self.repeat_tail_revert * 0.100

    @repeat_tail_revert_seconds.setter
    def repeat_tail_revert_seconds(self, value):
        self.repeat_tail_revert = value / 0.100

    repeat_tail_delay = mrc.UInt8(
        offset=0x48,
        default=0x02,
        range=range(0x00, 0x0B))

    @property
    def repeat_tail_delay_seconds(self):
        return self.repeat_tail_delay * 0.100

    @repeat_tail_delay_seconds.setter
    def repeat_tail_delay_seconds(self, value):
        self.repeat_tail_delay = value / 0.100

    tone_burst = mrc.UInt8(
        offset=0x49,
        default=ToneBurst.FREQ_1750_HZ,
        enum=ToneBurst)

    channel_display_a = mrc.Bits(
        offset=0x50,
        bits=0b00000001,
        default=ChannelDisplay.NAME_NUMBER,
        enum=ChannelDisplay)

    channel_display_b = mrc.Bits(
        offset=0x50,
        bits=0b00000010,
        default=ChannelDisplay.NAME_NUMBER,
        enum=ChannelDisplay)

    # XXX what is this data?
    unknown_magic_general_60 = mrc.Const(
        mrc.Bytes(offset=0x60, length=32, default=b''),
        bytes([
            0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00]))

    # XXX is this empty space used for anything?
    unknown_magic_general_80 = mrc.Const(
        mrc.Bytes(offset=0x80, length=0x285, default=bytes([0x00] * 0x285)),
        bytes([0x00] * 0x285))

    # XXX what is this data?
    # Default -> 0x00, Custom1 -> 0x07
    unknown_value_general1 = mrc.Bytes(
        offset=0x305,
        length=1,
        default=bytes([0x00]))

    # XXX what is this data?
    # Default -> 0x00, Custom1 -> 0x01
    unknown_value_general2 = mrc.Bytes(
        offset=0x306,
        length=1,
        default=bytes([0x00]))

    # XXX: content seems to vary based on what was written here before
    trailing_space_general = mrc.Bytes(
        offset=0x307,
        length=0xCB9,
        default=bytes([0x00] * 0xCB9))

    def hexdump(self, *args, **kwargs):
        # only show the non-empty part of the block
        kwargs['length'] = self.get_size() - len(self.trailing_space_general)
        super().hexdump(*args, **kwargs)
