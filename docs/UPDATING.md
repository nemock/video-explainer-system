# Keeping the explainer-system up to date

This project is actively maintained. Updates ship as commits to `main` and occasionally as [releases](https://github.com/nemock/video-explainer-system/releases).

## Manual updates

```bash
cd ~/projects/video-explainer-system
git pull origin main
```

The `/explainer` skill reads from the repo's files on disk, so updates take effect immediately on the next invocation.

---

## Automatic update alerts (optional)

If you'd like a heads-up when new commits land, set up a shell hook that runs whenever you open a terminal:

### For zsh users (Oh My Zsh)

Create a precmd hook in `~/.oh-my-zsh/custom/hooks/explainer-check-updates.sh`:

```bash
#!/bin/zsh
source /path/to/repo/bin/check-updates.sh
```

Then add to `~/.zshrc` (after `source $ZSH/oh-my-zsh.sh`):

```bash
precmd() {
  source ~/.oh-my-zsh/custom/hooks/explainer-check-updates.sh
}
```

### For bash users

Add to `~/.bashrc`:

```bash
# Explainer system update check
source /path/to/repo/bin/check-updates.sh
```

### For other shells (fish, dash, etc.)

Add to your shell's initialization file:

```bash
source /path/to/repo/bin/check-updates.sh
```

---

## GitHub notifications

Prefer email alerts? Watch the repository on GitHub:

1. Go to https://github.com/nemock/video-explainer-system
2. Click **Watch** (top-right)
3. Select **Releases**

GitHub will email you when a new release ships.

---

## How it works

`bin/check-updates.sh` is a portable shell script (works on bash, zsh, dash, fish) that:
- Fetches updates from `origin` (silent)
- Checks if your local branch is behind `origin/main`
- Prints a yellow alert **only if** unpulled commits exist
- Exits silently if repo is current or unavailable

It's safe to source repeatedly — no performance impact if the repo is current.
