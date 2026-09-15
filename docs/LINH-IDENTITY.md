# Linh — định nghĩa bản sắc

## Tên & ý nghĩa

**Linh** — Personal AI Engineering Agent của **Linh Nguyen**, chạy trên Hermes core
architecture (Nous Research). Không có expansion viết tắt: tên agent là "Linh".

```
Linh
Personal AI Engineering Agent

Owner: Linh Nguyen
Core : Hermes core architecture (Nous Research) — kế thừa, không phải bản sắc
```

## Định vị

Linh là **cộng sự kỹ thuật cá nhân**, không phải chatbot đổi tên. Nó:

| Thuộc tính | Thể hiện trong hệ thống |
|---|---|
| autonomous | vòng lặp agent đầy đủ + tool calling (`agent/turn_*.py`) |
| engineering-oriented | persona + 6 engineering agent chuyên trách (`~/.linh/agents/`) |
| persistent | memory + user profile + `state.db` riêng (`~/.linh/state.db`) |
| tool-enabled | 253 tool implementation, 6 nhóm toolset |
| multi-agent | `delegate_task` + `linh team` + spawn process độc lập |
| repository-aware | đọc/grep/git thật, không suy đoán cấu trúc |
| long-running | cron scheduler 24 module + task nền |
| planning & execution | kế hoạch → thực thi → verify, có checkpoint xin duyệt |
| code generation | tool file/shell + convention-aware |
| debugging | charter `debug` với quy trình 4 pha bắt buộc |
| research | tool web/browser + charter `research` (trích dẫn nguồn) |
| code review | charter `review` (phân loại BLOCKER/MAJOR/MINOR) |
| automation | cron, webhook, gateway 30 nền tảng |
| delegation | `linh team <role>` chạy agent riêng biệt process |

## Chuẩn hành vi (đã cài, không phải khẩu hiệu)

Những điều dưới đây không nằm ở tài liệu mà nằm ở **prompt + công cụ** thật:

1. **Bằng chứng trước kết luận** — `~/.linh/SOUL.md` yêu cầu đọc code/ chạy lệnh trước khi khẳng định.
2. **Không bịa** — cấm sinh output giả; không làm được thì báo không làm được.
3. **Checkpoint xin duyệt** — `~/.linh/AGENTS.md` liệt kê phạm vi phải hỏi trước (lệnh phá huỷ,
   deploy, ghi `.env`, restart service dùng chung).
4. **Ngôn ngữ** — trả lời tiếng Việt, xưng "em"/"anh/chị", thuật ngữ kỹ thuật giữ tiếng Anh,
   định dạng thân thiện Telegram (không bảng Markdown).
5. **Giữ tương thích core** — nghi thức sửa core ghi trong `AGENTS.md` + `docs/REBRAND.md`.

## Bề mặt bản sắc (những gì người dùng thấy)

| Bề mặt | Giá trị Linh | Ở đâu |
|---|---|---|
| Lệnh | `linh` | `bin/linh` → `~/.local/bin/linh` |
| Home | `~/.linh` | `LINH_HOME` |
| Logo banner | wordmark "Linh" (cyan) | `core/linh_branding.py`, `identity/skins/linh.yaml` |
| Nhãn trả lời | `⚡ Linh` | skin branding |
| Lời chào | "Linh ready — Personal AI Engineering Agent…" | skin branding |
| Version | `Linh v1.0.0 · core 0.21.1 (2026.9.7)` | `linh_branding.version_label()` |
| Persona | `~/.linh/SOUL.md` | seed từ `identity/SOUL.md` |
| Identity trong system prompt | "You are Linh…" | `agent/prompt_builder.py` (patched) |
| Đội agent | 6 charter | `~/.linh/agents/*.md` |

## Cây hệ thống

```
Linh
├── Core Agent            → run_agent.py + agent/turn_*.py (planning, reasoning, execution)
├── Agent Orchestrator    → delegate_task, batch_runner, linh team, cron
├── Engineering Agents    → code · debug · review · test · research · devops
├── Tools                 → shell · filesystem · git · search · browser/web · MCP
├── Memory                → session (state.db) · project (AGENTS.md/SOUL.md) · long-term (memories/)
└── Runtime               → config · logging · error/retry handling · session management
```

Bản đồ file cụ thể cho từng nhánh: `docs/ARCHITECTURE.md`.
