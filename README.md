# EpochGuard: Y2038 Time-Bug Scanner

*An open-source Year 2038 bug finder, by Waheed Qazeem Ayomide.*

**A beginner-friendly tool that finds code which could break in the Year 2038 bug.**

It reads C/C++ and SQL files, flags lines that might store time in a 32-bit "box", and explains how to fix each one.

> **Not affiliated with any company or product with a similar name.** This is an independent, open-source learning project that scans source code for Year 2038 time-storage bugs. It is not a security, compliance, or risk-assurance product.

> Status: early version (v1.1). It works, it has limits, and I am improving it step by step.

---

## Why I made this

At **03:14:07 UTC on 19 January 2038**, computers that store time in a signed 32-bit number will run out of room. The number wraps around to a large negative value, and the computer thinks the date is **13 December 1901**.

The fix is already known: use 64 bits for time. Modern systems have mostly done this. What is still unsolved is the **long tail**:

- old software and embedded devices that nobody has checked
- hidden 32-bit timestamps buried in code
- old database columns and file formats

You cannot fix a bug you have not found. So my idea was to build a tool that **helps find the hidden 32-bit time bugs first**.

I am a beginner, and I learned the basics of binary, signed numbers, and Python while building this. I started with a simple question: *what actually happens when a number runs out of room?* Then I tested it on my own phone, which really is a 32-bit system, and watched Python crash with `OverflowError: timestamp out of range for platform time_t`. That is the bug, live.

---

## What it does

1. Asks for a folder (or press Enter to scan a built-in demo).
2. Goes through every sub-folder and reads `.c`, `.h`, `.cpp`, `.cc`, `.hpp` and `.sql` files, line by line.
3. Checks each line against a set of rules.
4. Prints a report with the **file, line number, severity, the risky code, and a suggested fix**.
5. Saves the same report to `scan_report.txt`.

### What it looks for

| Severity | What it flags | Example |
|---|---|---|
| **HIGH** | A 32-bit variable (`int`, `long`, `int32_t`, `uint32_t`) with a time-like name | `int created_at;` |
| **HIGH** | `time()` stored or cast into a 32-bit type | `int now = time(NULL);` |
| **MEDIUM** | A 32-bit timeout variable (can overflow when added to the current time) | `int timeout = 30;` |
| **MEDIUM** | The 32-bit limit written into code | `2147483647`, `INT_MAX`, `0x7fffffff` |
| **MEDIUM** | SQL `TIMESTAMP` columns (some database versions stop at 2038) | `created_at TIMESTAMP` |
| **INFO** | Use of `time_t` (safe on 64-bit time, 32 bits on old builds) | `time_t t = time(NULL);` |
| **INFO** | Calendar functions that break past 2038 on 32-bit time | `gmtime()`, `localtime()`, `mktime()` |

It skips comment lines, and it treats `long long` as safe because it is already 64 bits.

---

## Example output

```
EPOCHGUARD SCAN REPORT
Folder: demo_project
Files scanned: 2

[HIGH] clock.c line 3
  32-bit variable holds time
  code: int created_at;
  fix:  Change the type to int64_t (or time_t on a 64-bit-time build).

[HIGH] clock.c line 8
  time() stored in 32 bits
  code: int now = time(NULL);
  fix:  time() returns a time_t. Store it in time_t or int64_t, not int or long.

SUMMARY
  HIGH:   3
  MEDIUM: 3
  INFO:   2
```

---

## How to run it

You only need **Python 3**. There is nothing to install.

**On a computer:**

```
python epochguard.py
```

**On an Android phone:** open `epochguard.py` in the Pydroid 3 app and tap the play button.

**Live web version:** open `epochguard-web.html` in any browser. Paste code and the results update as you type. Nothing is uploaded, because it all runs on your device.

Press Enter at the prompt to scan the built-in demo, or type the path of a folder with real code.

---

## Tested on real code

