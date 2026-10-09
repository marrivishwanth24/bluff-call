"""
questions.py — the curated question bank for Bluff Call.

Every entry is a real, verifiable behavior of a language/tool/spec — not a
"gotcha" that's actually disputed or version-dependent in a way that would
make the "real" answer arguable. Picked for being genuinely surprising
(good bluffing material) while staying unambiguous, since this answer gets
shown to players as ground truth.

Each question's "answer" is written the way a human would type it as a
quick, confident reply — short, specific, no hedging — so it doesn't stick
out from the player-written bluffs sitting next to it.
"""

QUESTIONS = [
    # JavaScript
    {"q": "In JavaScript, what does `[] + []` evaluate to?", "a": "An empty string \"\""},
    {"q": "In JavaScript, what does `typeof NaN` return?", "a": "\"number\""},
    {"q": "In JavaScript, what does `typeof null` return?", "a": "\"object\""},
    {"q": "In JavaScript, what does `0.1 + 0.2 === 0.3` evaluate to?", "a": "false"},
    {"q": "In JavaScript, what does `[] == false` evaluate to?", "a": "true"},
    {"q": "In JavaScript, what does `NaN === NaN` evaluate to?", "a": "false"},
    {"q": "In JavaScript, what does `'5' + 3` evaluate to?", "a": "\"53\""},
    {"q": "In JavaScript, what does `'5' - 3` evaluate to?", "a": "2"},
    {"q": "In JavaScript, what does `console.log(3 > 2 > 1)` print?", "a": "false"},
    {"q": "In JavaScript, what does `Array(3).length` return?", "a": "3"},
    {"q": "In JavaScript, what does `typeof []` return?", "a": "\"object\""},
    {"q": "In JavaScript, what does `1 + '1' + 1` evaluate to?", "a": "\"111\""},

    # Python
    {"q": "In Python, does `list.sort()` return the sorted list or `None`?", "a": "None (it sorts in place)"},
    {"q": "In Python, what does `print(0.1 + 0.2)` output?", "a": "0.30000000000000004"},
    {"q": "In Python, what does `bool('False')` evaluate to?", "a": "True"},
    {"q": "In Python, what does `[1, 2, 3] * 2` evaluate to?", "a": "[1, 2, 3, 1, 2, 3]"},
    {"q": "In Python, what does `True == 1` evaluate to?", "a": "True"},
    {"q": "In Python, what does `round(2.5)` return?", "a": "2"},
    {"q": "In Python, what does `-5 % 3` evaluate to?", "a": "1"},
    {"q": "In Python, does the `is` operator check value equality or identity?", "a": "Identity"},
    {"q": "In Python, what type does `1 / 2` return (Python 3)?", "a": "float (0.5)"},
    {"q": "In Python, what does `[] is []` evaluate to?", "a": "False"},
    {"q": "In Python, what does `len({1, 1, 2, 2, 3})` evaluate to?", "a": "3"},
    {"q": "In Python, what does `'abc'[::-1]` evaluate to?", "a": "\"cba\""},

    # SQL
    {"q": "In SQL, does `NULL = NULL` evaluate to TRUE?", "a": "No, it evaluates to NULL"},
    {"q": "In SQL, does `COUNT(*)` count rows where a given column is NULL?", "a": "Yes"},
    {"q": "In SQL, does `UNION` remove duplicate rows by default?", "a": "Yes (UNION ALL does not)"},
    {"q": "In SQL, does `ORDER BY` run before or after `SELECT DISTINCT`?", "a": "After"},

    # HTTP
    {"q": "What HTTP status code officially means \"I'm a teapot\"?", "a": "418"},
    {"q": "Is the HTTP PATCH method guaranteed to be idempotent by spec?", "a": "No"},
    {"q": "What does HTTP status 429 mean?", "a": "Too Many Requests"},
    {"q": "What does HTTP status 451 mean?", "a": "Unavailable For Legal Reasons"},
    {"q": "Is a 301 redirect meant to be permanent or temporary?", "a": "Permanent (302 is temporary)"},

    # Git
    {"q": "Does `git branch -d` delete a branch that has unmerged changes?", "a": "No, it refuses (use -D to force)"},
    {"q": "Does `git pull` run as a single git operation or two combined ones?", "a": "Two: fetch then merge (or rebase)"},
    {"q": "Does `git stash` include untracked new files by default?", "a": "No, unless you pass -u"},
    {"q": "Does `git commit --amend` change the commit hash?", "a": "Yes"},

    # Misc / Bash / Regex / CSS
    {"q": "In Bash, what does `echo $((5/2))` output?", "a": "2"},
    {"q": "In regex, does `.` match a newline character by default?", "a": "No"},
    {"q": "In CSS, does `z-index` apply to an element with `position: static`?", "a": "No"},
    {"q": "In HTML, does the browser collapse multiple consecutive spaces into one by default?", "a": "Yes"},
    {"q": "Does `localStorage` data in a browser survive closing the tab?", "a": "Yes"},
    {"q": "Does `sessionStorage` data survive closing the tab?", "a": "No"},
]
