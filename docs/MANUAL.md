# GSP-80 stock firmware: user guide

A practical rewrite of the paper instructions and Q&A sheet that came with the logger
(AKS / AIKESI, stock firmware). The manufacturer's content is kept, reorganised for quick
reference. Notes marked **ⓘ Repo note** are ours, linking the manual to what this repo
found in the firmware; they are not from the manufacturer.

Symbols used for the buttons and screen icons:

| Symbol | Meaning |
|---|---|
| **◀** | Left button |
| **⚙** | Settings button (middle) |
| **▶** | Right button |
| **◀+▶** | Press left and right together |
| 🔒 | Lock icon (top right of screen) |
| ⤒ / ⤓ | Upper / lower limit alarm arrows (left of a reading) |
| `[REC]` `[STOP]` `[USB]` `[LOG]` `[DATE]` `[TIME]` | Boxed text icons on the LCD |

"Long press" means about **4 seconds**.

## Quick reference

| Button | Short press | Long press (~4 s) |
|---|---|---|
| **◀** | Step through screens / in settings: **decrease** value | **Start / stop recording**; in settings: decrease in larger jumps |
| **⚙** | In settings: next setting | **Enter / exit settings** (only when stopped) |
| **▶** | Step through screens / in settings: **increase** value | **Power on / off** (only when stopped); in settings: increase in larger jumps |
| **◀+▶** | **Lock / unlock** | |

The printed key table has the value directions the wrong way round ("Numeric +" for ◀,
"Numeric −" for ▶). The table above is as observed on the device: ▶ increases, ◀ decreases,
and holding either changes the value in larger jumps.

| I want to… | Do this |
|---|---|
| Turn on | Hold **▶** ~3 s until the screen shows **On** |
| Turn off | Unlock, make sure it's stopped, hold **▶** ~4 s until **OFF** |
| Unlock / lock | Press **◀+▶** together (it auto-locks after 60 s idle) |
| Start recording | Unlock, hold **◀** ~4 s → `[REC]` flashes during the start delay, then stays on |
| Stop recording | Unlock, hold **◀** ~4 s → `[STOP]` appears |
| Look at max / min / average, date, time | Short-press **◀** or **▶** to step through screens |
| Change settings | Stop recording, unlock, hold **⚙** ~4 s ⚠ **this clears the recorded data** |
| Get the data off | Stop recording, plug in USB; a PDF report appears on the drive |

## Specifications (from the manual)

| | |
|---|---|
| Temperature range | −30 °C to +60 °C (logger body) |
| External probe temperature range | −40 °C to +85 °C |
| Humidity range | 5.0 % to 99.9 % RH |
| Accuracy | Temperature ±0.3 °C, humidity ±5.0 % (as printed) |
| Resolution | 0.1 °C, 0.1 % RH |
| Capacity | 99,990 records |
| Sampling interval | 5 s to 90 min (as printed) |
| Interface | USB Type-C |
| Power | Built-in 3.7 V rechargeable Li-ion, or USB power |
| Battery life | More than 1 year, at room temperature with buzzer/sound prompts disabled |
| Units | °C or °F |
| Water resistance | IP3X: **not** suitable for rain or splashing water |
| Sensor | External temperature+humidity probe, or temperature-only probe (GSP-70 Pro), in the 3.5 mm jack at the bottom |

In the cold the LCD may respond slowly; this doesn't affect measurement or recording.

> **ⓘ Repo note:** the firmware stops at 99,990 records (no wrap-around); see the capacity
> table in [INTERNALS.md](INTERNALS.md#memory-capacity). Settings written with
> `gsp80cfg.py` use 10 s steps (10–9990 s); the firmware's internal tick is 5 s.

## Screen

```
 [USB] [REC] [STOP]  ▮▮▮        ← status icons, battery
  MAX  MIN  AVR   ⚙ 🔒          ← which statistic is shown, settings mode, locked
⤒⤓  888.8 °C/°F                ← temperature (alarm arrows on the left)
⤒⤓  88.8 %                     ← humidity
    88:88:88                    ← record count / date / time
   [LOG] [DATE] [TIME]          ← what the bottom line is showing
```

| Icon | Meaning |
|---|---|
| ▮▮▮ (battery) | Battery level; blinks while charging over USB |
| 🔒 | Locked: only current readings, record count, date and time can be viewed |
| ⚙ | In the settings menu |
| `[STOP]` | Not recording |
| `[REC]` | Recording (flashing = waiting for the start delay) |
| `[USB]` | Connected to a computer |
| MAX / MIN / AVR | Highest / lowest / average reading in the current recording |
| `[LOG]` | Recording-info screen; bottom-right number = number of records |
| `[DATE]` | Date screen, with current readings |
| `[TIME]` | Time screen, with current readings |
| ⤒ | A reading went above the upper alarm limit |
| ⤓ | A reading went below the lower alarm limit |

If the readings show as `----.-°C`, the sensor isn't detected: check the probe is fully
inserted. A damaged probe needs replacing (contact the seller).

### Battery level

| Icon | Remaining |
|---|---|
| ▮▮▮ | 75–100 % |
| ▮▮▯ | 50–75 % |
| ▮▯▯ | 25–50 % |
| ▯▯▯ | < 10 %: charge it soon |

## Step by step

### 1. Power on

Plug the external sensor into the 3.5 mm jack at the bottom (the logger can't be used
without it). Hold **▶** for about 3 s until the screen shows **On**.

The logger starts on the `[LOG]` screen, stopped, with record count **0** in the bottom
right corner.

### 2. Viewing readings

Short-press **◀** or **▶** to step through the screens: date & time, maximum (MAX),
minimum (MIN), average (AVR), etc.

### 3. Lock and unlock

The logger locks itself after **60 s** with no button presses (🔒 appears top right).
Press **◀+▶** together to lock or unlock manually. While locked you can only view current
readings, record count, date and time; you must unlock to record, change settings or
switch off.

### 4. Start recording

1. Unlock, and make sure the logger is stopped.
2. Hold **◀** for about 4 s. The screen switches to the recording screen, `[REC]` flashes
   in the top left and a countdown (the start delay) shows in the bottom right.
3. When the countdown ends, `[REC]` stops flashing and recording begins. On the `[LOG]`
   screen the bottom-right number is the record count. The green light blinks once for each
   record saved.

The start delay can be changed in the settings menu or with the configuration tool.

### 5. Stop recording

* Manually: unlock, hold **◀** for about 4 s; `[STOP]` appears at the top.
* Automatically: recording stops when it reaches **99,990** records.
* From the computer: with the configuration tool.

⚠ **Starting a new recording erases the previous one.** Copy the data off first.

> **ⓘ Repo note:** stop-by-button can be disabled (`gsp80cfg.py --button-stop off`). The
> computer "software stop" corresponds to the firmware's `stp.txt` command file (see
> INTERNALS.md).

