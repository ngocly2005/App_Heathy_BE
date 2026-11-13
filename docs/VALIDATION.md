# Kiểm chứng backend

## 2026-11-13 — Giữ phiên khi liên kết Google không hợp lệ

- 27 tests thành công. Khi Bearer app hợp lệ nhưng Google proof gửi để liên kết
  không hợp lệ, BE trả 400 thay vì 401 để client không tự xoay/xóa phiên email.
  Trường hợp chưa đăng nhập và Google login ban đầu vẫn trả 401 đúng ngữ nghĩa.
- Kiểm tra tài khoản hiện tại vẫn truy cập /auth/me và chưa bị liên kết sai.
  Chỉ thay BE và kiểm thử; không đổi schema/migration hoặc code FE đã được build.

## 2026-11-13 — Rà soát 32 task, email/mật khẩu song song Google

- Android: 75 JVM tests thành công, APK và lintDebug thành công, không có Error/Fatal.
- BE: 26 HTTP tests thành công, gồm 7 kiểm tra mới về đăng ký, login, đổi mật khẩu,
  liên kết Google, dữ liệu cùng user ID, role Admin và tài khoản bị khóa. Database
  SQLite trong bộ nhớ, Google/Groq được mock; không dùng DB/provider thật.
- Web: 12 tests thành công (5 mới về hai phương thức login, role và thu hồi token
  khi không lưu được phiên), TypeScript và production build thành công. Còn cảnh
  báo bundle lớn có sẵn.
- OpenAPI: 37 paths/55 operations. Đối chiếu route Retrofit Auth/App/Admin không
  có endpoint thiếu ở BE. Một head 20261113_0012; sinh SQL upgrade/downgrade offline
  cho đúng một revision mới, guard downgrade chạy trước thao tác xóa cột. DDL của
  15 bảng biên dịch được cho PostgreSQL; chưa chạy migration thật.
- Giữ Google, thêm email/password Argon2; chỉ liên kết sau xác thực, không tự gộp
  email trùng. Không lưu mật khẩu ở Android/web, không trả hash hoặc input mật
  khẩu trong lỗi validation. API/current-user/refresh chấp nhận cả hai phương thức.
- Đã kiểm tra bảng đối chiếu 32 mã BL, đường vào UI, lịch dự kiến trong sprint và
  giới hạn kiểm thử. Không đổi ngày Git thành ngày kế hoạch.
- Lượt test BE đầu có assertion dùng từ “short” trùng mã lỗi “too_short”; đã đổi
  mẫu test và xác nhận response không chứa input mật khẩu. Bộ tách task có lỗi
  thứ tự khai báo một schema cha; đã sửa exporter và kiểm tra lại từng mốc.
- Chưa kiểm thử email/Google trên emulator, camera, Groq, CORS thực tế hay DB
  PostgreSQL của học sinh. Giáo viên tự cài requirements và upgrade sau khi pull.

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
