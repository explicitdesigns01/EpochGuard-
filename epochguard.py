"""
EPOCHGUARD v1.1
Idea by: Waheed Qazeem Ayomide

WHAT IT DOES
  Reads C/C++ code (and SQL files) and flags lines that might hold a
  time value in a 32-bit "box". Those are the lines that break in 2038.

HOW TO USE
  1. Run this file in Pydroid 3.
  2. When it asks for a folder, press Enter to scan the built-in demo,
     or type the path of a folder with real code.
  3. Read the report on screen. It is also saved in scan_report.txt.

IMPORTANT
  This scanner matches TEXT patterns. It does not understand code fully,
  so it can flag harmless lines (false alarms) and miss some real risks.
  Making it smarter is the project.
"""

import os
import re


# ---------------------------------------------------------------
# PART 1: SETTINGS (things you can change)
# ---------------------------------------------------------------

# File types we scan.
C_EXTS = (".c", ".h", ".cpp", ".cc", ".hpp")
SQL_EXTS = (".sql",)
ALL_EXTS = C_EXTS + SQL_EXTS

# Folders we never go into.
SKIP_FOLDERS = (".git", "node_modules", "__pycache__")

# Words in a variable NAME that hint it holds a time value.
TIME_WORDS = ("time", "stamp", "expire", "expiry", "created",
              "modified", "mtime", "ctime", "atime", "deadline", "epoch")

# True = also show low-priority INFO notes. False = hide them.
SHOW_INFO = True


# ---------------------------------------------------------------
# PART 2: PATTERNS (what each rule looks for)
# A "regex" is a search pattern for text. Each one below is a rule.
# ---------------------------------------------------------------

# 32-bit types: int, long, int32_t, uint32_t (optionally unsigned/signed).
TYPES = r"(?:unsigned\s+|signed\s+)?(?:int|long|int32_t|uint32_t)"

# A variable declaration, like:  int created_at   or   long expires
DECL = re.compile(r"\b" + TYPES + r"(?:\s+int)?\s+\**\s*([A-Za-z_]\w*)")

# A time() result stored in a 32-bit variable:  int now = time(NULL);
ASSIGN_TIME = re.compile(r"\b" + TYPES + r"\s+\w+\s*=\s*time\s*\(")

# A time() result forced into 32 bits:  (int) time(NULL)
CAST_TIME = re.compile(r"\(\s*" + TYPES + r"\s*\)\s*time\s*\(")

# The biggest 32-lamp number written out, or its common names.
LIMIT = re.compile(r"2147483647|0x7fffffff|\bINT_MAX\b|\bINT32_MAX\b",
                   re.IGNORECASE)

# The time_t type (32 bits on old systems, 64 bits on modern ones).
TIME_T = re.compile(r"\btime_t\b")

# Calendar functions that fail past 2038 if time_t is 32 bits.
TIME_FUNCS = re.compile(r"\b(?:gmtime|localtime|mktime|ctime|asctime)\s*\(")

# SQL column type TIMESTAMP (some database versions stop at 2038).
SQL_TS = re.compile(r"\bTIMESTAMP\b", re.IGNORECASE)


# ---------------------------------------------------------------
# PART 3: THE RULES THEMSELVES
# Each finding = (severity, short title, advice)
# ---------------------------------------------------------------

def is_comment(text, ext):
    """True if the line is a comment, so we can skip it."""
    if ext in SQL_EXTS:
        return text.startswith("--")
    return text.startswith(("//", "/*", "*"))


def check_line(text, ext):
    """Look at ONE line and return a list of findings."""
    findings = []

    # SQL files only have one rule.
    if ext in SQL_EXTS:
        if SQL_TS.search(text):
            findings.append((
                "MEDIUM", "SQL TIMESTAMP column",
                "Some database versions stop at 2038. Check your version, "
                "or use DATETIME / a 64-bit column."))
        return findings

    # "long long" is already 64 bits (safe), so hide it from the rules.
    text = re.sub(r"\blong\s+long\b", "int64_t", text)

    flagged_high = False

    # Rule 1: a 32-bit variable whose NAME sounds like time.
    for match in DECL.finditer(text):
        name = match.group(1).lower()

        # v1.1 filter A: a name followed by "(" is a FUNCTION, not a
        # variable holding time (example: int uptime_main(...)).
        if text[match.end():].lstrip().startswith("("):
            continue

        # v1.1 filter B: counters and nanosecond fields are not
        # second-counters, so they cannot hit the 2038 wall.
        if "count" in name or "nsec" in name:
            continue

        if "timeout" in name:
            findings.append((
                "MEDIUM", "32-bit timeout variable",
                "If a timeout is ADDED to the current time, the sum can "
                "pass the 32-bit limit. Use int64_t for the result."))
        elif any(word in name for word in TIME_WORDS):
            findings.append((
                "HIGH", "32-bit variable holds time",
                "Change the type to int64_t (or time_t on a 64-bit-time "
                "build)."))
            flagged_high = True

    # Rule 2: time() squeezed into 32 bits (skip if Rule 1 already caught it).
    if not flagged_high:
        if ASSIGN_TIME.search(text) or CAST_TIME.search(text):
            findings.append((
                "HIGH", "time() stored in 32 bits",
                "time() returns a time_t. Store it in time_t or int64_t, "
                "not int or long."))

    # Rule 3: the 32-bit limit written into the code.
    if LIMIT.search(text):
        findings.append((
            "MEDIUM", "32-bit limit constant",
            "Check if this number is used for time. If yes, it is a "
            "hidden 2038 wall."))

    # Rule 4 and 5: low-priority notes.
    if SHOW_INFO:
        if TIME_T.search(text):
            findings.append((
                "INFO", "uses time_t",
                "Safe on 64-bit time. On old 32-bit builds it is 32 bits. "
                "Check compile flags (_TIME_BITS=64)."))
        if TIME_FUNCS.search(text):
            findings.append((
                "INFO", "calendar function",
                "Breaks past 2038 if time_t is 32 bits. Test with dates "
                "after 2038."))

    return findings


