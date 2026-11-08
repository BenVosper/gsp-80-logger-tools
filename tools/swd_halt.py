"""Halt the FM33LC046U at its reset vector before firmware disables SWD.

The GSP-80 firmware repurposes the SWD pins a few ms after boot, so we:
hold NRST low -> bring up the DP -> set C_DEBUGEN|C_HALT + VC_CORERESET -> release NRST.
"""
import time
from pyocd.core.helpers import ConnectHelper
from pyocd.probe.debug_probe import DebugProbe

DHCSR, DEMCR = 0xE000EDF0, 0xE000EDFC

class RawSWD:
    def __init__(self, freq=1_000_000):
        self.s = ConnectHelper.session_with_chosen_probe(target_override='cortex_m', frequency=freq, connect_mode='attach')
        self.s.open(init_board=False)
        self.p = self.s.probe
        self.p.connect(DebugProbe.Protocol.SWD)
        self.p.set_clock(freq)

    def line_reset(self):
        p = self.p
        p.swj_sequence(51, 0xffffffffffffff); p.swj_sequence(16, 0xe79e)
        p.swj_sequence(51, 0xffffffffffffff); p.swj_sequence(8, 0)
        return p.read_dp(0)

    def power_up(self):
        p = self.p
        p.write_dp(0x0, 0x1E)          # ABORT: clear sticky errors
        p.write_dp(0x8, 0)             # SELECT AP0 bank0
        p.write_dp(0x4, 0x50000000)    # CSYSPWRUPREQ | CDBGPWRUPREQ
        for _ in range(100):
            if (p.read_dp(0x4) & 0xA0000000) == 0xA0000000:
                break
        p.write_ap(0x00, 0x23000002)   # CSW: 32-bit, no auto-increment

    def rd(self, addr):
        self.p.write_ap(0x04, addr)
        return self.p.read_ap(0x0C)

    def wr(self, addr, val):
        self.p.write_ap(0x04, addr)
        self.p.write_ap(0x0C, val)

    def halt_at_reset(self):
        p = self.p
        p.assert_reset(True); time.sleep(0.05)
        idc = self.line_reset()
        self.power_up()
        self.wr(DHCSR, 0xA05F0003)     # DBGKEY | C_HALT | C_DEBUGEN
        self.wr(DEMCR, 0x00000001)     # VC_CORERESET
        p.assert_reset(False)
        time.sleep(0.05)
        try:
            dh = self.rd(DHCSR)
        except Exception:
            self.line_reset(); self.power_up(); dh = self.rd(DHCSR)
        return idc, dh

    def close(self):
        self.s.close()

if __name__ == '__main__':
    r = RawSWD()
    idc, dh = r.halt_at_reset()
    print(f'IDCODE 0x{idc:08x}  DHCSR 0x{dh:08x}  halted={bool(dh & (1<<17))}')
    print('AP0 IDR 0x%08x' % r.p.read_ap(0xFC))
    print('CPUID  0x%08x' % r.rd(0xE000ED00))
    print('vector table: SP 0x%08x  Reset 0x%08x' % (r.rd(0x0), r.rd(0x4)))
    r.close()
