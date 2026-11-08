# AppHealth backend chính

FastAPI cho Android và React Admin trong repo `Heathy_Team`. Đây là bản hoàn chỉnh
dùng trên máy giáo viên/học sinh. Bản BE chia sprint nằm ngoài repo này và giữ nguyên.

## Cài đặt

Dùng Python 3.12. Tạo/kích hoạt môi trường riêng nếu chưa có, không sao chép `.venv`
giữa các máy. Giữ `.env` đang dùng, chỉ bổ sung các trường còn thiếu.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

- `DATABASE_URL`: PostgreSQL hiện có của bạn.
- `SECRET_KEY`: khóa JWT riêng, không dùng khóa phát triển cho môi trường thật.
- `GOOGLE_WEB_CLIENT_ID`: cùng Web OAuth Client ID phía Android/React.
- `GROQ_API_KEY`, `GROQ_MODEL`: provider Groq hiện có; không đưa key vào FE.
- `GROQ_VISION_MODEL`: model hỗ trợ ảnh. Bỏ trống sẽ dùng `GROQ_MODEL`; model chat
  không hỗ trợ ảnh sẽ không phân tích ảnh được. Chọn model khả dụng trong tài khoản.
- `CORS_ORIGINS`: mảng JSON các origin React, ví dụ
  `["http://localhost:5173","http://127.0.0.1:5173"]`.
- `TIME_ZONE=Asia/Bangkok`: ngày nghiệp vụ UTC+7; timestamp lưu theo UTC.

## Một migration mới, giáo viên tự chạy

Revision mới duy nhất là `20261105_0011`, nối tiếp `20261006_0010`. Nó thêm role,
mục tiêu nước/dinh dưỡng, giờ ăn, lịch sử AI và mức vận động 1.9. Không gộp hoặc
sửa các revision cũ. Sau khi sao lưu database, đối chiếu:

```powershell
alembic current
alembic heads
```

Source có head `20261105_0011`. Nếu DB đang ở `20261006_0010`, sau khi kiểm tra
cấu hình và sao lưu, giáo viên thực hiện:

```powershell
alembic upgrade head
```

DB đã ở head mới thì không cần chạy lại. Nếu current là revision không có trong
repo, hoặc đến từ chuỗi `git_*`/checkpoint BE khác, đối chiếu nguồn trước; không
tự stamp, xóa bảng hay đổi revision để ép chạy. File refresh-token đuôi `.PY` có
sẵn không được Alembic nạp; chuỗi active dùng `8da74fd2c368`. Không đổi file đó
sang `.py` vì sẽ tạo nhánh trùng tạo bảng.

Codex chỉ sinh SQL offline và kiểm tra graph; chưa upgrade DB của bạn.

## Chạy API và cấp Admin

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Mở `/health`, `/docs`. Đăng nhập Google một lần để có user đã xác minh. Sau đó
giáo viên tự cấp quyền cho email đã đăng nhập (thay chuỗi trong dấu nháy):

```powershell
python -m app.admin_setup --email "email-Google-da-dang-nhap"
```

Lệnh chỉ cấp role cho user Google đang hoạt động đã tồn tại. Không có tài khoản
Admin mẫu. Đăng nhập lại React Admin sau khi cấp quyền. Mọi API Admin kiểm tra
quyền tại BE; khóa user thu hồi refresh token và chặn access token đang còn hạn.

Admin Android mới và React Admin web cùng dùng `/auth/me` và `/admin/*`, cùng
Google account, role và database. Android mở cổng quản trị khi đăng nhập Admin;
từ phần sức khỏe mở lại tại Tài khoản → Quản trị viên → Mở quản trị. Thay role
trực tiếp trong DB có hiệu lực với API trên cả hai UI mà không cần cấp lại JWT;
Android cập nhật danh tính khi trở lại app, Tải lại tài khoản hoặc mở Admin.
Sửa danh mục ở một UI rồi tải lại UI còn lại để đọc dữ liệu chung mới nhất.

Chat giữ `answer`, `suggestions`, `disclaimer`; `suggestions` là toàn bộ chi tiết
bữa ăn nằm trong tin AI. Trường `follow_up_questions` mới (mặc định danh sách rỗng,
tối đa 4 câu hỏi ngắn) chỉ phục vụ nút hỏi tiếp. Ngữ cảnh gửi cho AI bao gồm cả
các bữa gợi ý trong lịch sử cũ. Dữ liệu được lưu trong JSON đã có; đợt này không
thêm migration và không chạy upgrade database thật.

## API chính

Tất cả đường dẫn dưới `/api/v1`, trừ `/health` ở origin:

| Nhóm | Endpoint |
|---|---|
| Google/JWT | `/auth/google`, `/auth/me`, `/auth/refresh`, `/auth/logout` |
| Hồ sơ/mục tiêu | `/profile`, `/nutrition-settings`, `/water-settings` |
| Tổng ngày/macro | `/dashboard/daily?date=YYYY-MM-DD` |
| Thực phẩm | `/foods?q=`, `/food-logs`, PUT/DELETE `/food-logs/{id}` |
| Vận động | `/activity-types`, `/activity-logs`, PUT/DELETE theo ID |
| Nước | `/water-logs`, `/water-logs/adjust`, PUT/DELETE theo ID |
| Saved meals | `/saved-meals`, CRUD và `/{id}/log` |
| Cân nặng | `/weight-entries`, PUT/DELETE `/{measured_on}` |
| Diary/lịch | `/diary/{date}`, `/history/daily`, `/history/calendar` |
| Chat/ảnh | `/ai/chat`, `/ai/chat/history`, `/ai/photo/analyze`, `/ai/photo/confirm` |
| Admin | `/admin/users`, `/admin/foods`, `/admin/activities`, `/admin/analytics`, `/admin/ai-logs` |

Xem `/docs` hoặc `docs/openapi.json` cho payload đầy đủ. Nghiệp vụ cần Bearer JWT;
Admin cần role Admin. List Admin hỗ trợ page/per_page/sort/filter, trả `{items,total}`.

Phân tích ảnh không tạo food log; chỉ xác nhận kết quả đã sửa mới ghi nhật ký.
Sửa gram/thời lượng giữ snapshot dinh dưỡng/MET; ngừng dùng catalog giữ log cũ.
Mục tiêu cho ngày cũ hiện dùng cấu hình mục tiêu hiện hành. POST chưa có idempotency
key bền vững: sau lỗi mất kết nối, client tải lại để kiểm tra trước khi gửi lại.

## Kiểm tra cô lập

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Tests dùng SQLite trong bộ nhớ và mock Google/Groq, không chạy Docker/DB thật.
Không dùng `test.py` ở root thay cho regression; đó là thử nghiệm provider có sẵn.
OAuth thật, ảnh/chat Groq thật và migration PostgreSQL cần cấu hình của giáo viên.
Xem `docs/VALIDATION.md` để biết các bước đã/chưa chạy.