# ---------------------------------------------------------------
# PART 4: SCANNING ONE FILE
# ---------------------------------------------------------------

def scan_file(path):
    """Read one file line by line. Return a list of findings."""
    ext = os.path.splitext(path)[1].lower()
    results = []
    try:
        # errors="ignore" skips strange characters instead of crashing.
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for number, line in enumerate(f, 1):
                text = line.strip()
                if text == "" or is_comment(text, ext):
                    continue
                for severity, title, advice in check_line(text, ext):
                    results.append((path, number, severity, title,
                                    text, advice))
    except OSError as error:
        print("Could not read", path, "->", error)
    return results


# ---------------------------------------------------------------
# PART 5: SCANNING A WHOLE FOLDER
# ---------------------------------------------------------------

def scan_folder(folder):
    """Walk through every sub-folder and scan matching files."""
    all_results = []
    files_scanned = 0
    for root, dirs, files in os.walk(folder):
        # Remove folders we want to skip, so os.walk never enters them.
        dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS]
        for name in files:
            if name.lower().endswith(ALL_EXTS):
                files_scanned += 1
                all_results.extend(scan_file(os.path.join(root, name)))
    return all_results, files_scanned


# ---------------------------------------------------------------
# PART 6: A DEMO FOLDER (so it works the first time you run it)
# ---------------------------------------------------------------

DEMO_C = """#include <time.h>
struct session {
    int created_at;
    long expires;
    long long safe_stamp;
};
int main() {
    int now = time(NULL);
    time_t t = time(NULL);
    struct tm *p = gmtime(&t);
    int timeout = 30;
    int max = 2147483647;
    // int old_timestamp = 0;
    return 0;
}
"""

DEMO_SQL = """CREATE TABLE users (
  id INT,
  created_at TIMESTAMP
);
"""


def make_demo():
    """Create demo_project/ with two small files to scan."""
    os.makedirs("demo_project", exist_ok=True)
    with open("demo_project/clock.c", "w") as f:
        f.write(DEMO_C)
    with open("demo_project/db.sql", "w") as f:
        f.write(DEMO_SQL)
    return "demo_project"


# ---------------------------------------------------------------
# PART 7: THE REPORT
# ---------------------------------------------------------------

def build_report(results, files_scanned, folder):
    """Turn findings into readable text lines."""
    order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
    results = sorted(results, key=lambda r: (order[r[2]], r[0], r[1]))

    lines = []
    lines.append("EPOCHGUARD SCAN REPORT")
    lines.append("Folder: " + folder)
    lines.append("Files scanned: " + str(files_scanned))
    lines.append("")

    for path, number, severity, title, code, advice in results:
        short_path = os.path.relpath(path, folder)
        if len(code) > 60:
            code = code[:57] + "..."
        lines.append("[" + severity + "] " + short_path + " line " + str(number))
        lines.append("  " + title)
        lines.append("  code: " + code)
        lines.append("  fix:  " + advice)
        lines.append("")

    counts = {"HIGH": 0, "MEDIUM": 0, "INFO": 0}
    for r in results:
        counts[r[2]] += 1
    lines.append("SUMMARY")
    lines.append("  HIGH:   " + str(counts["HIGH"]))
    lines.append("  MEDIUM: " + str(counts["MEDIUM"]))
    lines.append("  INFO:   " + str(counts["INFO"]))
    return lines


# ---------------------------------------------------------------
# PART 8: MAIN (this is where the program starts)
# ---------------------------------------------------------------

def main():
    print("=== EPOCHGUARD v1.1 ===")
    answer = input("Folder to scan (press Enter for demo): ").strip()
    answer = answer.strip("'\"")

    if answer == "":
        folder = make_demo()
        print("Using demo folder:", folder)
    else:
        folder = answer

    if not os.path.isdir(folder):
        print("That folder was not found:", folder)
        return

    results, files_scanned = scan_folder(folder)
    report = build_report(results, files_scanned, folder)

    print("")
    for line in report:
        print(line)

    with open("scan_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print("")
    print("Report saved to:", os.path.abspath("scan_report.txt"))


main()
