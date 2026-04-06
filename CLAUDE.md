# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MeSpam is a single-file Python script (`mespam.py`) that connects to IMAP mailboxes and moves spam emails to a spam folder. It targets a specific spam pattern: emails that appear to come from your own address and contain links to `https://storage.googleapis.com`.

## Running

```bash
# Process all configured mailboxes
python3 mespam.py

# Process a specific mailbox by name (key from mailboxes.yml)
python3 mespam.py john
```

## Architecture

- **`mespam.py`** — Single module containing the `MeSpamFilter` class. Reads `mailboxes.yml` on init, connects via IMAP, scans inbox emails, and moves matches to the configured spam folder.
- **`mailboxes.yml`** — YAML config with mailbox credentials and IMAP settings. Each entry has: `email`, `password`, `imap-host`, `spam-folder`.

## Dependencies

- Python >= 3.10
- `pyyaml` (the `yaml` package) — only external dependency
- Standard library: `imaplib`, `email`, `re`, `sys`

## Key Details

- The script uses non-SSL IMAP (`imaplib.IMAP4`, not `IMAP4_SSL`)
- `mailboxes.yml` contains credentials — never commit real passwords
- The spam detection is intentionally narrow: matches only emails where From == the mailbox email AND body contains `https://storage.googleapis.com`
