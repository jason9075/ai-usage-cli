# Agent Notes for ai-usage-cli

## Setting up multiple Codex accounts on one machine

Use this when the user wants several OpenAI Codex accounts (for example a
personal one and a work one) side by side, each shown as its own entry in
`ai-usage`.

### How it works

The Codex CLI keeps all of its state (login in `auth.json`, `config.toml`,
history, sessions, sqlite databases, skills, plugins) in one directory. The
default is `~/.codex`, and the `CODEX_HOME` environment variable overrides it.
Pointing `CODEX_HOME` at a different directory per account gives fully
isolated accounts while sharing a single Codex binary.

### Step 1: Shell wrappers (one per account)

Back up the shell rc file first, for example
`cp ~/.zshrc ~/.zshrc.backup-codex-accounts-$(date +%Y%m%d-%H%M%S)`.
Then append one function per account to `~/.zshrc` (or `~/.bashrc`):

```zsh
# Separate Codex accounts.
codex-<name>() {
  mkdir -p "$HOME/.codex_<name>" || return
  CODEX_HOME="$HOME/.codex_<name>" "$HOME/.local/bin/codex" "$@"
}
```

- Replace `<name>` with a short label for each account (`work`, `personal`, ...).
- Use the absolute path to the real `codex` binary (check with
  `command -v codex`; it is often `~/.local/bin/codex`). Using the absolute
  path avoids recursion if a wrapper is ever named `codex`.
- `mkdir -p` creates the directory on first use; `|| return` stops if that fails.
- `"$@"` forwards all arguments, so `codex-<name> login`,
  `codex-<name> exec "..."` and so on work as normal.

### Step 2: Log in each account once

```sh
source ~/.zshrc
codex-<name> login
```

Repeat for every account. Each login writes its own
`~/.codex_<name>/auth.json`.

### Step 3: Tell ai-usage about the accounts

Edit `~/.codexbar/config.json` and add `accounts` to the `codex` provider:

```json
"codex": {
  "enabled": true,
  "accounts": [
    {"name": "codex-work", "home": "~/.codex_work"},
    {"name": "codex-personal", "home": "~/.codex_personal"}
  ]
}
```

- `ai-usage -p codex` queries every configured account;
  `ai-usage -p codex-work` queries just one.
- Each account reads and refreshes only the `auth.json` in its own `home`.
- Without `accounts`, the provider uses `$CODEX_HOME`, or `~/.codex` if that is unset.
- The lookup is implemented in `ai_usage/providers/codex.py`.

### Caveats

- Plain `codex` (no wrapper) still uses `~/.codex`, which is a separate third
  login and config.
- Each account has its own `config.toml`. Settings such as the model or trusted
  projects are not shared, so change them in each home if needed.
- Every wrapper runs the same binary, so upgrading Codex once upgrades all
  accounts.

### Security rules for agents

- Never print, copy, commit, or paste the contents of any `auth.json`, tokens,
  or API keys. Check whether a file exists (`test -f`) without reading it.
- Never put real email addresses or account identifiers in this repo. Use
  placeholder names like the ones above.
- Do not commit anything from `~/.codex*` or `~/.codexbar/` into the repo.
