# Linh

**Linh** — Personal AI Engineering Agent của **Linh Nguyen**.

Linh là một agent kỹ thuật cá nhân độc lập: lệnh riêng (`linh`), home riêng (`~/.linh`),
bản sắc riêng (persona, banner, branding), và một đội 6 engineering agent chuyên trách.
Nó chạy trên **Hermes core architecture** (Nous Research) nên kế thừa toàn bộ năng lực:
vòng lặp agent tự trị, 253 tool, delegation đa agent, cron, gateway 30 nền tảng, desktop/TUI.

## Cài đặt

```bash
git clone https://github.com/tiennguyen3000/linh_agent.git ~/Linh
bash ~/Linh/scripts/install.sh
```

Repo có **2 nhánh**: `main` = lớp Linh (CLI, bản sắc, scripts), `core` = runtime Hermes core
đã áp bản sắc Linh. Clone `main` một mình **không chạy được** — installer tự lấy nhánh `core`,
dựng venv riêng, seed `~/.linh` và link lệnh `linh`.

- Máy đã có Hermes (`~/.hermes`): `bash scripts/install.sh --from-hermes` — copy core+venv, không tải gì.
- Yêu cầu: `git`, Python 3.11–3.13, ~1,5 GB trống, quyền đọc repo private.
- Chi tiết đầy đủ (thủ công, tuỳ chọn, update, uninstall, troubleshooting): **`docs/INSTALL.md`**.

## Bắt đầu

```bash
linh                                   # phiên tương tác
linh chat -q "câu hỏi"                 # một lượt
linh identity                          # thẻ bản sắc + home + đội agent
linh agents                            # 6 engineering agent
linh team debug "lỗi khi chạy X"       # giao việc cho một agent chuyên trách
linh selfcheck                         # kiểm tra cài đặt (10 check)
linh doctor                            # health check của core (passthrough)
```

Mọi subcommand của core dùng được y nguyên qua `linh` (`linh cron`, `linh gateway`,
`linh config`, `linh tools`, …) — `linh` chỉ chèn lớp bản sắc ở trên.

## Cấu trúc

```
~/Linh/
├── core/         # source runtime (fork Hermes core, git repo + remote upstream)
├── linh/         # package CLI: identity · agents · team · selfcheck · passthrough
├── identity/     # nguồn bản sắc: SOUL.md · AGENTS.md · agents/*.md · skins/ · skills/linh
├── bin/linh      # launcher (resolve symlink, set LINH_HOME, exec venv)
├── scripts/      # install · clone_core · rebrand · setup_venv · seed_home · sync_home · verify · rebuild
├── patches/      # rebrand.patch + manifest (bản sắc Linh vs upstream)
├── venv/         # runtime riêng của Linh
└── docs/         # ARCHITECTURE · LINH-IDENTITY · REBRAND · AGENT-ROLES

~/.linh/          # dữ liệu: config.yaml .env SOUL.md AGENTS.md agents/ skins/ skills/
                  #          memories/ plugins/ state.db logs/ sessions/
```

## Tài liệu

| Đọc | Nội dung |
|---|---|
| `docs/INSTALL.md` | **Cài đặt**: 2 nhánh repo, installer 6 bước, 2 chế độ venv, credentials, update, uninstall, troubleshooting |
| `docs/ARCHITECTURE.md` | Bản đồ kiến trúc đo từ code: entry point, agent loop, tool, đa agent, memory, runtime, build/test |
| `docs/LINH-IDENTITY.md` | Định nghĩa bản sắc Linh + chuẩn hành vi đã cài |
| `docs/AGENT-ROLES.md` | 6 engineering agent, cách gọi, hợp đồng đầu ra |
| `docs/REBRAND.md` | **Quan trọng**: đổi gì, giữ gì, vì sao, cách áp lại sau khi merge upstream |

## Vận hành

```bash
bash scripts/verify.sh                  # kiểm chứng toàn bộ (không tốn API call)
bash scripts/verify.sh --with-chat      # thêm smoke test identity (1 API call)
bash scripts/rebuild.sh                 # dựng lại từ đầu (idempotent)
bash scripts/rebuild.sh --force-seed    # ghi đè config/skills trong ~/.linh
python3 scripts/rebrand_core.py         # áp lại lớp bản sắc (idempotent, fail loudly)
```

**Quy tắc sắt:** `core/` là runtime đang chạy — không sửa tay. Sửa bản sắc thì thêm mục vào
manifest trong `scripts/rebrand_core.py` rồi chạy lại; sửa năng lực thì viết ở lớp `linh/`
(CLI/skill/plugin) để giữ core gần upstream và còn merge được fix.

## Ghi công

Linh là bản phái sinh (derived work) từ **Hermes Agent** của **Nous Research**, giấy phép MIT
(`core/LICENSE`). Bản sắc, lớp điều phối, đội agent và tài liệu Linh thuộc Linh Nguyen.
