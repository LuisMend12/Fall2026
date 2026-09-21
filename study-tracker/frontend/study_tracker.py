"""Study Ledger desktop app: tkinter front end over the C backend DLL.

Run with pythonw for a clean taskbar entry (no console window):
    pythonw study_tracker.py
"""

import ctypes
import os
import random
import time
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

HERE = os.path.dirname(os.path.abspath(__file__))
DLL_PATH = os.path.join(HERE, "..", "backend", "studybackend.dll")

lib = ctypes.CDLL(DLL_PATH)
lib.sl_add_session.argtypes = [ctypes.c_char_p, ctypes.c_double, ctypes.c_char_p, ctypes.c_char_p]
lib.sl_add_session.restype = ctypes.c_int
lib.sl_delete_session.argtypes = [ctypes.c_int]
lib.sl_delete_session.restype = ctypes.c_int
lib.sl_sum_range.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_double)]
lib.sl_sum_range.restype = ctypes.c_int
lib.sl_get_history.argtypes = [ctypes.c_char_p, ctypes.c_int]
lib.sl_get_history.restype = ctypes.c_int
lib.sl_add_todo.argtypes = [ctypes.c_char_p]
lib.sl_add_todo.restype = ctypes.c_int
lib.sl_set_todo_done.argtypes = [ctypes.c_int, ctypes.c_int]
lib.sl_set_todo_done.restype = ctypes.c_int
lib.sl_delete_todo.argtypes = [ctypes.c_int]
lib.sl_delete_todo.restype = ctypes.c_int
lib.sl_get_todos.argtypes = [ctypes.c_char_p, ctypes.c_int]
lib.sl_get_todos.restype = ctypes.c_int

HISTORY_BUF_SIZE = 1 << 20  # 1 MiB: plenty for personal-scale data
TODOS_BUF_SIZE = 1 << 16

DAILY_GOAL_HOURS = 8.0
DAY_START_HOUR = 8     # the study day is assumed to run 8am-11pm for pacing
DAY_END_HOUR = 23
CHECKIN_HOUR = 21      # end-of-day roast/praise popup

GOGGINS_QUOTES = [
    "Stay hard!",
    "Don't stop when you're tired. Stop when you're done.",
    "The most important conversations you'll ever have are the ones you'll have with yourself.",
    "You are in danger of living a life so comfortable and soft, that you will die without ever "
    "realizing your true potential.",
    "We are all in a fight against our comfort zone. It's how you handle that fight that will "
    "determine how great you become.",
    "Motivation is crap. Motivation comes and goes. When you're driven, whatever's in front of "
    "you will get destroyed.",
    "It's so much better when you have callused hands and a calloused mind and heart.",
    "Suffering is the true test of life.",
    "No one is going to come help you. No one is coming to save you.",
    "You have to build calluses on your brain just like how you build calluses on your hands.",
    "When you think you're done, you're only actually 40 percent into what your body's capable "
    "of doing.",
    "Am I doing enough to become the best version of myself?",
    "Embrace the suck.",
]


def goggins_quote():
    return f"“{random.choice(GOGGINS_QUOTES)}”\n— David Goggins"


ROASTS = GOGGINS_QUOTES  # kept for the pacing logic below; formatted via goggins_quote()
PRAISES = [
    "8 hours down. That's actual discipline, not just vibes.",
    "Look at you, showing up for yourself today.",
    "Goal met. Go touch grass, you earned it.",
    "That's the kind of day that shows up on the transcript.",
    "Stay hard. Now go again tomorrow.\n— David Goggins",
]
NUDGES = [
    "Behind pace, but there's still time to fix that.",
    "A slow start beats no start. Get back in.",
    "Small gap right now. Twenty focused minutes closes it.",
]


def today_str():
    return datetime.date.today().isoformat()


def days_ago_str(n):
    return (datetime.date.today() - datetime.timedelta(days=n)).isoformat()


def sum_range(start, end):
    out = ctypes.c_double(0.0)
    lib.sl_sum_range(start.encode("utf-8"), end.encode("utf-8"), ctypes.byref(out))
    return out.value


def get_history():
    buf = ctypes.create_string_buffer(HISTORY_BUF_SIZE)
    lib.sl_get_history(buf, HISTORY_BUF_SIZE)
    rows = []
    for line in buf.value.decode("utf-8", "replace").splitlines():
        parts = line.split("|", 4)
        if len(parts) != 5:
            continue
        rid, date, minutes, subject, note = parts
        try:
            rows.append({"id": int(rid), "date": date, "minutes": float(minutes),
                         "subject": subject, "note": note})
        except ValueError:
            continue
    return rows


