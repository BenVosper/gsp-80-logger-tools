"""Sanity tests for tools/gsp80cfg.py, using real get.txt files captured from loggers."""
import datetime, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
TOOL = os.path.join(HERE, '..', 'tools', 'gsp80cfg.py')
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import gsp80cfg  # noqa: E402


def firmware_settings(cn1, cn2):
    """What the firmware stores: cn1 from the first 'L', then cn2[3:7] and cn2[7:]."""
    return cn1[cn1.index('L'):] + ',' + cn2[3:7] + ',' + cn2[7:]


def run(*args):
    return subprocess.run([sys.executable, '-I', TOOL, *args], capture_output=True, text=True)


class ReadSettings(unittest.TestCase):
    def test_parses_real_get_txt(self):
        _, c = gsp80cfg.read_settings(os.path.join(DATA, 'run1_get.txt'))
        self.assertEqual(int(c['L']) * 10, 300)
        self.assertEqual((int(c['th']), int(c['tl'])), (40, -10))
        self.assertEqual((int(c['hh']), int(c['hl'])), (95, 35))
        self.assertEqual(int(c['S']), 600)
        self.assertEqual((c['K'], c['U'], c['P'], c['A']), ('0', 'c', '1', '1'))
        self.assertEqual(c['N'], 'e03000929')
        self.assertEqual(c['mark'], 'null')

    def test_parses_fahrenheit_and_custom_mark(self):
        _, c = gsp80cfg.read_settings(os.path.join(DATA, 'short_f_get.txt'))
        self.assertEqual((c['U'], c['P'], c['mark']), ('f', '0', 'decode test 1'))


class Build(unittest.TestCase):
    def setUp(self):
        self.header, self.c = gsp80cfg.read_settings(os.path.join(DATA, 'run1_get.txt'))

    def test_round_trip_matches_firmware_storage(self):
        # Unchanged settings must reproduce get.txt's settings string, except the
        # last-start time which we deliberately send as zeros.
        cn1, cn2 = gsp80cfg.build(self.c, None)
        with open(os.path.join(DATA, 'run1_get.txt'), 'rb') as f:
            text = f.read().decode().split('\0')[0]
        original = text[text.index(',L') + 1:].replace('261107,160525', '000000,000000')
        self.assertEqual(firmware_settings(cn1, cn2), original)

    def test_clock_field(self):
        cn1, _ = gsp80cfg.build(self.c, datetime.datetime(2026, 1, 2, 3, 4, 5))
        self.assertTrue(cn1.startswith('D260102,030405,L'))

    def test_field_widths(self):
        self.c.update(L='6', th='8', tl='-5', hh='75', hl='5', S='10')
        cn1, _ = gsp80cfg.build(self.c, None)
        self.assertEqual(cn1, 'L  6,W008-05,7505,K0Uc,S00010,000000,000000')

    def test_cn2_layout(self):
        self.c.update(P='0', A='1', mark='kitchen')
        _, cn2 = gsp80cfg.build(self.c, None)
        self.assertEqual(cn2, '000P0A1Ne03000929{kitchen}')
        self.assertLessEqual(len(cn2), gsp80cfg.CN2_MAX)

    def test_mark_too_long_rejected(self):
        self.c['mark'] = 'x' * 40
        with self.assertRaises(SystemExit):
            gsp80cfg.build(self.c, None)


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.drive = self.tmp.name
        with open(os.path.join(DATA, 'run1_get.txt'), 'rb') as src, \
                open(os.path.join(self.drive, 'get.txt'), 'wb') as dst:
            dst.write(src.read())

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, name):
        with open(os.path.join(self.drive, name)) as f:
            return f.read()

    def test_writes_requested_changes(self):
        r = run(self.drive, '--interval', '60', '--delay', '0', '--unit', 'F', '--temp-high', '100',
                '--temp-low', '32', '--button-tone', 'off', '--button-stop', 'off', '--mark', 'shed',
                '--no-clock')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read('cn1.txt'), 'L  6,W100032,9535,K1Uf,S00000,000000,000000')
        self.assertEqual(self.read('cn2.txt'), '000P0A1Ne03000929{shed}')

    def test_show_and_dry_run_write_nothing(self):
        for args in (['--show'], ['--interval', '60', '-n']):
            r = run(self.drive, *args)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(os.path.join(self.drive, 'cn1.txt')))
        self.assertIn('interval     : 300 s', r.stdout)

    def test_rejects_bad_values(self):
        for args in (['--interval', '65'], ['--interval', '0'], ['--rh-high', '100'],
                     ['--mark', 'a{b}'], ['--button-tone', 'maybe']):
            r = run(self.drive, *args)
            self.assertNotEqual(r.returncode, 0, args)
            self.assertFalse(os.path.exists(os.path.join(self.drive, 'cn1.txt')), args)

    def test_unit_change_warns_about_alarms(self):
        r = run(self.drive, '--unit', 'F', '-n')
        self.assertIn('does NOT convert', r.stderr)
        r = run(self.drive, '--unit', 'F', '--temp-high', '100', '--temp-low', '32', '-n')
        self.assertNotIn('does NOT convert', r.stderr)


if __name__ == '__main__':
    unittest.main()
