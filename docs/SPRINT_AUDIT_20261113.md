# Rà soát 32 task và lịch sprint

Ngày rà soát/cập nhật source: **13/11/2026**.

Lịch gốc do giáo viên cung cấp: Sprint 1 15/09–05/10, Sprint 2 06/10–26/10, Sprint 3 27/10–23/11/2026.
Các mốc dưới là **kế hoạch phân bổ**, giữ hạn cuối đã ghi trong lịch gốc; không phải bằng chứng ngày hoàn thành thực tế.
UI có thể dựng theo hợp đồng/mock trước API. Kiểm tra ghép FE/BE thực hiện khi cả hai sẵn sàng và có dự phòng cuối sprint.
Commit và biên nhận phát hành giữ ngày tạo thực tế. Bộ chia task là bản cập nhật/tổng hợp lại từ source đã hoàn thiện, có hỗ trợ Codex; không nhận là lịch sử phát triển gốc của học sinh.

## Kết quả đối chiếu

Bản chính đã có các nhóm tính năng của cả 3 sprint. Lịch mới bổ sung rõ Login/Register: đợt này thêm email/mật khẩu song song Google, API đăng ký/đăng nhập, liên kết Google và đổi mật khẩu. Admin Android và React Admin web được giữ song song, dùng chung quyền/dữ liệu BE.
Bộ BE chia sprint cũ còn đánh dấu thiếu Admin; bản cập nhật thay trạng thái đó bằng source quản trị đã có trong code_chinh. Không sửa các snapshot hay commit cũ.

## Lịch dự kiến và tiêu chí kiểm tra

| Task | Từ | Đến | Chức năng |
|---|---|---|---|
| S1-BL03-BE | 2026-09-15 | 2026-09-20 | Authentication |
| S1-BL07-BE | 2026-09-21 | 2026-09-25 | Profile BMI/TDEE |
| S1-BL11-BE | 2026-09-26 | 2026-09-27 | Daily calories |
| S1-BL15-BE | 2026-10-01 | 2026-10-03 | Food camera |
| S1-BL19-BE | 2026-09-28 | 2026-09-30 | Food search and portions |
| S1-BL23-BE | 2026-10-04 | 2026-10-05 | Admin users |
| S1-BL02-FE | 2026-09-15 | 2026-09-17 | Authentication |
| S1-BL06-FE | 2026-09-16 | 2026-09-17 | Profile BMI/TDEE |
| S1-BL10-FE | 2026-09-18 | 2026-09-20 | Daily calories |
| S1-BL14-FE | 2026-09-18 | 2026-09-19 | Food camera |
| S1-BL18-FE | 2026-09-21 | 2026-09-22 | Food search and portions |
| S1-BL22-FE | 2026-09-29 | 2026-10-03 | Admin users |
| S2-BL27-BE | 2026-10-06 | 2026-10-10 | Nutrition macros |
| S2-BL31-BE | 2026-10-08 | 2026-10-11 | Exercise tracking |
| S2-BL35-BE | 2026-10-12 | 2026-10-15 | Water tracking |
| S2-BL39-BE | 2026-10-16 | 2026-10-19 | Saved meals |
| S2-BL43-BE | 2026-10-16 | 2026-10-19 | Weight history |
| S2-BL47-BE | 2026-10-20 | 2026-10-25 | Admin food/exercise catalog |
| S2-BL26-FE | 2026-10-06 | 2026-10-07 | Nutrition macros |
| S2-BL30-FE | 2026-10-06 | 2026-10-07 | Exercise tracking |
| S2-BL34-FE | 2026-10-08 | 2026-10-10 | Water tracking |
| S2-BL38-FE | 2026-10-09 | 2026-10-10 | Saved meals |
| S2-BL42-FE | 2026-10-11 | 2026-10-12 | Weight history |
| S2-BL46-FE | 2026-10-20 | 2026-10-25 | Admin food/exercise catalog |
| S3-BL51-BE | 2026-10-27 | 2026-11-03 | Meal AI chat |
| S3-BL55-BE | 2026-10-30 | 2026-11-03 | Unified diary |
| S3-BL59-BE | 2026-11-04 | 2026-11-05 | Historical calendar |
| S3-BL63-BE | 2026-11-06 | 2026-11-10 | Admin analytics and AI logs |
| S3-BL50-FE | 2026-10-27 | 2026-10-29 | Meal AI chat |
| S3-BL54-FE | 2026-10-29 | 2026-10-31 | Unified diary |
| S3-BL58-FE | 2026-10-30 | 2026-10-31 | Historical calendar |
| S3-BL62-FE | 2026-11-06 | 2026-11-10 | Admin analytics and AI logs |

