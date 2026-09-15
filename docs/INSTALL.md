# Cài đặt Linh

Repo `tiennguyen3000/linh_agent` chứa **hai** thứ trên hai nhánh:

| Nhánh | Nội dung | Kích thước |
|---|---|---|
| `main` | lớp Linh: CLI `linh/`, bản sắc `identity/`, scripts, docs | ~30 file |
| `core` | runtime: Hermes core đã áp lớp bản sắc Linh (fork) | ~410 MB / 69 MB pack |

Vì vậy `git clone` nhánh `main` **không đủ để chạy** — phải lấy thêm nhánh `core`
(installer làm việc này tự động) hoặc copy core từ một máy đã có Hermes.

## Yêu cầu

- macOS hoặc Linux, `git`.
- Python **3.11–3.13** (core khai báo `requires-python = ">=3.11,<3.14"`). macOS có sẵn 3.9 → cần thêm:
  `brew install python@3.12` (hoặc trỏ `LINH_PYTHON=/path/to/python3.12`).
- ~1,5 GB dung lượng trống (core 410 MB + venv 311 MB + deps).
- Quyền đọc repo private: HTTPS + token (fine-grained token cần **Contents: Read**), hoặc SSH key.

## Cài một lệnh

```bash
git clone https://github.com/tiennguyen3000/linh_agent.git ~/Linh
bash ~/Linh/scripts/install.sh
```

Installer chạy 6 bước: kiểm tra prereq → lấy lớp Linh → lấy core (nhánh `core`) →
áp lớp bản sắc → dựng venv → seed `~/.linh` → link `~/.local/bin/linh` → `verify.sh`.

Tuỳ chọn:

```bash
bash scripts/install.sh --from-hermes      # máy đã có ~/.hermes: copy core+venv, không tải gì
bash scripts/install.sh --dir ~/Linh       # đổi vị trí cài
bash scripts/install.sh --core-ref core    # đổi nhánh core
bash scripts/install.sh --mode git         # buộc lấy core từ nhánh `core` trên GitHub
bash scripts/install.sh --venv-mode fresh  # buộc dựng venv mới (không copy venv Hermes)
bash scripts/install.sh --extras messaging # extras của core (mặc định 'all', trống = core only)
bash scripts/install.sh --with-dev         # thêm [dev] (pytest…) để verify.sh chạy được test suite
bash scripts/install.sh --no-link          # không tạo symlink ~/.local/bin/linh
bash scripts/install.sh --skip-verify      # dừng trước bước verify
```

Nếu `~/.local/bin` không có trong `PATH`, thêm vào shell rc:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Các bước thủ công (nếu không dùng installer)

```bash
export LINH_HOME="$HOME/.linh"
cd ~/Linh

bash   scripts/clone_core.sh --mode git --ref core   # hoặc --mode local để copy từ ~/.hermes
python3 scripts/rebrand_core.py                     # kỳ vọng: 0 edits (core branch đã áp sẵn)
python3 scripts/setup_venv.py --mode fresh          # hoặc --mode clone nếu có venv Hermes
python3 scripts/seed_home.py
ln -sfn ~/Linh/bin/linh ~/.local/bin/linh
bash   scripts/verify.sh
```

## Hai chế độ dựng venv

- `--mode clone` — copy venv Hermes (308 MB, đã có sẵn deps) rồi repoint mọi đường dẫn
  tuyệt đối sang core Linh. Không tải gì, vài giây. Dùng khi máy có `~/.hermes/hermes-agent/venv`.
- `--mode fresh` — tạo venv mới bằng CPython 3.11–3.13 rồi cài deps của core
  (`uv sync --frozen` khi có `uv` + `core/uv.lock`, ngược lại `pip install -e "core[all]"`).
  Dùng cho máy mới; mất vài phút và cần mạng. Extras mặc định là `all` (giống installer của
  Hermes); các backend cài lười (messaging/telegram, TTS, search provider…) do core tự cài ở
  lần dùng đầu, nên không cần thêm vào đây. `--with-dev` thêm `[dev]` để `verify.sh` chạy được
  test suite (`--with-dev` mà thiếu thì verify bỏ qua bước test chứ không fail).
- `--mode auto` (mặc định) — có venv Hermes thì `clone`, không thì `fresh`.

Cả hai chế độ kết thúc bằng cùng một bước finalize: ghi `linh_core.pth` (để `import cli`,
`import hermes_cli`, `import tools` trỏ vào `~/Linh/core`) và tạo console script `venv/bin/linh`.

## Sau khi cài: credentials

`seed_home.py` kế thừa `config.yaml`, `.env`, `skills`, `memories`, `plugins` từ `~/.hermes`
nếu có. Máy mới không có gì để kế thừa → seeding tự sinh `config.yaml` mặc định (do core
tự ghi, có `display.skin: linh`), nhưng **chưa có API key**:

```bash
linh setup            # flow cấu hình provider/model của core
# hoặc sửa trực tiếp ~/.linh/.env
linh chat -q "bạn là ai?"
```

