# Kiểm chứng backend

## 2026-11-08 — Chat đầy đủ và Admin Android/web dùng chung

- 19 tests thành công (7 mới): SQLite trong bộ nhớ, Google/Groq mock; còn 2
  deprecation warnings của thư viện test. Không gọi provider hoặc DB thật.
- Chat giữ nguyên đầy đủ các bữa ăn dài/nhiều mục, đọc bản ghi legacy không có
  `follow_up_questions`, lưu payload mới, phân trang/ownership và không tự ghi món.
- Ngữ cảnh câu hỏi tiếp chứa cả các bữa gợi ý của lịch sử cũ; giới hạn riêng của
  câu hỏi tiếp không cắt nội dung bữa ăn. OpenAPI offline đã được cập nhật.
- Cấp/thu hồi Admin trực tiếp trong DB áp dụng ngay với access JWT còn hiệu lực:
  các API Admin bị chặn khi mất role; role/status không do Android hoặc web tự quyết.
- Kiểm tra payload đổi trạng thái không thể cấp role, không khóa Admin, cùng
  danh mục CRUD/read/list/deactivate và dữ liệu công khai giữ nhất quán.
- API Admin sẵn có dùng chung cho cả Android và React Admin. Không thêm migration.

## 2026-11-07 — Đối chiếu UI và BE

- 12 HTTP regression tests thành công, gồm 3 tests mới; SQLite bộ nhớ,
  mock Google/Groq, không kết nối DB/provider thật.
- Xác nhận sửa/xóa số đo quá khứ đúng ngày và đúng user, giữ số đo mới nhất
  trên hồ sơ; chặn xóa bản ghi cuối khi đã có hồ sơ và chặn ngày tương lai.
- Xác nhận lọc khoảng tháng bao gồm ngày đầu/cuối và ngày nhuận.
- Xác nhận thêm món cập nhật tổng đã ăn/calo còn lại khi calo vận động
  vẫn lớn hơn calo đã ăn; dữ liệu ngày khác giữ nguyên.
- Các API hiện có đáp ứng lần sửa UI này, chỉ thêm tests BE. Không thêm
  migration, không chạy Alembic upgrade; giữ nguyên bộ triển khai BE theo sprint.
- Còn 2 deprecation warnings của thư viện tests, không có lỗi tests.

## 2026-11-05

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