## Vào UI và kiểm tra từng cặp FE/BE

### S1-BL02-FE / S1-BL03-BE — Authentication

- Vào UI: Màn đầu → Đăng ký / Đăng nhập / Tiếp tục với Google.
- API (prefix `/api/v1`): `POST /auth/register; POST /auth/login; POST /auth/google; GET /auth/me; POST /auth/refresh; POST /auth/logout; PUT /auth/password; POST /auth/link-google`.
- Cần kiểm tra: Đăng ký email mới, thoát rồi đăng nhập lại; trùng email bị chặn; liên kết Google trong Bảo mật tài khoản giữ nguyên ID và dữ liệu.

### S1-BL06-FE / S1-BL07-BE — Profile BMI/TDEE

- Vào UI: Tài khoản → Hồ sơ thể chất → Thiết lập/Chỉnh sửa.
- API (prefix `/api/v1`): `GET/PUT /profile`.
- Cần kiểm tra: Đổi chiều cao/cân nặng/mức vận động, so BMI/TDEE xem trước với BE sau lưu và mở lại.

### S1-BL10-FE / S1-BL11-BE — Daily calories

- Vào UI: Trang chủ → chọn ngày → Calo còn lại.
- API (prefix `/api/v1`): `GET /dashboard/daily?date=`.
- Cần kiểm tra: Thêm/sửa/xóa món hoặc vận động: tổng calo cập nhật; tiến độ đã ăn/mục tiêu; còn lại = mục tiêu − đã ăn + vận động.

### S1-BL14-FE / S1-BL15-BE — Food camera

- Vào UI: Nút + → Chụp món ăn; hoặc Tài khoản → Chụp món ăn.
- API (prefix `/api/v1`): `POST /ai/photo/analyze; POST /ai/photo/confirm`.
- Cần kiểm tra: Cấp quyền camera hoặc chọn ảnh; phân tích chưa ghi nhật ký; sửa kết quả và xác nhận mới ghi. Cần kiểm thử camera/Groq thật.

### S1-BL18-FE / S1-BL19-BE — Food search and portions

- Vào UI: Nút + → Tìm món ăn → chọn món → nhập gram/bữa/giờ.
- API (prefix `/api/v1`): `GET /foods?q=; POST /food-logs; PUT/DELETE /food-logs/{id}`.
- Cần kiểm tra: Tìm tên, thay 100 thành 150 g, kiểm tra tỷ lệ dinh dưỡng; lưu đúng ngày và không lẫn tài khoản.

### S1-BL22-FE / S1-BL23-BE — Admin users

- Vào UI: Android: tài khoản Admin → Tài khoản → Mở quản trị → Người dùng; web: chạy admin-web rồi đăng nhập.
- API (prefix `/api/v1`): `GET /auth/me; GET /admin/users; PUT /admin/users/{id}`.
- Cần kiểm tra: Teacher cấp role qua admin_setup/DB; thường bị 403, Admin đọc/khóa user; không tự cấp role, không khóa Admin; hai UI dùng chung BE.

### S2-BL26-FE / S2-BL27-BE — Nutrition macros

- Vào UI: Tài khoản → Dinh dưỡng; hoặc Trang chủ → Tổng quan dinh dưỡng → Chi tiết.
- API (prefix `/api/v1`): `GET/PUT /nutrition-settings; GET /dashboard/daily`.
- Cần kiểm tra: Tổng P/C/F và tỷ lệ năng lượng 4/4/9; trường hợp không có món không chia 0; tổng mục tiêu phần trăm phải bằng 100.

### S2-BL30-FE / S2-BL31-BE — Exercise tracking

- Vào UI: Tài khoản → Vận động → Loại vận động + số phút.
- API (prefix `/api/v1`): `GET /activity-types; POST /activity-logs; PUT/DELETE /activity-logs/{id}`.
- Cần kiểm tra: Calo MET × 3.5 × kg / 200 × phút; chỉnh thời lượng giữ MET snapshot; ngày/tài khoản độc lập.

### S2-BL34-FE / S2-BL35-BE — Water tracking

- Vào UI: Trang chủ → Uống nước ±; Tài khoản → Uống nước.
- API (prefix `/api/v1`): `GET/PUT /water-settings; POST /water-logs/adjust; PUT/DELETE /water-logs/{id}`.
- Cần kiểm tra: Chọn ly 200/500 ml, đổi mục tiêu, thêm/bớt không âm; nhật ký và Trang chủ cùng tổng nước.

### S2-BL38-FE / S2-BL39-BE — Saved meals

