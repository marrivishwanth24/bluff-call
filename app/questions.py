"""
questions.py — the curated question bank for Bluff Call.

Every entry is a real, verifiable behavior of a language/tool/spec — not a
"gotcha" that's actually disputed or version-dependent in a way that would
make the "real" answer arguable. Picked for being genuinely surprising
(good bluffing material) while staying unambiguous, since this answer gets
shown to players as ground truth.

Each question asks for a *specific value* ("what does X evaluate to / return
/ output"), never a bare yes/no judgment call. A bare "Yes"/"No" answer
sticks out immediately next to the more detailed bluffs players write for
it, which makes the real answer trivial to spot in voting and defeats the
whole bluffing mechanic — so every question here is phrased so its true
answer has the same shape a good bluff would have.

Each "answer" is written the way a human would type it as a quick,
confident reply — short, specific, no hedging — so it doesn't stick out
from the player-written bluffs sitting next to it.
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
    {"q": "In Python, what does `list.sort()` return?", "a": "None (it sorts the list in place)"},
    {"q": "In Python, what does `print(0.1 + 0.2)` output?", "a": "0.30000000000000004"},
    {"q": "In Python, what does `bool('False')` evaluate to?", "a": "True"},
    {"q": "In Python, what does `[1, 2, 3] * 2` evaluate to?", "a": "[1, 2, 3, 1, 2, 3]"},
    {"q": "In Python, what does `True == 1` evaluate to?", "a": "True"},
    {"q": "In Python, what does `round(2.5)` return?", "a": "2"},
    {"q": "In Python, what does `-5 % 3` evaluate to?", "a": "1"},
    {"q": "In Python, what does the `is` operator actually check?", "a": "Object identity, not value equality"},
    {"q": "In Python, what type does `1 / 2` return (Python 3)?", "a": "float (0.5)"},
    {"q": "In Python, what does `[] is []` evaluate to?", "a": "False"},
    {"q": "In Python, what does `len({1, 1, 2, 2, 3})` evaluate to?", "a": "3"},
    {"q": "In Python, what does `'abc'[::-1]` evaluate to?", "a": "\"cba\""},

    # SQL
    {"q": "In SQL, what does `NULL = NULL` evaluate to?", "a": "NULL (not TRUE)"},
    {"q": "In SQL, how many rows does `COUNT(*)` return for a 5-row table where 2 rows are all NULL?", "a": "5 (COUNT(*) counts every row, NULLs included)"},
    {"q": "In SQL, how many rows does `SELECT 1 UNION SELECT 1` return?", "a": "1 row (UNION drops duplicates; UNION ALL wouldn't)"},
    {"q": "In SQL's logical query processing order, which clause runs first: SELECT DISTINCT or ORDER BY?", "a": "SELECT DISTINCT"},

    # HTTP
    {"q": "What HTTP status code officially means \"I'm a teapot\"?", "a": "418"},
    {"q": "Per the HTTP spec, which method is guaranteed idempotent: PUT or PATCH?", "a": "PUT (PATCH is not guaranteed idempotent)"},
    {"q": "What does HTTP status 429 mean?", "a": "Too Many Requests"},
    {"q": "What does HTTP status 451 mean?", "a": "Unavailable For Legal Reasons"},
    {"q": "Is a 301 redirect meant to be permanent or temporary?", "a": "Permanent (302 is temporary)"},

    # Git
    {"q": "What happens when you run `git branch -d` on a branch with unmerged changes?", "a": "It refuses to delete it (use -D to force)"},
    {"q": "Does `git pull` run as a single git operation or two combined ones?", "a": "Two: fetch then merge (or rebase)"},
    {"q": "What flag does `git stash` need to include untracked files?", "a": "-u (untracked files are skipped by default)"},
    {"q": "What happens to a commit's hash after `git commit --amend`, even with no changes?", "a": "It always changes"},

    # Misc / Bash / Regex / CSS
    {"q": "In Bash, what does `echo $((5/2))` output?", "a": "2"},
    {"q": "What single character does `.` fail to match by default in regex?", "a": "A newline (\\n)"},
    {"q": "What `position` value makes `z-index` have no effect in CSS?", "a": "static (the default)"},
    {"q": "How many spaces does `<p>a    b</p>` actually render between a and b in HTML?", "a": "Just one (whitespace collapses by default)"},
    {"q": "Between localStorage and sessionStorage, which one survives closing the browser tab?", "a": "localStorage"},
    {"q": "What does Python's `is not` operator check?", "a": "That two objects are not the same object in memory"},
]