def get_todos():
    buf = ctypes.create_string_buffer(TODOS_BUF_SIZE)
    lib.sl_get_todos(buf, TODOS_BUF_SIZE)
    rows = []
    for line in buf.value.decode("utf-8", "replace").splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        rid, done, text = parts
        try:
            rows.append({"id": int(rid), "done": done == "1", "text": text})
        except ValueError:
            continue
    return rows


def fmt_hms(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt_hours_minutes(minutes):
    minutes = round(minutes)
    h, m = divmod(minutes, 60)
    if h == 0:
        return f"{m}m"
    return f"{h}h {m}m" if m else f"{h}h"


class StudyLedgerApp:
    def __init__(self, root):
        self.root = root
        root.title("Study Ledger")
        root.geometry("620x580")
        root.minsize(540, 500)

        self.timer_running = False
        self.timer_start_ts = None
        self.timer_accum = 0.0
        self.timer_subject = None
        self._checkin_shown_date = None
        self._tick_count = 0
        self._current_roast = random.choice(ROASTS)
        self._last_roast_bucket = None

        self._build_style()
        self._build_ui()
        self._tick()
        self._schedule_progress_check()

    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Timer.TLabel", font=("Consolas", 34, "bold"))
        style.configure("Roast.TLabel", font=("Segoe UI", 10), wraplength=560, justify="center")
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))

    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.timer_tab = ttk.Frame(nb)
        self.todo_tab = ttk.Frame(nb)
        self.history_tab = ttk.Frame(nb)
        nb.add(self.timer_tab, text="Timer")
        nb.add(self.todo_tab, text="To-Do")
        nb.add(self.history_tab, text="History")

        self._build_timer_tab()
        self._build_todo_tab()
        self._build_history_tab()

    # ---------- Timer tab ----------
    def _build_timer_tab(self):
        f = self.timer_tab
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(12, 4))
        ttk.Label(row, text="Subject:").pack(side="left")
        self.subject_var = tk.StringVar()
        self.subject_combo = ttk.Combobox(row, textvariable=self.subject_var, width=30)
        self.subject_combo.pack(side="left", padx=8)

        self.timer_label = ttk.Label(f, text="00:00:00", style="Timer.TLabel", anchor="center")
        self.timer_label.pack(pady=14)

        self.status_var = tk.StringVar(value="Ready to start")
        ttk.Label(f, textvariable=self.status_var).pack()

        btn_row = ttk.Frame(f)
        btn_row.pack(pady=10)
        self.start_btn = ttk.Button(btn_row, text="Start", command=self.start_timer)
        self.pause_btn = ttk.Button(btn_row, text="Pause", command=self.pause_timer)
        self.resume_btn = ttk.Button(btn_row, text="Resume", command=self.start_timer)
        self.stop_btn = ttk.Button(btn_row, text="Stop & Save", command=self.stop_and_save)
        self.discard_btn = ttk.Button(btn_row, text="Discard", command=self.discard_timer)
        self._render_timer_buttons()

        ttk.Separator(f).pack(fill="x", pady=10)

        ttk.Label(f, text=f"Today's goal: {DAILY_GOAL_HOURS:g}h", style="Header.TLabel").pack()
        self.progress = ttk.Progressbar(f, maximum=DAILY_GOAL_HOURS * 60, length=400)
        self.progress.pack(pady=8)
        self.progress_label_var = tk.StringVar()
        ttk.Label(f, textvariable=self.progress_label_var).pack()

        self.roast_var = tk.StringVar(value=goggins_quote())
        ttk.Label(f, textvariable=self.roast_var, style="Roast.TLabel").pack(pady=(10, 4), padx=10)
        ttk.Button(f, text="Hit me with another quote", command=self.new_goggins_quote).pack(pady=(0, 8))

    def _render_timer_buttons(self):
        for b in (self.start_btn, self.pause_btn, self.resume_btn, self.stop_btn, self.discard_btn):
            b.pack_forget()
        if not self.timer_running and self.timer_accum == 0:
            self.subject_combo.configure(state="normal")
            self.start_btn.pack(side="left", padx=4)
        elif self.timer_running:
            self.subject_combo.configure(state="disabled")
            self.pause_btn.pack(side="left", padx=4)
            self.stop_btn.pack(side="left", padx=4)
        else:
            self.subject_combo.configure(state="disabled")
            self.resume_btn.pack(side="left", padx=4)
            self.stop_btn.pack(side="left", padx=4)
            self.discard_btn.pack(side="left", padx=4)

    def start_timer(self):
        if not self.timer_running:
            subj = self.subject_var.get().strip() or "General study"
            self.timer_subject = subj
            self.timer_running = True
            self.timer_start_ts = time.time()
            self._render_timer_buttons()

    def pause_timer(self):
        if self.timer_running:
            self.timer_accum += time.time() - self.timer_start_ts
            self.timer_running = False
            self.timer_start_ts = None
            self._render_timer_buttons()

    def _current_elapsed(self):
        extra = (time.time() - self.timer_start_ts) if (self.timer_running and self.timer_start_ts) else 0
        return self.timer_accum + extra

    def stop_and_save(self):
        elapsed = self._current_elapsed()
        minutes = elapsed / 60.0
        if minutes >= 0.5:
            started = datetime.datetime.now() - datetime.timedelta(seconds=elapsed)
            lib.sl_add_session(
                (self.timer_subject or "General study").encode("utf-8"),
                ctypes.c_double(round(minutes, 1)),
                started.date().isoformat().encode("utf-8"),
                b"",
            )
            self.refresh_history_and_stats()
        self.timer_running = False
        self.timer_start_ts = None
        self.timer_accum = 0.0
        self.timer_subject = None
        self._render_timer_buttons()

    def discard_timer(self):
        self.timer_running = False
        self.timer_start_ts = None
        self.timer_accum = 0.0
        self.timer_subject = None
        self._render_timer_buttons()

    def _tick(self):
        self.timer_label.configure(text=fmt_hms(self._current_elapsed()))
        if self.timer_running:
            self.status_var.set(f"Studying {self.timer_subject}")
        elif self.timer_accum > 0:
            self.status_var.set("Paused")
        else:
            self.status_var.set("Ready to start")
        self._tick_count += 1
        if self._tick_count % 5 == 0:
            self._refresh_progress()
        self.root.after(1000, self._tick)

    # ---------- To-Do tab ----------
    def _build_todo_tab(self):
        f = self.todo_tab
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(12, 6), padx=6)
        self.todo_entry = ttk.Entry(row)
        self.todo_entry.pack(side="left", fill="x", expand=True)
        self.todo_entry.bind("<Return>", lambda e: self.add_todo())
        ttk.Button(row, text="Add", command=self.add_todo).pack(side="left", padx=6)

        self.todo_tree = ttk.Treeview(f, columns=("status", "task"), show="headings", height=14)
        self.todo_tree.heading("status", text="")
        self.todo_tree.heading("task", text="Task (double-click to toggle done)")
        self.todo_tree.column("status", width=50, anchor="center")
        self.todo_tree.column("task", width=440, anchor="w")
        self.todo_tree.pack(fill="both", expand=True, padx=6, pady=4)
        self.todo_tree.bind("<Double-1>", self.toggle_todo)

        ttk.Button(f, text="Delete selected", command=self.delete_todo).pack(pady=6)

    def add_todo(self):
        text = self.todo_entry.get().strip()
        if not text:
            return
        lib.sl_add_todo(text.encode("utf-8"))
        self.todo_entry.delete(0, "end")
        self.refresh_todos()

    def toggle_todo(self, _event):
        sel = self.todo_tree.selection()
        if not sel:
            return
        item = sel[0]
        todo_id = int(item)
        currently_done = self.todo_tree.set(item, "status") == "Done"
        lib.sl_set_todo_done(todo_id, 0 if currently_done else 1)
        self.refresh_todos()

    def delete_todo(self):
        sel = self.todo_tree.selection()
        if not sel:
            return
        lib.sl_delete_todo(int(sel[0]))
        self.refresh_todos()

    def refresh_todos(self):
        for row in self.todo_tree.get_children():
            self.todo_tree.delete(row)
        for t in get_todos():
            self.todo_tree.insert("", "end", iid=str(t["id"]),
                                   values=("Done" if t["done"] else "Open", t["text"]))

    # ---------- History tab ----------
    def _build_history_tab(self):
        f = self.history_tab
        stats_row = ttk.Frame(f)
        stats_row.pack(fill="x", pady=(12, 6), padx=6)
        self.stat_vars = {
            "today": tk.StringVar(), "week": tk.StringVar(),
            "all": tk.StringVar(), "streak": tk.StringVar(),
        }
        for key, label in (("today", "Today"), ("week", "Last 7 days"),
                            ("all", "All time"), ("streak", "Streak")):
            box = ttk.Frame(stats_row, relief="groove", padding=8)
            box.pack(side="left", expand=True, fill="x", padx=3)
            ttk.Label(box, textvariable=self.stat_vars[key], font=("Consolas", 13, "bold")).pack()
            ttk.Label(box, text=label, font=("Segoe UI", 8)).pack()

        self.hist_tree = ttk.Treeview(f, columns=("date", "subject", "dur"), show="headings", height=14)
        self.hist_tree.heading("date", text="Date")
        self.hist_tree.heading("subject", text="Subject")
        self.hist_tree.heading("dur", text="Duration")
        self.hist_tree.column("date", width=110, anchor="w")
        self.hist_tree.column("subject", width=250, anchor="w")
        self.hist_tree.column("dur", width=100, anchor="center")
        self.hist_tree.pack(fill="both", expand=True, padx=6, pady=4)

        ttk.Button(f, text="Delete selected session", command=self.delete_session).pack(pady=6)

    def delete_session(self):
        sel = self.hist_tree.selection()
        if not sel:
            return
        lib.sl_delete_session(int(sel[0]))
        self.refresh_history_and_stats()

    def refresh_history_and_stats(self):
        rows = sorted(get_history(), key=lambda r: (r["date"], r["id"]), reverse=True)
        for row in self.hist_tree.get_children():
            self.hist_tree.delete(row)
        for r in rows:
            self.hist_tree.insert("", "end", iid=str(r["id"]),
                                   values=(r["date"], r["subject"], fmt_hours_minutes(r["minutes"])))

        subjects = sorted({r["subject"] for r in rows if r["subject"]})
        self.subject_combo["values"] = subjects

        self.stat_vars["today"].set(fmt_hours_minutes(sum_range(today_str(), today_str())))
        self.stat_vars["week"].set(fmt_hours_minutes(sum_range(days_ago_str(6), today_str())))
        self.stat_vars["all"].set(fmt_hours_minutes(sum_range("0000-01-01", "9999-12-31")))
        self.stat_vars["streak"].set(self._compute_streak_label(rows))
        self._refresh_progress()

    def _compute_streak_label(self, rows):
        dates = {r["date"] for r in rows}
        streak = 0
        cursor = datetime.date.today()
        while cursor.isoformat() in dates:
            streak += 1
            cursor -= datetime.timedelta(days=1)
        return f"{streak}d"

    # ---------- goal pacing / roast ----------
    def _expected_minutes_now(self):
        now = datetime.datetime.now()
        span = DAY_END_HOUR - DAY_START_HOUR
        elapsed = (now.hour + now.minute / 60.0) - DAY_START_HOUR
        elapsed = max(0.0, min(elapsed, span))
        return (elapsed / span) * DAILY_GOAL_HOURS * 60.0

    def _refresh_progress(self):
        today_minutes = sum_range(today_str(), today_str())
        self.progress["value"] = min(today_minutes, DAILY_GOAL_HOURS * 60)
        self.progress_label_var.set(f"{fmt_hours_minutes(today_minutes)} / {DAILY_GOAL_HOURS:g}h today")

        expected = self._expected_minutes_now()
        if today_minutes >= DAILY_GOAL_HOURS * 60:
            self.roast_var.set(random.choice(PRAISES))
        elif today_minutes + 1 < expected - 30:
            self.roast_var.set(self._pick_roast())
        elif today_minutes + 1 < expected:
            self.roast_var.set(random.choice(NUDGES))
        else:
            self.roast_var.set("On pace. Keep going.")

    def _pick_roast(self):
        bucket = datetime.datetime.now().minute // 15
        if bucket != self._last_roast_bucket:
            self._last_roast_bucket = bucket
            self._current_roast = goggins_quote()
        return self._current_roast

    def new_goggins_quote(self):
        self._current_roast = goggins_quote()
        self.roast_var.set(self._current_roast)

    def _schedule_progress_check(self):
        self._maybe_checkin_popup()
        self.root.after(60000, self._schedule_progress_check)

    def _maybe_checkin_popup(self):
        now = datetime.datetime.now()
        today = today_str()
        if now.hour >= CHECKIN_HOUR and self._checkin_shown_date != today:
            self._checkin_shown_date = today
            total = sum_range(today, today)
            if total >= DAILY_GOAL_HOURS * 60:
                messagebox.showinfo("Study Ledger", random.choice(PRAISES))
            else:
                short_by = fmt_hours_minutes(DAILY_GOAL_HOURS * 60 - total)
                messagebox.showwarning(
                    "Study Ledger",
                    f"{goggins_quote()}\n\nYou're {short_by} short of today's {DAILY_GOAL_HOURS:g}h goal.",
                )


def main():
    root = tk.Tk()
    app = StudyLedgerApp(root)
    app.refresh_history_and_stats()
    app.refresh_todos()
    root.mainloop()


if __name__ == "__main__":
    main()
