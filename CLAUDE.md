# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MeSpam is a single-file Python script (`mespam.py`) that connects to IMAP mailboxes and moves spam emails to a spam folder. Spam is identified by configurable patterns; the original target was emails that appear to come from your own address and contain links to `https://storage.googleapis.com`.

## Running

```bash
# Process all configured mailboxes
python3 mespam.py

# Process a specific mailbox by name (key from mailboxes.yml)
python3 mespam.py john
```

## Architecture

- **`mespam.py`** — Single module containing the `MeSpamFilter` class. Reads `mailboxes.yml` on init, connects via IMAP, scans inbox emails, and moves matches to the configured spam folder.
- **`mailboxes.yml`** — YAML config with mailbox credentials and IMAP settings. Each entry has: `email`, `password`, `imap-host`, `spam-folder`, and optionally its own `patterns`.

## Dependencies

- Python >= 3.10
- `pyyaml` (the `yaml` package) — only external dependency
- Standard library: `imaplib`, `email`, `codecs`, `re`, `sys`

## Key Details

- The script connects with `imaplib.IMAP4_SSL`
- Candidates are found with server-side IMAP `SEARCH` built from each pattern, verified locally, then moved with `UID MOVE` (falling back to `COPY` + `UID EXPUNGE`); messages are never re-uploaded
- `mailboxes.yml` contains credentials — never commit real passwords
- Spam detection is driven by `patterns` in `mailboxes.yml` (global, or per mailbox). A message is spam if it matches ALL conditions of ANY pattern. Conditions: `from-is-self`, `sender-auth-fails`, `body-contains`, `body-matches`, `subject-contains`, `subject-matches`
