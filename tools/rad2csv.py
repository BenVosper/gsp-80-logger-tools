#!/usr/bin/env python3
"""Convert a GSP-70/80 logger's rad.txt (raw records) into a linear CSV.

rad.txt layout (one line per flash block of 20 values):
    S<row:4>D<YY-MM-DD><values>    first row, or first row of a new day
    S<row:4>C<HH:MM:SS><values>    time of the row's first sample
    values = fixed-width 5-char fields
             GSP-80 (get.txt 'bm8a'): temp, RH, temp, RH, ...  -> 10 samples per row
             GSP-70 (get.txt 'bm8b'): temp, temp, temp, ...    -> 20 samples per row
    file ends with '$\\r\\n'

Firmware bug: rows past the end of the recording are filled from erased flash
(-46.9 / 655.3), so the true record count is taken from get.txt ('log%05d').

Timestamps: the time of a 'D' row is not given, so each row's start time is
derived from the next/previous 'C' row +/- (samples per row) * interval; every 'C' row is used
as an anchor and checked for consistency.
"""
import argparse, csv, datetime, re, sys

ERASED = {'-46.9', '655.3'}


def parse_get(path):
    with open(path, 'rb') as f:
        t = f.read().decode('ascii', 'replace').split('\0')[0]
    info = {}
    # header model letter is set by sensor auto-detection: a = temp+RH probe, b = temp-only probe
    info['channels'] = {'bm8a': 2, 'bm8b': 1}.get(t[:4])
    m = re.search(r'log(\d{5})', t);  info['count'] = int(m.group(1)) if m else None
    m = re.search(r',L\s*(\d+)', t);  info['interval'] = int(m.group(1)) * 10 if m else None
    m = re.search(r'K.U(.),S', t);       info['unit'] = {'c': 'C', 'f': 'F'}.get(m.group(1), m.group(1)) if m else 'C'
    m = re.search(r'K.U.,S\d{5},(\d{6}),(\d{6})', t)
    if m and m.group(1) != '000000':
        info['start'] = datetime.datetime.strptime(m.group(1) + m.group(2), '%y%m%d%H%M%S')
    m = re.search(r',N([^{]*)\{(.*?)\}', t)
    if m: info['serial'], info['mark'] = m.group(1), m.group(2)
    return info


def parse_rad(path):
    rows = []
    with open(path, 'rb') as f:
        text = f.read().decode('ascii', 'replace')
    for line in text.splitlines():
        line = line.rstrip('$\r\n ')
        m = re.match(r'S(\d{4})([DC])(.{8})(.*)', line)
        if not m:
            continue
        kind, stamp, body = m.group(2), m.group(3), m.group(4)
        try:   # rows read from erased flash have impossible dates/times: stop there
            datetime.datetime.strptime(stamp, '%y-%m-%d' if kind == 'D' else '%H:%M:%S')
        except ValueError:
            break
        vals = [body[i:i + 5].strip() for i in range(0, len(body), 5)]
        rows.append(dict(row=int(m.group(1)), kind=kind, stamp=stamp, vals=vals))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rad_txt')
    ap.add_argument('--get', help='get.txt from the same download (record count, interval, unit)')
    ap.add_argument('--interval', type=int, help='record interval in seconds (overrides get.txt)')
    ap.add_argument('--channels', type=int, choices=(1, 2), help='1 = temp only (GSP-70), 2 = temp+RH (default: from get.txt, else 2)')
    ap.add_argument('-o', '--output', default='-')
    a = ap.parse_args()

    info = parse_get(a.get) if a.get else {}
    rows = parse_rad(a.rad_txt)
    interval = a.interval or info.get('interval')
    count = info.get('count')
    if not rows:
        sys.exit('no rows found')

    # Every row holds 20 values, so the layout can't be told from rad.txt alone:
    # get.txt's header says which sensor type was detected.
    nch = a.channels or info.get('channels')
    if not nch:
        nch = 2
        if any(len(r['vals']) % 2 for r in rows):
            nch = 1
        elif not a.get:
            print('note: assuming temp+RH (GSP-80); pass --get or --channels 1 for temp-only', file=sys.stderr)
    per_row = 20 // nch

    # Interval from consecutive C rows if not known.
    c_rows = [r for r in rows if r['kind'] == 'C' and r['stamp'][2] == ':']
    if not interval:
        for r1, r2 in zip(c_rows, c_rows[1:]):
            if r2['row'] == r1['row'] + 1:
                t1 = datetime.datetime.strptime(r1['stamp'], '%H:%M:%S')
                t2 = datetime.datetime.strptime(r2['stamp'], '%H:%M:%S')
                interval = int((t2 - t1).total_seconds()) % 86400 // per_row
                break
    if not interval:
        sys.exit('cannot determine interval; pass --interval or --get')
    row_span = datetime.timedelta(seconds=per_row * interval)

    # Walk rows, tracking the date from D rows and times from C rows.
    # Row start time t[row]: from C rows directly; D rows inferred from neighbours.
    times = {}
    date = None
    for r in rows:
        if r['kind'] == 'D':
            try:
                date = datetime.datetime.strptime(r['stamp'], '%y-%m-%d').date()
            except ValueError:
                break           # erased-flash garbage row
        else:
            try:
                tod = datetime.datetime.strptime(r['stamp'], '%H:%M:%S').time()
            except ValueError:
                break
            if date is None:
                sys.exit('C row before any D row')
            t = datetime.datetime.combine(date, tod)
            prev = times.get(r['row'] - 1)
            if prev and t < prev:          # crossed midnight without a D row (shouldn't happen)
                t += datetime.timedelta(days=1)
            times[r['row']] = t
    # Fill D rows from neighbours.
    for r in rows:
        n = r['row']
        if n in times or r['kind'] != 'D':
            continue
        if n + 1 in times:
            times[n] = times[n + 1] - row_span
        elif n - 1 in times:
            times[n] = times[n - 1] + row_span
        elif info.get('start'):
            # get.txt's start time is consistently 1 s later than rad.txt/PDF timestamps
            times[n] = info['start'] - datetime.timedelta(seconds=1)
    if not times:
        sys.exit('no row has a time of day (recording shorter than 2 rows?); pass --get get.txt for the start time')
    # Consistency check on anchors.
    first = min(times)
    t0 = times[first] - (first - 1) * row_span
    drift = [(n, (t - (t0 + (n - 1) * row_span)).total_seconds()) for n, t in times.items()]
    bad = [d for d in drift if abs(d[1]) > 2]
    if bad:
        print(f'warning: row times deviate from a fixed interval: {bad[:5]}', file=sys.stderr)

    out = sys.stdout if a.output == '-' else open(a.output, 'w', newline='')
    w = csv.writer(out)
    unit = info.get('unit', 'C')
    w.writerow(['record', 'timestamp', f'temp_{unit}'] + (['rh_pct'] if nch == 2 else []))
    rec = 0
    for r in rows:
        if r['row'] not in times:
            continue
        vals = r['vals']
        for k in range(0, len(vals) - nch + 1, nch):
            if count is not None and rec >= count:
                break
            sample = vals[k:k + nch]
            if any(v in ERASED or not v for v in sample):
                continue
            ts = times[r['row']] + datetime.timedelta(seconds=interval * (k // nch))
            rec += 1
            w.writerow([rec, ts.isoformat(sep=' ')] + sample)
    if out is not sys.stdout:
        out.close()
    print(f'{rec} records, interval {interval}s, {t0:%Y-%m-%d %H:%M:%S} onwards'
          + (f' (get.txt says {count})' if count is not None else ''), file=sys.stderr)


if __name__ == '__main__':
    main()
