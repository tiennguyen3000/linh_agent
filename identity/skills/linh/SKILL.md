---
name: linh
description: "Use when operating, extending, or troubleshooting Linh — the user's own agent. Commands, home layout, engineering agents, rebrand layer."
version: 1.0.0
author: Linh Nguyen
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [linh, identity, agents, rebrand, cli, team, engineering]
---

# Linh — Personal AI Engineering Agent

Linh is the personal AI engineering agent of Linh Nguyen.
It runs on the Hermes core architecture (Nous Research) but is an independent
distribution: own command, own home, own identity, own team of engineering agents.

## Layout

```
~/Linh/                 # the distribution
├── core/               # forked core source (runtime) — patched via scripts/rebrand_core.py
├── linh/               # the `linh` CLI package (dispatch + passthrough)
├── identity/           # SOUL.md, AGENTS.md, agents/*.md, skins/, skills/
├── bin/linh            # launcher
├── scripts/            # clone → rebrand → venv → seed → verify (re-runnable)
├── patches/            # diff + manifest of every core edit
├── venv/               # Linh's own runtime (independent of ~/.hermes)
└── docs/               # ARCHITECTURE, LINH-IDENTITY, REBRAND, AGENT-ROLES

~/.linh/                # data home (LINH_HOME)
├── config.yaml .env    # settings / secrets (inherited from the Hermes home at seed time)
├── SOUL.md AGENTS.md   # persona + repo rules
├── agents/*.md         # the 6 engineering-agent charters
├── skins/linh.yaml     # Linh branding (active skin)
├── skills/ memory/     # capability + memory
└── state.db logs/ sessions/
```

## Repo GitHub

`~/Linh` là git repo, remote `origin` = `https://github.com/tiennguyen3000/linh_agent` (**private**, nhánh `main`).
Chi tiết cần nhớ khi push:

- Repo giờ có **2 nhánh**: `main` = lớp Linh (29 file: `identity/`, `linh/`, `bin/`, `scripts/`,
  `patches/`, `docs/`), `core` = runtime Hermes core đã áp bản sắc (push từ `git -C core push
  <repo> main:core`, root commit riêng, 69MB pack). `.gitignore` loại trừ `core/` và `venv/` —
  `core/` có git repo riêng (remote `upstream` = NousResearch/hermes-agent).
- **Cài trên máy mới**: `git clone --single-branch --branch main <repo> ~/Linh && bash ~/Linh/scripts/install.sh`
  (6 bước, tự lấy nhánh `core`). Cờ hay dùng: `--from-hermes` (copy core+venv từ `~/.hermes`),
  `--mode git|local|auto` (nguồn core), `--venv-mode auto|clone|fresh` (nguồn venv),
  `--extras`/`--with-dev`, `--no-link`, `--skip-verify`. Chi tiết: `docs/INSTALL.md`.
- **Test lại đường cài mà không phá máy thật**: clone repo vào `/tmp/linh-fresh`, chạy
  `LINH_HOME=/tmp/linh-home-test bash /tmp/linh-fresh/scripts/install.sh --dir /tmp/linh-fresh --mode git --venv-mode fresh --no-link`
  (nhớ `LINH_HOME` + `--no-link` để không ghi vào `~/.linh` và không đổi symlink `~/.local/bin/linh`).
- Auth: token trong macOS keychain (user `tiennguyen3000`, quyền admin/push) — `git push`
  chạy trực tiếp, không cần `gh auth login`.

## Commands

- `linh` — interactive session; `linh chat -q "<question>"` for one-shot.
- `linh identity` — identity card + home + team roster.
- `linh agents [role]` — list charters, or print one.
- `linh team <role> "<task>"` — delegate a task to code|debug|review|test|research|devops.
- `linh selfcheck` — end-to-end install verification.
- `bash scripts/sync_home.sh [--apply] [--overwrite] [--only skills|memories|plugins] [--show-extra]`
  — kéo skill/memory/plugin **mới** từ `~/.hermes` sang `~/.linh` (seed chỉ copy 1 lần lúc cài;
  sau đó 2 home tách rời). Mặc định dry-run, không đè, không xoá, không đụng `skills/linh`.
  Phân loại NEW/DIFF bằng 1 pass dry-run rồi mới copy — cần vì rsync của macOS là openrsync
  (không có `+` trong itemize code, và nếu copy trước khi phân loại thì file mới thành DIFF).
- Everything else (`gateway`, `cron`, `config`, `tools`, `doctor`, …) passes
  straight through to the core CLI; capability is not reduced.

## Pitfalls (đã trả giá)

- **`linh_branding.py` không có trong tree Hermes gốc** → rebuild từ `~/.hermes` (hoặc clone
  nhánh `core` cũ) chết ở gate `branding import`. Bản canonical nằm ở `patches/linh_branding.py`,
  `rebrand_core.py` tự tạo/refresh vào core. Thêm identity mới thì copy ngược lại vào `patches/`.
- **Seed kế thừa `config.yaml` từ `~/.hermes` → `display.skin: default`**, mất skin Linh và
  `linh selfcheck` fail. `seed_home.py` giờ luôn chạy `linh config set display.skin linh` sau khi
  seed (idempotent).

- **`LINH_HOME` trong terminal của Linh thắng `HERMES_HOME`.** Runtime Linh export `LINH_HOME`,
  và patch trong `hermes_constants.get_hermes_home()` cho `LINH_HOME` ưu tiên cao hơn
  `HERMES_HOME`. Hệ quả: mọi lệnh chạy qua terminal tool thừa hưởng `LINH_HOME=$HOME/.linh`;
  `HERMES_HOME=/tmp/x python3 -c "...save_config()"` vẫn ghi vào home THẬT. Muốn cô lập để thử
  nghiệm thì set cả hai (`LINH_HOME=/tmp/probe HERMES_HOME=/tmp/probe`), hoặc `unset LINH_HOME`.
- **Không bao giờ chạy code ghi config của core trên home thật để "probe".** Đã từng ghi đè
  `~/.linh/config.yaml` bằng `save_config(DEFAULT_CONFIG)` → mất `model`, telegram prompts,
  plugins, `display.skin` (skin check fail). Khôi phục: `cp ~/.hermes/config.yaml ~/.linh/config.yaml`
  rồi `linh config set display.skin linh` (vì bản Linh khác bản Hermes đúng ở key này).
- **Tool `patch` từ chối sửa file config** (`Refusing to write to Hermes config file`) — sửa
  config bằng `linh config set <key> <value>`, không sửa tay.
- Bootstrap python của `rebuild.sh`/`install.sh` đã bỏ hard-code `~/.hermes/.../venv/bin/python3`:
  giờ tự dò `python3.12|3.11|3.13|python3` (>=3.8). Venv mới cần CPython 3.11–3.13
  (core `requires-python = ">=3.11,<3.14"`; macOS mặc định 3.9.6, Homebrew có 3.12/3.14).

## Rules that matter here

- `core/` is the live runtime: never hand-edit it. Add the edit to
  `scripts/rebrand_core.py`'s manifest (idempotent, fails loudly on a stale anchor),
  re-run it, then run `scripts/verify.sh`.
- After merging upstream core changes, re-run `scripts/rebrand_core.py` to re-apply
  the identity layer; `patches/rebrand.patch` shows exactly what is Linh-specific.
- Internal module names (`hermes_cli`, `hermes_state`) and `HERMES_*` env vars stay
  as-is on purpose: they are the runtime API. Only the identity surface is renamed.
- Prefer adding capability in `~/Linh/linh` (CLI/skill/plugin) over touching core.
