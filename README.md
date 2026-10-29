# Y2038 Scanner

**A beginner-friendly tool that finds code which could break in the Year 2038 bug.**

It reads C/C++ and SQL files, flags lines that might store time in a 32-bit "box", and explains how to fix each one.

> Status: early version (v1). It works, it has limits, and I am improving it step by step.

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
Y2038 SCAN REPORT
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
python scanner.py
```

**On an Android phone:** open `scanner.py` in the Pydroid 3 app and tap the play button.

Press Enter at the prompt to scan the built-in demo, or type the path of a folder with real code.

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

- [ ] Test it on real open-source C projects and measure the false alarms
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
