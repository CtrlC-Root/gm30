from mrcrowbar import models as mrc


class UnknownMemory(mrc.Block):
    # XXX educated guess this is calibration data of some sort because when
    # overwriting with garbage the radio becomes erratic and unresponsive
    # showing impossible frequencies on the VFOs and battery levels
    unknown_data_unkown = mrc.Bytes(
        offset=0x00,
        length=0x201,
        default=bytes([0x00] * 0xFC0))

    # XXX: content seems to vary based on what was written here before
    trailing_space_unknown = mrc.Bytes(
        offset=0x202,
        length=0xDBE,
        default=bytes([0x00] * 0xDBE))

    def hexdump(self, *args, **kwargs):
        # only show the non-empty part of the block
        kwargs['length'] = self.get_size() - len(self.trailing_space_unknown)
        super().hexdump(*args, **kwargs)
