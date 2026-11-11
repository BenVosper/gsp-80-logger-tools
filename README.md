# GSP-80 logger tools

Two small Python tools for the **AIKESI / CHNADKS GSP-80S** temperature & humidity logger,
so you can use it from Linux without the vendor's Windows/Excel software. 

#### Models tested and working:

 - **GSP-80S** (with sensor unit attached to main body)
 - **GSP-80Pro** (with sensor unit on long cable)

The GSP-70 variants (which have temperature only) very likely run the same firmware (it
auto-detects the probe type) and should work too; see
[docs/INTERNALS.md](docs/INTERNALS.md#model-variants-what-is-known).

* **`tools/gsp80cfg.py`**: view and change the logger's settings, and set its clock.
* **`tools/rad2csv.py`**: turn a recording into a clean CSV, one row per sample with a timestamp.

Both need only Python 3 (standard library). How to use the logger's buttons and screen
(the stock firmware's manual, rewritten) is in [docs/MANUAL.md](docs/MANUAL.md). How the
logger works inside, and how this was worked out, is in [docs/INTERNALS.md](docs/INTERNALS.md).

## Mounting the logger

Plug the logger in and mount it so your user can write to it (replace `/dev/sdX`; check with `lsblk`):

```sh
sudo mount -o uid=$(id -u),gid=$(id -g) /dev/sdX /mnt/bulk
```

The drive contains the PDF report plus two hidden files: `get.txt` (settings and summary)
and, after a recording, `rad.txt` (the raw data).

## Changing settings: `gsp80cfg.py`

```sh
python3 tools/gsp80cfg.py /mnt/bulk --show                      # print current settings
python3 tools/gsp80cfg.py /mnt/bulk --interval 300 --delay 0 \
        --temp-low 2 --temp-high 8 --mark "fridge"              # change some settings
```

Then **unmount and unplug** the logger. The new settings are applied when USB is
disconnected. The tool always sets the logger's clock to your computer's time too
(use `--no-clock` to skip that).

| Option | Meaning |
|---|---|
| `--interval SEC` | Record interval, 10–9990 s in steps of 10 |
| `--delay SEC` | Start delay after pressing start, 0–99999 s |
| `--temp-high DEG`, `--temp-low DEG` | Temperature alarm limits, in the logger's unit |
| `--rh-high PCT`, `--rh-low PCT` | Humidity alarm limits |
| `--unit C\|F` | Temperature unit (display, PDF and raw data) |
| `--button-stop on\|off` | Allow stopping a recording with the `<` button |
| `--button-tone on\|off` | Beep on key press |
| `--alarm-tone on\|off` | Beep on alarm |
| `--mark TEXT` | Track mark printed in the PDF (about 25 chars max, no `{ }`) |
| `--show` | Only print the current settings |
| `-n`, `--dry-run` | Show what would be written without writing it |
| `--get FILE` | Read settings from a saved `get.txt` instead of the drive |

Anything you don't specify keeps its current value. Notes:

* **Changing `--unit` does not convert the alarm limits.** Give `--temp-high`/`--temp-low`
  in the new unit at the same time (the tool warns if you don't).
* The tool copies the logger's serial number from its own `get.txt`. The settings file
  includes it, so don't reuse files written for one logger on another.
* The tool writes `cn1.txt` and `cn2.txt` to the drive; the logger reads and deletes them.

## Exporting data: `rad2csv.py`

After stopping a recording and plugging the logger in:

```sh
python3 tools/rad2csv.py /mnt/bulk/rad.txt --get /mnt/bulk/get.txt -o recording.csv
```

```
record,timestamp,temp_C,rh_pct
1,2026-11-07 16:05:24,18.9,71.0
2,2026-11-07 16:10:24,18.7,71.4
...
```

* Copy the data off before starting a new recording: the logger wipes the drive when the
  next recording is saved.
* Always pass `--get` if you have it. It provides the exact record count, interval and
  model (temperature+RH or temperature only), plus the start time for very short recordings.
  Without it the tool assumes a temperature+RH logger; use `--channels 1` for a GSP-70.
* Without `-o` the CSV goes to stdout. The temperature column is `temp_C` or `temp_F` to
  match the logger's unit.
* The firmware pads the end of the data with junk readings (`-46.9` / `655.3`); these are
  removed automatically.

## Tests

```sh
python3 -m unittest discover -s tests -v
```
