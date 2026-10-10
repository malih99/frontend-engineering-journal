# Setup (Ubuntu 24.04)

## 1. Tools

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip gh
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
gh auth login                     # GitHub.com, HTTPS, browser login
```

## 2. Project

```bash
mkdir -p ~/projects && cd ~/projects
git clone https://github.com/malih99/frontend-engineering-journal.git
cd frontend-engineering-journal
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Ubuntu 24.04 blocks system-wide `pip install`, so always work inside the virtual environment.

## 3. Verify

```bash
ruff check . && pytest -q
journal validate
journal serve                     # open http://127.0.0.1:8000
```

## 4. Daily shortcut

Add this function to `~/.bashrc`, then run `source ~/.bashrc`:

```bash
jr() {
  cd ~/projects/frontend-engineering-journal || return
  source .venv/bin/activate
  git pull --rebase
  journal new
}
```

## 5. GitHub settings (once)

Let the Actions bot commit the README dashboard:

```bash
gh api -X PUT repos/malih99/frontend-engineering-journal/actions/permissions/workflow \
  -f default_workflow_permissions=write
```

Keep the repository private once you are done checking it: it holds your logs and mistakes.
