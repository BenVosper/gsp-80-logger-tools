"""Sanity tests for tools/rad2csv.py, using real rad.txt/get.txt files captured from loggers."""
import csv, io, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
TOOL = os.path.join(HERE, '..', 'tools', 'rad2csv.py')


def convert(rad, *args):
    r = subprocess.run([sys.executable, '-I', TOOL, rad, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return list(csv.reader(io.StringIO(r.stdout)))


class FullRecording(unittest.TestCase):
    """250 records at 300 s across midnight; rad.txt has 2 junk rows from erased flash."""

    def setUp(self):
        self.rows = convert(os.path.join(DATA, 'run1_rad.txt'), '--get', os.path.join(DATA, 'run1_get.txt'))

    def test_header_and_count(self):
        self.assertEqual(self.rows[0], ['record', 'timestamp', 'temp_C', 'rh_pct'])
        self.assertEqual(len(self.rows) - 1, 250)

    def test_first_and_last_samples_match_pdf(self):
        self.assertEqual(self.rows[1], ['1', '2026-11-07 16:05:24', '18.9', '71.0'])
        self.assertEqual(self.rows[-1], ['250', '2026-11-08 12:50:24', '17.9', '73.8'])

    def test_midnight_rollover(self):
        self.assertEqual(self.rows[100][1], '2026-11-08 00:20:24')  # record 100
        self.assertEqual(self.rows[101][1:], ['2026-11-08 00:25:24', '18.1', '76.3'])  # first 'D' row of day 2

    def test_no_junk_values(self):
        values = {v for row in self.rows[1:] for v in row[2:]}
        self.assertFalse(values & {'-46.9', '655.3'})

    def test_works_without_get_txt(self):
        rows = convert(os.path.join(DATA, 'run1_rad.txt'))  # interval inferred from C rows
        self.assertEqual(rows, self.rows)


class ShortRecording(unittest.TestCase):
    """3 records in Fahrenheit: a single partial row with no time of day."""

    def test_uses_get_start_time_and_unit(self):
        rows = convert(os.path.join(DATA, 'short_f_rad.txt'), '--get', os.path.join(DATA, 'short_f_get.txt'))
        self.assertEqual(rows, [
            ['record', 'timestamp', 'temp_F', 'rh_pct'],
            ['1', '2026-11-08 16:29:38', '75.0', '60.9'],   # get.txt says 16:29:39; PDF/rad are 1 s earlier
            ['2', '2026-11-08 16:30:38', '75.3', '59.9'],
            ['3', '2026-11-08 16:31:38', '75.3', '59.6'],
        ])

    def test_without_get_txt_fails_cleanly(self):
        with self.assertRaises(AssertionError) as cm:
            convert(os.path.join(DATA, 'short_f_rad.txt'), '--interval', '60')
        self.assertIn('--get', str(cm.exception))


class TemperatureOnly(unittest.TestCase):
    """GSP-70 layout (from firmware, no real sample yet): 20 temperatures per row,
    identified by get.txt's 'bm8b' header."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rad = os.path.join(self.tmp.name, 'rad.txt')
        with open(self.rad, 'w') as f:
            f.write('S0001D26-01-01' + ' 20.0' * 20 + '\n')
            f.write('S0002C00:20:00' + ' 21.0' * 4 + '$\r\n')
        self.get = os.path.join(self.tmp.name, 'get.txt')
        with open(os.path.join(DATA, 'run1_get.txt'), 'rb') as f:
            text = f.read().decode().split('\0')[0]
        with open(self.get, 'w') as f:  # same file, but temp-only model, 24 records, 60 s
            f.write(text.replace('bm8a', 'bm8b').replace('log00250', 'log00024').replace('L 30', 'L  6'))

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, rows):
        self.assertEqual(rows[0], ['record', 'timestamp', 'temp_C'])
        self.assertEqual(len(rows) - 1, 24)
        self.assertEqual(rows[1], ['1', '2026-01-01 00:00:00', '20.0'])
        self.assertEqual(rows[20], ['20', '2026-01-01 00:19:00', '20.0'])
        self.assertEqual(rows[21], ['21', '2026-01-01 00:20:00', '21.0'])

    def test_detected_from_get_txt(self):
        self.check(convert(self.rad, '--get', self.get))

    def test_explicit_channels(self):
        self.check(convert(self.rad, '--channels', '1', '--interval', '60'))


class StartTimeParsing(unittest.TestCase):
    def test_start_time_found_with_button_stop_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            get = os.path.join(tmp, 'get.txt')
            with open(os.path.join(DATA, 'short_f_get.txt'), 'rb') as f:
                text = f.read().decode().split('\0')[0]
            with open(get, 'w') as f:
                f.write(text.replace('K0Uf', 'K1Uf'))
            rows = convert(os.path.join(DATA, 'short_f_rad.txt'), '--get', get)
        self.assertEqual(rows[1][1], '2026-11-08 16:29:38')


if __name__ == '__main__':
    unittest.main()