### 6. Settings menu

1. Stop recording and unlock.
2. Hold **⚙** for about 4 s; ⚙ appears top right.
3. Short-press **⚙** to move to the next setting. Press **▶** to increase the value and
   **◀** to decrease it; hold either for larger jumps.
   The settings, in order: temperature alarm upper/lower limits, °C/°F, recording interval,
   date & time.
4. Hold **⚙** again to save and exit. If no button is pressed for about 60 s, it returns to
   the recording screen and locks.

⚠ **Entering the settings menu clears the recorded data.** Export it first.

The on-device menu can only set: temperature/humidity limits, unit, interval, date & time.
Start delay (stated default 20 s), button/alarm sounds and button-stop need the computer
tool. Don't use the device menu and the computer tool at the same time.

> **ⓘ Repo note:** on Linux, `tools/gsp80cfg.py` does everything the Excel tool does
> (interval, start delay, alarms, unit, button stop, key tone, alarm tone, track mark,
> clock) without clearing data; see the [README](../README.md). The units examined had a
> 600 s start delay from the factory, not 20 s.

### 7. Alarms

While recording, if a reading goes above the upper limit ⤒ lights next to it on the
`[LOG]` screen; below the lower limit, ⤓ lights. While out of range it beeps once for
every record saved.

To silence key beeps and alarm beeps, turn them off with the computer tool
(or `gsp80cfg.py --button-tone off --alarm-tone off`).

### 8. Getting the data off

1. Stop recording.
2. Connect a USB-C **data** cable (some cables are charge-only) to a computer. `[USB]`
   appears top left and the battery icon blinks.
3. After a recording stops, the logger generates a PDF report (the screen shows "PDF")
   which appears on the USB drive.

The manufacturer's Excel tool can also export the data to `.xlsx`.

> **ⓘ Repo note:** for a clean CSV use `tools/rad2csv.py`. The PDF has a firmware bug that
> adds junk rows at the end.

### 9. Switch off

Unlock, make sure it's stopped (`[STOP]`, not `[REC]`), then hold **▶** for about 4 s
until the screen shows **OFF**.

### 10. Wall hook

Line up the hook's three clips with the three slots on the back of the case and push
gently upwards until it clicks. Stick the hook where you want it with adhesive.

## The manufacturer's Excel configuration tool

The manual describes a Windows-only Excel workbook, **"Logger manage (V0.31).xlsm"** (also
called "Logger Configuration (V0.31).xlsm"), supposedly supplied on the logger's USB drive.
It says to **copy it to a computer before the first recording**, because the first
recording wipes the drive.

Using it (from the manual): with the logger stopped, plug it into a Windows PC, open the
workbook in Excel and enable macros (File → Options → Trust Center → Trust Center Settings
→ Enable VBA Macros, then reopen). Then:

* **Read Configuration**: shows model, serial number, track code, track mark ("travel
  description"), status and record count.
* Edit sampling interval, start delay, unit, key stop, temperature/humidity limits, key
  sound, alarm sound.
* **Export Data**: saves the recording to an Excel file.
* **Stop Recording**: software stop.
* **Save Configuration**: confirm, then unplug; the logger applies the settings and syncs
  its clock to the PC.
* A "Reference" sheet lists recommended settings for various industries.

> **ⓘ Repo note:** neither unit examined had this file on its drive, and it was never
> needed. `gsp80cfg.py` writes the same `cn1.txt`/`cn2.txt` files the workbook must write
> (also applied on unplug); see [INTERNALS.md](INTERNALS.md).

## Troubleshooting (from the Q&A sheet)

| Problem | Cause / fix |
|---|---|
| Beeps once per record while recording | A reading is outside the alarm limits. Change the limits, or turn off alarm sound |
| Beeps periodically and shows no readings | Probe unplugged or loose: reseat it |
| Readings show `----.-°C` | Sensor not detected or damaged: reseat, or replace the probe |
| Green light flashes once per record | Normal: one flash per record saved |
| Green light flashes rapidly when plugged into a computer | USB connection problem: try another cable/port, check USB drivers |
| Can't open settings or switch off | It's locked (🔒): press **◀+▶**. Or it's recording (`[REC]`): hold **◀** 4 s to stop first |
| Something doesn't work | Switch off and on again |

### Notices

* Don't unplug or swap the probe while recording.
* Charge it promptly when the battery is low, or recording may fail.
* IP3X only: keep it out of rain, splashes and condensation.
* On first use, connect it to a computer to set it up and sync the clock (the manual
  also says to back up the Excel tool from the drive).
