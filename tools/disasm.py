"""Quick Thumb disassembly helpers for the GSP-80 firmware dump."""
import struct, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
FW = open(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('0x') else 'firmware/gsp80_fm33lc046_flash_orig.bin', 'rb').read()
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB); md.detail = True

def u32(a): return struct.unpack_from('<I', FW, a)[0]

def dis(start, end):
    out = []
    a = start
    while a < end:
        insns = list(md.disasm(FW[a:end], a, 1))
        if not insns:
            out.append((a, 2, '.hword', '0x%04x' % struct.unpack_from('<H', FW, a)[0])); a += 2; continue
        i = insns[0]
        extra = ''
        if i.mnemonic.startswith('ldr') and '[pc' in i.op_str:
            tgt = ((a + 4) & ~3) + i.operands[1].mem.disp
            if 0 <= tgt < len(FW) - 3:
                v = u32(tgt); extra = f' ; =0x{v:08x}'
                if v < len(FW):
                    s = FW[v:v+24].split(b'\0')[0]
                    if s and all(32 <= c < 127 for c in s): extra += f' "{s.decode()}"'
        if i.mnemonic == 'adr' or (i.mnemonic.startswith('add') and 'pc' in i.op_str and len(i.operands)==3):
            tgt = ((a + 4) & ~3) + i.operands[-1].imm
            s = FW[tgt:tgt+24].split(b'\0')[0]
            extra = f' ; ->0x{tgt:x} "{s.decode(errors="replace")}"'
        out.append((a, i.size, i.mnemonic, i.op_str + extra)); a += i.size
    return out

def find_adr_refs(target, lo=0, hi=0x3e000):
    refs = []
    for a in range(lo, hi, 2):
        for i in md.disasm(FW[a:a+4], a, 1):
            if i.mnemonic == 'adr' or (i.mnemonic.startswith('add') and i.op_str.count('pc') and len(i.operands)==3 and i.operands[1].reg and 'pc' in i.op_str):
                try:
                    tgt = ((a + 4) & ~3) + i.operands[-1].imm
                except Exception: continue
                if tgt == target: refs.append(a)
            if i.mnemonic.startswith('ldr') and '[pc' in i.op_str:
                tgt = ((a + 4) & ~3) + i.operands[1].mem.disp
                if 0 <= tgt < len(FW)-3 and u32(tgt) == target: refs.append(a)
    return refs

if __name__ == '__main__':
    s, e = int(sys.argv[-2], 16), int(sys.argv[-1], 16)
    for a, sz, m, o in dis(s, e): print(f'{a:06x}: {m:8s} {o}')
