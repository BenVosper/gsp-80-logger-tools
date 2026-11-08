#!/usr/bin/env python3
"""Configure AIKESI / CHNADKS GSP-70 / GSP-80 loggers from Linux (no Windows/Excel needed).

Reads the logger's get.txt, applies the requested changes, and writes cn1.txt +
cn2.txt to the drive. Eject and unplug the logger: the firmware applies the files
on USB disconnect (and deletes them). It also sets the logger's clock to now.

See docs/INTERNALS.md for the file formats (reverse engineered from firmware).
"""
import argparse, datetime, os, re, sys

SETTINGS_RE = re.compile(
    r'L(?P<L>.{3}),W(?P<th>.{3})(?P<tl>.{3}),(?P<hh>.{2})(?P<hl>.{2}),'
    r'K(?P<K>.)U(?P<U>.),S(?P<S>\d{5}),(?P<tdate>\d{6}),(?P<ttime>\d{6}),'
    r'P(?P<P>.)A(?P<A>.),N(?P<N>[^{]*)\{(?P<mark>.*)\}')

# The track mark is the last field, so strchr()-located keys always hit the real
# fields first; only the braces delimiting the mark are a problem.
KEY_CHARS = set('{}')
CN2_MAX = 44   # firmware truncates cn2.txt at >= 45 chars (handler 0x9b8e)


def read_settings(get_txt):
    with open(get_txt, 'rb') as f:
        text = f.read().decode('ascii', 'replace').split('\0')[0].rstrip()
    i = text.find(',L')
    m = SETTINGS_RE.match(text[i + 1:]) if i >= 0 else None
    if not m:
        sys.exit(f'could not parse settings from {get_txt}: {text!r}')
    return text[:i], m.groupdict()


def describe(c):
    yn = lambda b: 'enabled' if b else 'disabled'
    return '\n'.join([
        f"  interval     : {int(c['L']) * 10} s",
        f"  start delay  : {int(c['S'])} s",
        f"  temp alarm   : {int(c['tl'])} .. {int(c['th'])} (unit {'F' if c['U'] == 'f' else 'C'})",
        f"  RH alarm     : {int(c['hl'])} .. {int(c['hh'])} %",
        f"  button stop  : {yn(c['K'] == '0')}",
        f"  button tone  : {yn(c['P'] == '1')}",
        f"  alarm tone   : {yn(c['A'] == '1')}",
        f"  serial       : {c['N']}   (PDF language: {'English' if c['N'][:1].islower() else 'Chinese'})",
        f"  track mark   : {c['mark']}",
        f"  last start   : {c['tdate']} {c['ttime']}",
    ])


def build(c, clock):
    cn1 = (f"L{int(c['L']):3d},W{int(c['th']):03d}{int(c['tl']):03d},{int(c['hh']):02d}{int(c['hl']):02d},"
           f"K{c['K']}U{c['U']},S{int(c['S']):05d},000000,000000")
    if clock:
        cn1 = f"D{clock:%y%m%d},{clock:%H%M%S}," + cn1
    cn2 = f"000P{c['P']}A{c['A']}N{c['N']}{{{c['mark']}}}"
    if len(cn1) > 64:
        sys.exit(f'cn1.txt too long ({len(cn1)} > 64): {cn1!r}')
    if len(cn2) > CN2_MAX:
        sys.exit(f'track mark too long: max {CN2_MAX - len(cn2) + len(c["mark"])} chars for this serial')
    return cn1, cn2


def onoff(s):
    s = s.lower()
    if s in ('on', 'yes', 'y', '1', 'true', 'enable', 'enabled'): return True
    if s in ('off', 'no', 'n', '0', 'false', 'disable', 'disabled'): return False
    raise argparse.ArgumentTypeError('expected on/off')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('drive', help='mount point of the logger (reads get.txt, writes cn1/cn2.txt there)')
    ap.add_argument('--get', help='read get.txt from here instead of <drive>/get.txt')
    g = ap.add_argument_group('settings (anything not given is kept)')
    g.add_argument('--interval', type=int, metavar='SEC', help='record interval, 10..9990 s in steps of 10')
    g.add_argument('--delay', type=int, metavar='SEC', help='start delay after pressing start, 0..99999 s')
    g.add_argument('--temp-high', type=int, metavar='DEG'); g.add_argument('--temp-low', type=int, metavar='DEG')
    g.add_argument('--rh-high', type=int, metavar='PCT'); g.add_argument('--rh-low', type=int, metavar='PCT')
    g.add_argument('--unit', choices=('C', 'F', 'c', 'f'), help='temperature unit')
    g.add_argument('--button-stop', type=onoff, metavar='on|off', help='allow stopping with the < button')
    g.add_argument('--button-tone', type=onoff, metavar='on|off', help='beep on key press')
    g.add_argument('--alarm-tone', type=onoff, metavar='on|off', help='beep on alarm')
    g.add_argument('--mark', help='track mark text shown in the PDF (max ~26 chars, no braces)')
    ap.add_argument('--no-clock', action='store_true', help="don't set the logger's clock")
    ap.add_argument('--show', action='store_true', help='just print the current settings')
    ap.add_argument('-n', '--dry-run', action='store_true', help="print the files but don't write them")
    a = ap.parse_args()

    _, c = read_settings(a.get or os.path.join(a.drive, 'get.txt'))
    print('current settings:\n' + describe(c))
    if a.show:
        return

    if a.interval is not None:
        if a.interval % 10 or not 10 <= a.interval <= 9990:
            sys.exit('interval must be 10..9990 s and a multiple of 10')
        c['L'] = str(a.interval // 10)
    if a.delay is not None:
        if not 0 <= a.delay <= 99999: sys.exit('delay must be 0..99999 s')
        c['S'] = str(a.delay)
    for key, val, lo, hi in (('th', a.temp_high, -99, 999), ('tl', a.temp_low, -99, 999),
                             ('hh', a.rh_high, 0, 99), ('hl', a.rh_low, 0, 99)):
        if val is not None:
            if not lo <= val <= hi: sys.exit(f'{key} value {val} out of range {lo}..{hi}')
            c[key] = str(val)
    if a.unit:
        if a.unit.lower() != c['U'] and a.temp_high is None and a.temp_low is None:
            print('warning: changing unit does NOT convert the temperature alarm limits; '
                  'pass --temp-high/--temp-low in the new unit', file=sys.stderr)
        c['U'] = a.unit.lower()
    if a.button_stop is not None: c['K'] = '0' if a.button_stop else '1'
    if a.button_tone is not None: c['P'] = '1' if a.button_tone else '0'
    if a.alarm_tone is not None: c['A'] = '1' if a.alarm_tone else '0'
    if a.mark is not None:
        bad = KEY_CHARS & set(a.mark)
        if bad or not all(32 <= ord(ch) < 127 for ch in a.mark):
            sys.exit('mark must be printable ASCII without { }')
        c['mark'] = a.mark

    cn1, cn2 = build(c, None if a.no_clock else datetime.datetime.now())
    print('\nnew settings:\n' + describe(c))
    print(f'\ncn1.txt: {cn1}\ncn2.txt: {cn2}')
    if a.dry_run:
        return
    for name, body in (('cn1.txt', cn1), ('cn2.txt', cn2)):
        with open(os.path.join(a.drive, name), 'w') as f:
            f.write(body)
    os.sync()
    print(f'\nwritten to {a.drive}. Now eject and unplug the logger to apply.')


if __name__ == '__main__':
    main()
