# Study Ledger

A desktop study-time tracker: a focus timer, a to-do list, and history/stats,
backed by a daily hour goal that nags you (with real David Goggins quotes)
when you fall behind pace.

It's a real Windows app, not a browser page, so it shows up in your taskbar
like any other program.

Architecture: a C backend (`backend/studybackend.c`, compiled to
`studybackend.dll`) owns all storage and math — sessions, to-dos, date-range
sums — as flat files under `%APPDATA%\StudyLedger`. The Python/tkinter
frontend (`frontend/study_tracker.py`) is the GUI and talks to the DLL
through `ctypes`.

## Setup

Requires a C compiler (MinGW-w64 `gcc`) and Python 3 with `tkinter` (both
already on this machine). Build the backend once:

```powershell
cd study-tracker/backend
gcc -shared -O2 -Wall -o studybackend.dll studybackend.c -Wl,--out-implib,libstudybackend.a
```

Re-run that whenever `studybackend.c` changes — the frontend loads whatever
`studybackend.dll` currently sits next to it.

## Running it

```powershell
study-tracker\launch_study_ledger.bat
```

or directly:

```powershell
C:\Python314\pythonw.exe study-tracker\frontend\study_tracker.py
```

(`pythonw`, not `python`, so no console window opens alongside the GUI.)

To pin it to the taskbar: run `create_shortcut.ps1` once (creates
`Study Ledger.lnk` on the Desktop), then right-click the app in the taskbar
while it's running — or the shortcut itself — and choose **Pin to taskbar**.

```powershell
powershell -ExecutionPolicy Bypass -File study-tracker\create_shortcut.ps1
```

## Features

- **Timer tab** — pick a subject, Start/Pause/Stop & Save. Shows today's
  progress toward an 8h goal and a 🔥 day-streak counter (a streak survives
  through today until the day actually ends without a session).
- **To-Do tab** — add tasks, double-click to check off, delete when done.
- **History tab** — today / last-7-days / all-time totals, streak, and a
  deletable session log.
- **Goal pacing & Goggins quotes** — falling behind the expected pace for
  the time of day surfaces a real, verified David Goggins quote under the
  timer (button to pull another on demand); hitting the goal swaps in a
  congratulatory line instead. At 9pm, if you're still short, a popup names
  exactly how far short you are.

## Data

Everything lives in `%APPDATA%\StudyLedger\`:

- `sessions.dat` — `id|date|minutes|subject|note`, one line per session.
- `todos.dat` — `id|done|text`, one line per to-do.

Plain text, so it's easy to back up, inspect, or migrate — but it also means
there's no encryption or multi-device sync; it's local to this machine.

## Notes / current limits

- The 8h daily goal, the 8am-11pm pacing window, and the 9pm check-in time
  are constants at the top of `study_tracker.py`, not exposed in the UI yet.
- Personal-scale data only — the backend scans the whole file on every read,
  which is instant for hundreds of sessions but wasn't built for thousands.
- Single-user, single-machine: there's no concept of separate profiles.