I ran EpochGuard on the source code of **BusyBox**, a real open-source project (751 C, header and SQL files scanned).

| Version | HIGH | MEDIUM | INFO |
|---|---|---|---|
| v1 (first run) | 74 | 146 | 163 |
| v1.1 (after two filters) | 48 | 141 | 163 |

**What I learned from the results:**

- **Some hits are worth a human look.** For example, one line casts `time(NULL)` to an `int` before writing it out. That is exactly the pattern I am hunting.
- **Some hits are fixed by a file format, not by the programmer.** Fields like `uint32_t i_mtime` in file-system structures are defined by the format itself, so changing the type is not enough. These need a different kind of fix.
- **My first version raised false alarms.** It flagged function names like `uptime_main` as if they were time variables. Fixing that cut the HIGH count from 74 to 48. That is why v1.1 exists.
- **More false alarms remain.** Names such as `sleeptime` and `waittime` are durations, not dates, and many `INT_MAX` uses have nothing to do with time. Reducing these is the next step.

These findings are leads for review. I have not confirmed any of them as bugs yet.

### More projects (v1.1)

| Project | Files scanned | HIGH | MEDIUM | INFO |
|---|---|---|---|---|
| BusyBox | 751 | 48 | 141 | 163 |
| Lua | 68 | 0 | 30 | 16 |
| zlib | 79 | 1 | 2 | 6 |
| curl | 1078 | 45 | 219 | 152 |

**What I learned from reading these results:**

- **Careful projects score low.** Lua had zero HIGH findings. Its MEDIUM hits are mostly `INT_MAX` used for sizes, not time.
- **Most of curl's HIGH hits are not dates.** Names like `idle_time_ms`, `sleeptime`, `retry_time` and `timer_calls` are durations in milliseconds or seconds, or counters. They are small numbers that do not reach the 2038 limit. Many also sit in test code and function parameters.
- **zlib's one HIGH hit is a file-format field.** It reads a 16-bit time stored inside a ZIP header, which the ZIP format defines.
- **So EpochGuard currently over-reports.** It is good at pointing at places to look, and not yet good at telling dates apart from durations. Fixing that is my next step.

---

## Limits (please read)

This is version 1, and I want to be honest about what it cannot do.

- **It matches text, not meaning.** It does not truly understand code, so it can give **false alarms** (for example, a variable called `runtime` contains the word "time").
- **It can miss real bugs.** If a time value has an ordinary name like `x`, or is hidden behind a macro or typedef, the scanner may not notice.
- **It cannot tell which system the code will run on.** `time_t` is safe on 64-bit time and risky on 32-bit, and a text search cannot know which one applies. That is why it only gives it an INFO note.
- **It only covers C, C++ and SQL files.** Other languages and file formats are not checked yet.
- **It does not fix anything.** It points to the problem and suggests a fix, and a human still has to make the change.
- **Treat results as leads to investigate, not as proof of a bug.**

---

## Roadmap

- [x] Test it on a real open-source C project (BusyBox) and measure the false alarms
- [x] Test it on more projects (Lua, zlib, curl)
- [ ] v1.2: skip durations (ms, sleep, retry), counters and test folders
- [ ] Reduce false alarms and catch more hidden cases
- [ ] Add more rules (for example, 32-bit time inside file formats and network code)
- [ ] Add a safe-patch suggestion for the common cases
- [ ] Support more languages
- [ ] Submit real fixes to open-source projects and share what I find

---

## How this project was built

The idea, direction, testing, and decisions are mine. I am learning as I go, and I used **Claude (an AI assistant made by Anthropic)** as a tutor and coding helper, asking it to explain each concept and each line of code until I understood it. I am being open about that because I think it matters.

---

## Author

**Waheed Qazeem Ayomide**
Graphic designer, tech entrepreneur, and coding instructor. Founder of Explicit Designs.

Feedback, ideas, and corrections are very welcome. Open an issue or send a message.
