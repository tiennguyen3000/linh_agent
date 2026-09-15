# Linh Engineering Agents — 6 vai chuyên trách

Charter nằm ở `~/.linh/agents/<role>.md` (nguồn: `identity/agents/`). Mỗi charter gồm
YAML frontmatter (`name`, `title`, `mission`, `engine`, `output`) + phần phương pháp bắt buộc
và hợp đồng đầu ra.

## Gọi một agent

```bash
linh agents                       # liệt kê cả 6
linh agents debug                 # in charter đầy đủ
linh team debug "lỗi X khi chạy Y"     # giao việc → agent chạy process riêng
linh team review --show                # xem prompt sẽ gửi (không chạy)
LINH_TEAM_DRY_RUN=1 linh team test "…"  # in prompt rồi thoát
```

Trong phiên Linh, có thể giao việc qua `delegate_task` và dán charter tương ứng làm context.
`linh team` chạy `venv/bin/hermes chat -q` trong process riêng: session riêng, đầy đủ tool,
không làm hỏng state của shell gọi.

## Danh mục

| Role | Nhiệm vụ | Hợp đồng đầu ra |
|---|---|---|
| `code` | Viết/sửa/mở rộng code trong repo thật | diff + lệnh kiểm chứng đã chạy |
| `debug` | Tìm root cause từ triệu chứng thật (4 pha) | root cause + bằng chứng + fix tối thiểu + test |
| `review` | Soát diff/PR như reviewer khó tính | phát hiện phân loại + file:dòng + cách sửa |
| `test` | Viết & chạy test bắt được lỗi thật | test đã thêm + output đỏ-trước/xanh-sau |
| `research` | Trả lời câu hỏi kỹ thuật có nguồn | câu trả lời + nguồn + mức tin cậy |
| `devops` | Build/deploy/CI/ops có rollback | thay đổi + bằng chứng trạng thái + cách rollback |

## Quy tắc chung mọi charter (đã cài trong prompt, không phải gợi ý)

- **Không bịa**: không sinh output test/log như thể đã chạy; không báo xong khi chưa verify.
- **Bằng chứng**: mọi khẳng định phải kèm `file:dòng`, lệnh đã chạy, hoặc URL nguồn.
- **Không dọn triệu chứng**: cấm `try/except: pass`, sleep, retry mù để che lỗi.
- **Ranh giới an toàn (`devops`)**: lệnh phá huỷ / deploy production / ghi `.env` phải xin
  xác nhận trước.
- **Test có giá trị**: cấm test đọc source rồi regex (test hình dạng code); cấm snapshot giá
  trị dễ đổi — chỉ khẳng định quan hệ/bất biến.

## Mở rộng

Thêm role mới = thêm `identity/agents/<name>.md` (frontmatter + body), chạy
`python3 scripts/seed_home.py` để cài vào `~/.linh/agents/`, rồi `linh agents` để kiểm.
Nếu muốn vai đó chạy như agent nền song song, dùng `delegate_task` với charter làm context.
