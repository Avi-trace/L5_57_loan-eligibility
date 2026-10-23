# Lab 5 Reflection: Static Code Analysis

**Name:** Avyukt Ranjan  **SRN:** PES1UG24AM060  **Repo:** L5_57_loan-eligibility (`loan_calculator.py`)

## Q1. What is the purpose and scope of static code analysis, and what does each of the three tools check?

Static analysis examines source code without running it, to find bugs, vulnerabilities and style violations early and cheaply. Each tool covers a different slice:

- **Pylint** is the strict code reviewer. It checks code quality and design: naming, missing docstrings, unused imports and variables, dangerous defaults, resource handling.
- **Flake8** is the grammar checker. It enforces PEP 8 formatting: blank lines, line length, whitespace, unused imports.
- **Bandit** is the security guard. It flags insecure patterns: unsafe deserialisation, plaintext protocols, hardcoded passwords, weak randomness, shell and subprocess use.

On my file the three tools reported 43 Pylint messages (score 5.17/10), 22 Flake8 messages and 8 Bandit findings (2 High, 1 Medium, 5 Low).

## Q2. Which issues did you find and fix, and how did you prioritise them by severity?

I fixed far more than the required four, in three commits (one per tool).

**Bandit (security).**
- `marshal` deserialisation (B302, Medium) replaced with JSON.
- Plain FTP (B402/B321, High) replaced with FTPS (`FTP_TLS` with an encrypted data channel).
- The hardcoded password (B107) removed and read from environment variables instead.
- `subprocess` call to `mail` (B404/B603/B607) replaced with `smtplib`.
- `random` for application IDs (B311) replaced with `secrets`.

**Pylint (quality and logic).**
- The mutable default argument `history=[]` removed. It was shared across calls and grew forever.
- Files opened without `with`.
- camelCase function names changed to snake_case, and docstrings added.
- The `global` statement, an unused import and an unused variable cleaned up.
- A demo that ran on import now sits behind `if __name__ == "__main__":`.

**Flake8 (formatting).** Blank lines, line length (79), an unused import and an f-string with no placeholders.

I prioritised by the damage a problem could do: logic errors that approve loans or compute money wrongly, then security issues, then robustness, then style. The Pylint score is not a priority list, because 32 of its 43 messages were style or naming.

## Q3. What did the tools miss, and how did you find those problems?

None of the tools flagged the bugs that made the program give wrong answers. I found them by reading the demo output and checking it by hand:

- The EMI printed 375,000 instead of 10,379.18. The rate unit was inconsistent (`9` passed where `0.09` was expected).
- Eligibility returned `True` for an applicant with a FOIR of 0.8 (limit 0.5) and for the unsupported loan type "crypto". A shortcut (`credit_score > 750 or income > 25000`) skipped the mandatory checks.
- The maximum loan was 900,000 instead of about 722,600, because the code ignored interest.
- Interest saved was 62,275 instead of 12,275, because the prepaid principal was counted as interest.
- A credit score of 950 was rated LOW instead of INVALID.
- Saved loan records were overwritten on every run.

A clean report is not proof of correct behaviour. The tools only know patterns, not what a correct EMI should be.

## Q4. How has static analysis contributed to code quality and maintainability, and how would you use it in future?

Static analysis gave me a measurable, repeatable review: Pylint went from 5.17 to 10.00, Flake8 from 22 messages to 0, and Bandit from 8 findings to 0. The result is code that is safer, easier to read and easier to change. The one exception is a justified `# nosec B402` on the FTPS import, because Bandit blacklists the whole `ftplib` module even when TLS is used. SFTP would be the ideal replacement, but it needs a third-party library.

In future projects I would:
- Run all three tools automatically (pre-commit hook and CI), and fail the build on Bandit High and Medium findings.
- Treat Pylint style messages as advisory, ranked below logic and security problems.
- Pair the tools with unit tests, because the wrong EMI and loan figures above would be caught by tests against known values, not by a linter.
- Keep secrets in environment variables or a secrets manager, never in source code.
