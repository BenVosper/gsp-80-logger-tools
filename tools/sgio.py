"""Minimal SG_IO wrapper for sending raw SCSI CDBs on Linux."""
import ctypes, fcntl, os, struct

SG_IO = 0x2285
SG_DXFER_NONE, SG_DXFER_TO_DEV, SG_DXFER_FROM_DEV = -1, -2, -3

class sg_io_hdr(ctypes.Structure):
    _fields_ = [("interface_id", ctypes.c_int), ("dxfer_direction", ctypes.c_int),
                ("cmd_len", ctypes.c_ubyte), ("mx_sb_len", ctypes.c_ubyte),
                ("iovec_count", ctypes.c_ushort), ("dxfer_len", ctypes.c_uint),
                ("dxferp", ctypes.c_void_p), ("cmdp", ctypes.c_void_p), ("sbp", ctypes.c_void_p),
                ("timeout", ctypes.c_uint), ("flags", ctypes.c_uint), ("pack_id", ctypes.c_int),
                ("usr_ptr", ctypes.c_void_p), ("status", ctypes.c_ubyte), ("masked_status", ctypes.c_ubyte),
                ("msg_status", ctypes.c_ubyte), ("sb_len_wr", ctypes.c_ubyte), ("host_status", ctypes.c_ushort),
                ("driver_status", ctypes.c_ushort), ("resid", ctypes.c_int), ("duration", ctypes.c_uint),
                ("info", ctypes.c_uint)]

class Dev:
    def __init__(self, path="/dev/sdc"):
        self.fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)

    def cmd(self, cdb, inlen=0, data_out=None, timeout=5000):
        cdb = bytes(cdb)
        cdbbuf = ctypes.create_string_buffer(cdb, len(cdb))
        sense = ctypes.create_string_buffer(32)
        h = sg_io_hdr(interface_id=ord('S'), cmd_len=len(cdb), mx_sb_len=32,
                      cmdp=ctypes.cast(cdbbuf, ctypes.c_void_p), sbp=ctypes.cast(sense, ctypes.c_void_p),
                      timeout=timeout)
        if data_out is not None:
            buf = ctypes.create_string_buffer(bytes(data_out), len(data_out))
            h.dxfer_direction, h.dxfer_len = SG_DXFER_TO_DEV, len(data_out)
        elif inlen:
            buf = ctypes.create_string_buffer(inlen)
            h.dxfer_direction, h.dxfer_len = SG_DXFER_FROM_DEV, inlen
        else:
            buf = None
            h.dxfer_direction = SG_DXFER_NONE
        if buf is not None:
            h.dxferp = ctypes.cast(buf, ctypes.c_void_p)
        fcntl.ioctl(self.fd, SG_IO, h)
        data = buf.raw[:h.dxfer_len - h.resid] if (buf is not None and data_out is None) else b""
        return dict(status=h.status, host=h.host_status, driver=h.driver_status,
                    sense=sense.raw[:h.sb_len_wr], data=data, resid=h.resid)

def read10(dev, lba, n=1):
    return dev.cmd([0x28, 0] + list(struct.pack(">I", lba)) + [0] + list(struct.pack(">H", n)) + [0], inlen=512 * n)
