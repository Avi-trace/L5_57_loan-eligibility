# Lab 5 Reflection (DRAFT)

> The handout's four questions were not in the material I had, so the headings below are my guess at common themes. Replace each heading with the handout's exact question, keep whichever points answer it, and rewrite in your own words before submitting.

## 1. What did the tools catch, and what did they miss?

Pylint, Flake8 and Bandit found the style problems, the unsafe patterns (`marshal`, FTP, a hardcoded password, `subprocess`, `random`) and the resource leaks. They found **none** of the bugs that make the program give wrong answers. Pylint's score went from 5.17 to 10.00 and Bandit's findings from 8 to 0, but every wrong number in the demo came from reading the output and checking it by hand:

- EMI of 375,000 instead of 10,379 (rate unit mismatch)
- Max loan of 900,000 instead of about 722,600 (interest ignored)
- Interest saved of 62,275 instead of 12,275 (prepaid principal counted as interest)
- A score of 950 rated `"LOW"`
- A `"crypto"` loan and a FOIR-0.8 applicant both approved

A tool can only flag patterns it knows. It cannot know that a bank's EMI should be about 2 % of the loan, so a clean report is not proof that the code is correct.

## 2. How did you decide what to fix first?

I ranked by the damage a bug could do, not by how many messages it produced:

1. Logic bugs that approve loans wrongly or compute money wrongly (rows 1-3, 7): direct financial loss for the bank.
2. Security issues that expose data or credentials (rows 4-6).
3. Robustness and data-loss bugs (rows 9-12).
4. Style, naming and docstrings, which make up most of the message count but carry the least risk.

This is why the Pylint score is a poor priority list: 32 of its 43 messages were style or naming.

## 3. Were any findings false positives, or hard to fix cleanly?

Bandit still blacklists the whole `ftplib` module, even when FTPS is used correctly. I switched to `FTP_TLS` with an encrypted data channel and added `# nosec B402` with the reason in a comment. A `nosec` is only acceptable when it is justified in writing, and it should be reviewed, not used to silence a tool. The cleanest fix would be SFTP via a third-party library, which I did not add to avoid a new dependency.

The Pylint "too many arguments" message disappeared only because the `history` parameter was dead code. The naming warnings (C0103) were pure style, but they matter once other code imports these functions, because renaming later breaks callers.

## 4. How would you use static analysis in a real project?

- Run all three tools automatically (pre-commit hook and CI) so problems are caught before review, not in a lab at the end.
- Fail the build on Bandit High/Medium findings. Treat Pylint style messages as advisory.
- Pair the tools with unit tests. The wrong EMI and max-loan figures would be caught by a test that compares against a known value, which is how I verified the fixes.
- Keep secrets in environment variables or a secrets manager, never in source control.
