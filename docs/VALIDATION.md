# Kiểm chứng backend 2026-11-05

- 9 HTTP regression tests thành công; SQLite bộ nhớ, mock Google/Groq.
- Cài được `requirements.txt` trong venv mới; `pip check` thành công.
- Kiểm tra Google exchange/refresh/reuse/logout, quyền và ownership, disabled user,
  profile/targets, snapshots, hoạt động/nước, saved meals, cân nặng, diary/calendar,
  AI analyze/confirm/history và ngày UTC+7.
- Từ chối gram/MET nhỏ hơn độ chính xác cột, tránh lỗi ghi thành 0.
- Một head `20261105_0011`; SQL offline cho migration mới. OpenAPI có 33 paths.

Chưa chạy live PostgreSQL migration, Docker, bootstrap Admin, OAuth hoặc Groq
thật. Cần cấu hình giáo viên để kiểm tra provider/model/quota. Thư viện tests có
deprecation warnings, không làm tests thất bại.

API/migration mới chỉ ở BE chính. `trien_khai_git_be` giữ nguyên; không chép
migration này vào chuỗi chia sprint `git_*`.