## Đồng bộ skill/memory về sau (Hermes → Linh)

Seed copy `skills/`, `memories/`, `plugins/` từ `~/.hermes` **một lần** lúc cài; sau đó hai home
tách rời (đúng thiết kế isolation). Muốn kéo việc làm sau đó bên Hermes sang Linh thì dùng:

```bash
bash scripts/sync_home.sh                      # dry run (mặc định, không ghi gì)
bash scripts/sync_home.sh --apply              # chỉ copy file Linh chưa có
bash scripts/sync_home.sh --apply --overwrite  # copy cả file khác nội dung
bash scripts/sync_home.sh --only skills        # giới hạn một vùng: skills|memories|plugins
bash scripts/sync_home.sh --show-extra         # liệt kê thêm file chỉ có bên Linh
```

Quy tắc an toàn của script: mặc định **dry-run**; **không bao giờ ghi đè** (muốn đè phải
`--overwrite`); **không xoá gì**; **không đụng `skills/linh`** (skill được pin
`ESSENTIAL_SKILLS`); bỏ qua file state riêng của từng home (`.curator_ledger.jsonl`,
`.usage.json`, `.bundled_manifest`, `.curator_backups/`). Script từ chối chạy nếu src = dst.

Chạy thật trên máy này (`--show-extra`, không ghi gì):

```
== skills
  DIFF  github/github-publish/SKILL.md   (kept — pass --overwrite to update)
== memories
  DIFF  MEMORY.md   (kept — pass --overwrite to update)
== plugins
  (up to date)

Tổng: 0 file mới, 2 file khác nội dung, 0 file chỉ có bên Linh
```

Đúng như thiết kế: 2 chỗ khác đó **không nên** bị đè (bản `github-publish` bên Linh mới hơn,
9095 B so với 5767 B; `MEMORY.md` là memory riêng của từng agent) — nên mặc định chỉ báo, không ghi.

## Cập nhật

```bash
cd ~/Linh
git pull --ff-only origin main                 # lớp Linh
bash scripts/clone_core.sh --mode git --ref core   # core mới nhất từ nhánh core
python3 scripts/rebrand_core.py                # phải in 0 edits
bash scripts/verify.sh
```

Sau khi merge fix từ upstream (`git -C core fetch upstream main`), luôn chạy lại
`rebrand_core.py` rồi `verify.sh` — xem `docs/REBRAND.md`.

## Gỡ cài đặt

```bash
rm ~/.local/bin/linh        # symlink
mv ~/Linh ~/Linh.removed    # distribution
mv ~/.linh ~/.linh.removed  # home dữ liệu (sessions, memory, skills)
```

## Xử lý sự cố

**`ModuleNotFoundError: hermes_cli`** — chưa có core, hoặc venv trỏ sai chỗ:
chạy `bash scripts/clone_core.sh --mode git` rồi `python3 scripts/setup_venv.py --mode auto`.

**`no CPython 3.11–3.13 found`** — `python3` của macOS là 3.9; cài `python@3.12` hoặc
`LINH_PYTHON=/opt/homebrew/bin/python3.12 python3 scripts/setup_venv.py --mode fresh`.

**`branding import: ModuleNotFoundError: No module named 'linh_branding'`** — core thiếu module
bản sắc (tree Hermes gốc không có file này). `python3 scripts/rebrand_core.py` sẽ tự tạo lại từ
`patches/linh_branding.py`; nếu file canonical đó mất thì lấy từ nhánh `core`.

**Clone repo private thất bại** — dùng token trong URL
(`https://<user>:<token>@github.com/tiennguyen3000/linh_agent.git`) hoặc SSH remote.
Token fine-grained cần **Contents: Read**.

**`linh selfcheck` báo `skin ok ✗`** — `display.skin` trong `~/.linh/config.yaml` không phải
`linh`: `linh config set display.skin linh`.

**Biến môi trường `LINH_HOME` thắng `HERMES_HOME`** — runtime Linh export `LINH_HOME`, và lớp
patch cho `LINH_HOME` quyền ưu tiên cao hơn `HERMES_HOME`. Nghĩa là mọi lệnh chạy trong
terminal của Linh đều thừa hưởng `LINH_HOME=$HOME/.linh`; muốn chạy core với home tạm để
thử nghiệm thì phải set **cả hai**:

```bash
LINH_HOME=/tmp/probe HERMES_HOME=/tmp/probe ~/Linh/venv/bin/python3 -c "..."
```

Không set `LINH_HOME` = ghi thẳng vào home thật (mất config/skin nếu là lệnh ghi).

**Kiểm chứng** — `bash scripts/verify.sh` chạy 5 nhóm check thật (CLI, selfcheck, rebrand
idempotent, isolation home, test files bị ảnh hưởng); `--with-chat` thêm 1 model call để
xác nhận agent tự nhận là Linh. Không có check nào đọc từ tài liệu.
