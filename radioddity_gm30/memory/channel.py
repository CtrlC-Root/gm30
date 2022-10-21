from mrcrowbar import models as mrc


class ChannelEntry(mrc.Block):
    name = mrc.CStringN(
        offset=0x00,
        element_length=6,
        encoding='ascii',
        default='')

    # 0x00 for built-in, 0xFF for custom?
    unknown = mrc.Bytes(
        offset=0x06,
        length=5,
        default=bytes([0x00] * 5))


class ChannelMemory(mrc.Block):
    # XXX: seems to break hexdump() when in initial state
    channel_entries = mrc.BlockField(
        ChannelEntry,
        offset=0x00,
        count=250,
        fill=bytes([0xFF]))

    # XXX: 0x0ABE -> 10x UInt8 CString ("GMRS1")
    # XXX: this may be count=2 but second entry is empty in my memory dump
    special_channel = mrc.BlockField(
        ChannelEntry,
        offset=0xABE,
        count=2,
        fill=bytes([0xFF]))

    # XXX: content seems to vary based on what was written here before
    trailing_space_channel = mrc.Bytes(
        offset=0xAD3,
        length=0x4ED,
        default=bytes([0x00] * 0x4ED))

    def hexdump(self, *args, **kwargs):
        # only show the non-empty part of the block
        kwargs['length'] = self.get_size() - len(self.trailing_space_channel)
        super().hexdump(*args, **kwargs)
