# group-chat-summarizer

**Let a lazy sloth read your group chats overnight so you don't have to.**

> *"Slow and steady wins the morning."* 🦥

A fully local, privacy-first CLI tool that reads exported WhatsApp and Telegram group chats and produces a two-line summary of each conversation — powered by open-weight models through [Ollama](https://ollama.com). No API keys, no cloud, no data leaves your machine.

Built for the [DEV.to "Slow and Steady" challenge](https://dev.to/challenges/open-weight) — build something with open-weight models that rewards laziness.

---

## Demo

```
$ summarize run

Summarizing work_project_chat.txt (15 new messages)...
Summarizing hiking_group_chat.json (11 new messages)...

╭──────────────────────────────╮
│   Group Chat Digest          │
│       slow and steady        │
╰──────────────────────────────╯

>> Hiking Group Chat

Summary:
The group planned a Ridge Loop hike for Sunday with a 7:30 AM carpool from Main St.
Mood is enthusiastic; logistics are locked in with snacks, water, and sunscreen covered.

Action items:
- Meet 7:30 AM at Main St coffee shop (Sunday)
- Marco drives, Lena brings snacks, Sam brings water

>> Work Project Chat

Summary:
Team coordinated slides for a 3 PM project meeting: Charlie did intro, Dave sent budget data, Bob finalized.
All slides uploaded to shared drive by evening; team is confident and ready.

Action items:
- Project meeting at 3 PM (Jan 16)

[OK] Digest saved to digests/2026-10-25.md
```

---

## Quick Start

### 1. Install Ollama

Download from [ollama.com](https://ollama.com/download), then start it:

```bash
ollama serve
```

### 2. Pull a model

Any small open-weight model that fits in ~6 GB VRAM works:

```bash
ollama pull qwen2.5:3b       # default, fast and capable
# or: ollama pull llama3.2:3b
# or: ollama pull phi3:mini
```

### 3. Clone and install the summarizer

```bash
git clone https://github.com/priyansh07-svnit/group-chat-summrizer.git
cd group-chat-summrizer
pip install .

# or in development mode:
pip install -e ".[dev]"
```

### 4. Add your chats

Export chats from WhatsApp or Telegram and drop them into `./chats/`:

- **WhatsApp**: Open a chat → ⋮ → More → Export chat → Without media → save the `.txt` file
- **Telegram**: Settings → Advanced → Export → JSON format → save the `result.json` file

Or try it immediately with the included examples:

```bash
cp examples/* chats/
```

### 5. Run

```bash
summarize run
```

That's it. Your digest appears in the terminal and is saved to `digests/YYYY-MM-DD.md`.

---

## CLI Commands

| Command                    | Description                                                |
| -------------------------- | ---------------------------------------------------------- |
| `summarize run`            | Process all chats and print the digest                     |
| `summarize watch`          | Continuously watch for new chats (Ctrl+C to stop)          |
| `summarize install-schedule` | Print a nightly schedule command (cron or Task Scheduler) |
| `summarize check`          | Verify Ollama is running and the model is pulled           |

All commands accept `--config path/to/config.yaml` to use a custom configuration.

---

## Configuration

Edit `config.yaml` in the project root:

```yaml
# Ollama settings
ollama:
  base_url: "http://localhost:11434"
  model: "qwen2.5:3b"         # swap any Ollama-compatible model
  timeout: 120

# Folders
chats_dir: "./chats"
digests_dir: "./digests"

# Summarization
summary:
  chunk_size: 3000             # max chars per chunk (map-reduce for longer chats)
  prompt_file: "./prompts/summary.txt"

# Watch mode
watch:
  interval_seconds: 300        # 5 minutes
```

### Swapping models

Change one line in `config.yaml`:

```yaml
ollama:
  model: "llama3.2:3b"
```

Then pull it: `ollama pull llama3.2:3b`. Done.

---

## Scheduling Nightly Runs

### Linux / macOS (cron)

```bash
summarize install-schedule --hour 6 --minute 30
# prints:  30 6 * * * /usr/bin/python -m chat_summarizer run
# add it:  crontab -e
```

### Windows (Task Scheduler)

```bash
summarize install-schedule --hour 7
# prints:  schtasks /create /tn "GroupChatSummarizer" /tr "..." /sc daily /st 07:00 /f
# run in an elevated terminal
```

---

## How It Works

1. **Parse**: WhatsApp `.txt` and Telegram `result.json` files are parsed into a common `Message(timestamp, sender, text)` dataclass. Media placeholders and system messages are filtered out.

2. **Incremental processing**: A `.state.json` file tracks the last-processed timestamp per chat, so each run only summarizes *new* messages.

3. **Chunk & summarize**: If a chat exceeds the configured chunk size, it's split and summarized with a **map-reduce** strategy — each chunk is summarized individually, then the chunk summaries are combined into one final summary.

4. **Output**: Each chat gets a strict two-line summary plus optional action items. The prompt template lives in `prompts/summary.txt` and is fully editable.

5. **Digest**: A Markdown file is written to `digests/YYYY-MM-DD.md`, and a rich-formatted version prints in the terminal.

---

## Editing the Prompt

The prompt template is a plain text file at `prompts/summary.txt`. Edit it to change the summary style, length, language, or focus. The chat messages are appended after the template.

---

## Project Structure

```
group-chat-summarizer/
  config.yaml               # user configuration
  pyproject.toml             # Python packaging
  prompts/summary.txt        # editable prompt template
  examples/                  # fake chats to try immediately
  src/chat_summarizer/
    cli.py                   # typer CLI (run, watch, check, install-schedule)
    config.py                # YAML config loader
    digest.py                # Markdown + terminal output
    ollama_client.py         # localhost-only Ollama HTTP client
    state.py                 # incremental processing state
    summarizer.py            # chunking + map-reduce summarization
    parsers/
      models.py              # Message dataclass
      whatsapp.py            # WhatsApp .txt parser
      telegram.py            # Telegram result.json parser
      auto.py                # format auto-detection
  tests/                     # pytest suite (41 tests)
  chats/                     # (git-ignored) drop your exports here
  digests/                   # (git-ignored) daily summaries appear here
```

---

## Privacy

- **No network calls** except to `localhost` (Ollama). A test (`test_privacy.py`) scans the entire source tree and **fails if any non-localhost URL appears** in runtime code.
- **`chats/` and `digests/` are git-ignored** — personal data is never committed.
- The Ollama client **refuses to connect** to any non-localhost URL at runtime.

---

## Development

```bash
pip install -e ".[dev]"
pytest -v
```

### Design decisions

- **No async**: The tool runs overnight; simplicity beats throughput.
- **Character-based chunking**: A conservative proxy for tokens that works across models without a tokenizer dependency.
- **Rich for terminal output**: Pretty panels and Markdown rendering with zero configuration.
- **Typer for CLI**: Auto-generated help, type safety, minimal boilerplate.

---

## Why Open-Source / Open-Weight Matters Here

| Principle | How this project embodies it |
|-----------|------------------------------|
| **Runs fully offline** | Everything happens on your laptop. No internet needed after pulling the model. |
| **Chat data never touches a third-party server** | The Ollama client hard-refuses non-localhost connections. A failing test enforces this. |
| **Model is swappable** | Change one line in `config.yaml`. Any Ollama-compatible model works. |
| **Zero running cost** | No API bills, no subscriptions, no quotas. Just your hardware. |
| **Auditable** | Open-source code + open-weight model = you can inspect everything. |

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built with patience by a very lazy sloth.* 🦥
