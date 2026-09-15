# Linh — kiến trúc hệ thống (bản đồ thật, đo từ code)

Tài liệu này là Phase 0–1 của quá trình clone/rebuild: bản đồ kiến trúc của hệ thống
nguồn (Hermes Agent v0.21.1) **đo trực tiếp từ code**, kèm ghi chú Linh giữ/đổi gì.

Bản gốc: `/Users/tiennk/.hermes/hermes-agent` (git install, upstream `a55c972e`,
local `ee35a462`, +65 carried commits). Bản Linh: `/Users/tiennk/Linh/core`.

## 1. Điểm vào & vòng lặp agent

```
~/.local/bin/linh                      # launcher Linh (bash) — set LINH_HOME/HERMES_HOME
└── Linh/bin/linh_entry.py             # python entry (sys.path = core/ + Linh/)
    └── linh/cli.py:main()             # dispatch lệnh Linh-native; còn lại passthrough
        └── os.execv(venv/bin/hermes)  # argv[0]="linh" → core CLI, giữ nguyên fidelity
            └── hermes_cli.main():main
                └── cli.py: HermesCLI (REPL, slash dispatch)
                    └── run_agent.py: AIAgent (facade)
                        └── agent/turn_*.py (27 file) — vòng lặp một lượt
```

`agent/` (224 file) chứa vòng lặp tách theo giai đoạn: `turn_preflight`, `turn_api_request`,
`turn_api_call`, `turn_tool_round`, `turn_retry_state`, `turn_overflow`,
`turn_context_compaction`, `turn_finalizer`, `turn_usage`, … Facade + sibling: sửa hành vi thì
tìm `agent/<stem>_<topic>.py`, không đọc facade trước (tốn context).

## 2. Tool & schema

| Thành phần | Vị trí | Ghi chú |
|---|---|---|
| Registry + auto-discovery | `tools/registry.py` | không phụ thuộc gì; `tools/*.py` tự đăng ký khi import |
| Tool implementations | `tools/` — **253 file** | terminal backend ở `tools/environments/` (local, docker, ssh, modal, daytona…) |
| Toolset & core schema | `toolsets.py`, `toolset_distributions.py` | `_HERMES_CORE_TOOLS` = tập tool gửi mọi request |
| Orchestration | `model_tools.py`, `model_tools_connectors.py` | `discover_builtin_tools()`, `handle_function_call()` |

Nguyên tắc thiết kế (từ `AGENTS.md` upstream): **core là eo hẹp** — mọi tool core đều phải trả phí
trên mỗi API call, nên năng lực mới đi theo thang: sửa code sẵn có → CLI + skill →
tool gated (`check_fn`) → plugin → MCP server → (cuối cùng) tool core mới.

## 3. Đa agent & song song

| Năng lực | Vị trí |
|---|---|
| Delegate task | `tools/delegate_tool.py::delegate_task`, `agent/subagent_lifecycle.py`, `agent/delegation_context.py` |
| Batch song song | `batch_runner.py` |
| Cron/scheduler | `cron/` (24 module: `jobs.py`, `scheduler.py`, `scheduler_delivery.py`, ledger, incidents…) |
| Kanban dispatcher | `hermes_cli/kanban*.py` (14 file), `tools/kanban_tools.py`, `plugins/kanban/` |
| Gateway đa nền tảng | `gateway/run.py` (facade + 15 sibling), `gateway/platforms/` — **30 adapter** |

## 4. Context, prompt, memory

| Thành phần | Vị trí |
|---|---|
| System prompt 3 tầng (stable/context/volatile) | `agent/system_prompt.py` — `build_system_prompt_parts()` |
| Identity mặc định | `agent/prompt_builder.py::DEFAULT_AGENT_IDENTITY` ← **Linh đã sửa** |
| Guidance tự-tri-thức | `HERMES_AGENT_HELP_GUIDANCE` (+ biến thể `_NO_SKILLS`) ← **Linh đã sửa** |
| Persona người dùng | `SOUL.md` (home), seed bởi `hermes_cli/default_soul.py` ← **Linh đã sửa** |
| Nén context | `agent/context_compressor*.py`, `trajectory_compressor.py`, `hermes_state_compression.py` |
| Memory | `plugins/memory/` — 10 backend (mem0, honcho, hindsight, supermemory, byterover…) |
| Bất biến prompt caching | prompt phải byte-stable suốt hội thoại; chỉ nén context được phép đổi |

## 5. Runtime, state, config

| Thành phần | Vị trí / giá trị |
|---|---|
| Home profile-aware | `hermes_constants.py::get_hermes_home()` — override context → `LINH_HOME` **(Linh thêm)** → `HERMES_HOME` → default |
| State store | `hermes_state.py` (facade + **21 sibling**) → `state.db` (SQLite + FTS5) |
| Logging | `hermes_logging.py` → `agent.log` / `errors.log` / `gateway.log` |
| Config | `~/.linh/config.yaml` (settings) + `.env` (secrets) |
| Branding/theme | `hermes_cli/skin_engine.py` — skin YAML ở `<home>/skins/`, có `branding{}`, `banner_logo`, `tool_prefix` |
| Banner | `hermes_cli/banner.py` — logo + `format_banner_version_label()` ← **Linh đã sửa** |
| Entry/version | `hermes_cli/__init__.py::__version__` (core version giữ nguyên) |

## 6. Build / test / deploy

- `pyproject.toml` (name `hermes-agent`, console scripts `hermes`, `hermes-agent`, `hermes-acp`).
- Test: **`scripts/run_tests.sh`** — KHÔNG dùng `pytest` trần: nó ép CI parity (bỏ credential,
  `TZ=UTC`, `HERMES_HOME` → temp dir, mỗi file một subprocess riêng). ~39k test / ~3.7k file.
- Docker: `Dockerfile`, `docker-compose.yml`. Nix: `flake.nix`. CI: `.github/`.
- Cài đặt: `setup-hermes.sh` / `install.sh` (uv + venv + launcher).

## 7. Kết quả Phase 0: cái gì sinh tự động, cái gì sửa được

| Nhóm | Sinh tự động / dẫn xuất | Sửa được an toàn |
|---|---|---|
| `venv/` | ✅ sinh bởi setup | không sửa tay (dùng `scripts/setup_venv.py`) |
| `node_modules/`, `__pycache__`, `*.pyc` | ✅ sinh | không |
| `state.db`, `logs/`, `sessions/`, `cache/` | ✅ runtime sinh | không (dữ liệu) |
| `patches/*` | ✅ sinh bởi `rebrand_core.py` | không (audit) |
| `hermes-agent.egg-info`, `__editable__*` | ✅ sinh bởi pip | không |
| `identity/*`, `linh/*`, `bin/*`, `scripts/*`, `docs/*` | ❌ người viết | ✅ sửa trực tiếp |
| `core/**` | ❌ người viết (upstream) | ⚠️ chỉ qua `scripts/rebrand_core.py` hoặc patch có ghi lại |

## 8. Quy mô rebrand (số liệu thật)

- **4264 file `.py`** chứa chuỗi `hermes`; **626 biến `HERMES_*`** unique.
- Xử lý: giữ nguyên tên module nội bộ + biến môi trường (là runtime API), chỉ đổi **bề mặt
  bản sắc** — 25 sửa đổi trên **11 file**. Chi tiết & lý do: `docs/REBRAND.md`.
- Kích thước fork: source 189 MB (không gồm `venv` 308 MB / `node_modules` 358 MB của bản gốc).