- Vào UI: Thực đơn → chọn món từ nhật ký → đặt tên → Lưu bữa ăn; Thêm nhanh.
- API (prefix `/api/v1`): `GET/POST/PUT/DELETE /saved-meals; POST /saved-meals/{id}/log`.
- Cần kiểm tra: Lưu bữa, chỉnh/xóa, thêm nhanh đúng ngày/bữa/giờ; xóa thực đơn không xóa nhật ký đã ghi; giữ snapshot món.

### S2-BL42-FE / S2-BL43-BE — Weight history

- Vào UI: Tài khoản → Cân nặng → chọn tháng/ngày → Lưu/Sửa/Xóa.
- API (prefix `/api/v1`): `GET /weight-entries; PUT/DELETE /weight-entries/{date}`.
- Cần kiểm tra: Biểu đồ theo ngày trong tháng; sửa/xóa quá khứ đúng ngày, giữ số lẻ; không đổi số đo mới nhất khi sửa số cũ; chặn tương lai/xóa số đo cuối.

### S2-BL46-FE / S2-BL47-BE — Admin food/exercise catalog

- Vào UI: Admin Android hoặc web → Thực phẩm / Bài tập.
- API (prefix `/api/v1`): `GET/POST/PUT/DELETE /admin/foods; GET/POST/PUT/DELETE /admin/activities`.
- Cần kiểm tra: Tạo/sửa/ngừng dùng trên một UI rồi tải lại ở UI kia; danh mục thường ẩn món ngừng dùng; không thay snapshot nhật ký cũ.

### S3-BL50-FE / S3-BL51-BE — Meal AI chat

- Vào UI: Tài khoản → Tư vấn bữa ăn.
- API (prefix `/api/v1`): `POST /ai/chat; GET /ai/chat/history?before_id=`.
- Cần kiểm tra: Bữa ăn đầy đủ trong từng tin AI và lịch sử cuộn; chip hỏi tiếp chỉ điền ô nhập; gửi mới thêm tin; cần thử provider thật.

### S3-BL54-FE / S3-BL55-BE — Unified diary

- Vào UI: Tab Nhật ký → chọn ngày → Món ăn/Vận động/Nước/Ghi chú.
- API (prefix `/api/v1`): `GET /history/daily?date=; GET/PUT/DELETE /diary/{date}; PUT/DELETE log endpoints`.
- Cần kiểm tra: Sửa/xóa mỗi loại log, ghi chú/tâm trạng đúng ngày; dashboard và lịch cập nhật sau lưu; không cần tải lại thủ công khi chuyển màn.

### S3-BL58-FE / S3-BL59-BE — Historical calendar

- Vào UI: Tài khoản → Lịch sử ngày → chuyển tháng → chọn ngày quá khứ.
- API (prefix `/api/v1`): `GET /history/calendar?month=; GET /history/daily?date=`.
- Cần kiểm tra: Tháng nhuận, ngày trống, ghi chú/cân nặng; chọn ngày mở đúng nhật ký; chặn ngày tương lai.

### S3-BL62-FE / S3-BL63-BE — Admin analytics and AI logs

- Vào UI: Admin Android: Tổng quan/Lịch sử AI; web: Dashboard/Lịch sử AI.
- API (prefix `/api/v1`): `GET /admin/analytics; GET /admin/ai-logs; GET /admin/ai-logs/{id}`.
- Cần kiểm tra: Lọc khoảng ngày, user/loại AI; xem JSON đầy đủ và lỗi provider; thu hồi role khi JWT còn hạn vẫn chặn ngay ở BE.

## Kiểm chứng và giới hạn

Các bộ kiểm thử/build, phạm vi dữ liệu giả lập và kết quả thực tế được ghi ở `docs/VALIDATION.md` của từng repo. Có source/API không tự đồng nghĩa đã chạy đạt trên máy học sinh.
Cần giáo viên kiểm thử Google, camera, Groq, CORS và PostgreSQL thật theo hướng dẫn. Chưa chạy upgrade hoặc sửa database thật trên máy này.
Không còn nhóm tính năng nào trong 32 task bị bỏ trống trong source cuối. Không nằm trong lịch: quên mật khẩu/email xác minh, đồng bộ realtime/offline, báo cáo/giỏ hàng/Premium.

## Hai bộ migration độc lập

Repo BE chính: thêm đúng một revision `20261113_0012` sau `20261105_0011`, giữ nguyên các revision đã có; giáo viên tự `alembic upgrade head`.
BE theo task giữ chuỗi `git_*` đã phát hành và chỉ thêm revision tương thích. Không trộn/stamp chuỗi migration của hai bộ lên cùng database. Cấu hình BE theo task dùng database `apphealth_git` riêng như trước.
