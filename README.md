# AppHealth backend chính

FastAPI cho Android và React Admin trong repo `Heathy_Team`. Đây là bản hoàn chỉnh
dùng trên máy giáo viên/học sinh. Bộ chia sprint cập nhật nằm ngoài repo này.

Xem [đối chiếu 32 task và lịch dự kiến](docs/SPRINT_AUDIT_20261113.md) cùng
[bảng lịch CSV](docs/SPRINT_SCHEDULE_20261113.csv).

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

## Bổ sung món cá nhân và ảnh — 17/11/2026

Revision `20261117_0013` tạo `user_foods` và thêm tên tệp ảnh cho catalog
`foods`. Revision `20261119_0015` bổ sung 100 món và ảnh đóng gói trong repo,
sau revision `20261119_0014` của danh sách vận động. Không sửa migration đã áp dụng.
Sau khi sao lưu DB, giáo viên chạy `alembic current`, `alembic heads`, rồi
`alembic upgrade head`. FE mới cần revision này trước khi dùng màn Tìm món ăn.

`FOOD_MEDIA_DIR` là thư mục ảnh **trên máy chạy BE** (mặc định `./media/food`),
không phải thư mục trên điện thoại và không dùng nhà cung cấp bên thứ ba.
Thư mục này cần quyền ghi, dung lượng và sao lưu cùng DB; khi triển khai nhiều
máy BE, mọi máy phải dùng cùng kho tệp bền vững. Ảnh được kiểm tra loại/kích
thước, chuẩn hóa thành JPEG và chỉ tải qua API có xác thực. Chỉ chủ tài khoản
được xem/sửa ảnh món riêng; chỉ Admin được tải ảnh lên món catalog.

Android: **Tìm món ăn → Tạo món** nhập số liệu/100 g, sau khi lưu chọn món để
**Thêm ảnh**. **Thực đơn đã lưu → Tạo bữa ăn từ các món của tôi** cho phép chọn
món trực tiếp và chỉnh thành phần bữa đã lưu, không cần ghi vào nhật ký trước.
API `GET/POST/PUT/DELETE /custom-foods`, `PUT/GET/DELETE /custom-foods/{id}/image`,
`PUT /admin/foods/{id}/image`, `GET /foods/{id}/image`. Nhật ký thức ăn vẫn giữ
snapshot khi sửa/xóa món riêng. API `GET /activity-logs` không truyền ngày trả
100 hoạt động mới nhất để hiển thị Nhật ký luyện tập.

## Chuỗi migration, giáo viên tự chạy

Đợt 13/11 thêm đúng một revision `20261113_0012`, sau `20261105_0011`.
Nó thêm password_hash Argon2 và cho phép google_sub rỗng với tài khoản email.
Tài khoản Google hiện có, quyền và dữ liệu sức khỏe được giữ nguyên. Revision
`20261105_0011` trước đó thêm role, mục tiêu, giờ ăn và AI history. Không sửa các
revision đã phát hành. Sau khi sao lưu database, đối chiếu:

```powershell
alembic current
alembic heads
```

Source hiện có **một head `20261119_0016`**. Alembic sẽ áp dụng các revision
còn thiếu theo thứ tự. Sau khi kiểm tra cấu hình và sao lưu,
giáo viên thực hiện:

```powershell
alembic upgrade head
```

DB đã ở head mới thì không cần chạy lại. Nếu current là revision không có trong
repo, hoặc đến từ chuỗi `git_*`/checkpoint BE khác, đối chiếu nguồn trước; không
tự stamp, xóa bảng hay đổi revision để ép chạy. File refresh-token đuôi `.PY` có
sẵn không được Alembic nạp; chuỗi active dùng `8da74fd2c368`. Không đổi file đó
sang `.py` vì sẽ tạo nhánh trùng tạo bảng.

Codex chỉ sinh SQL offline và kiểm tra graph; chưa upgrade DB của bạn.

## Danh mục 100 món mới

Chạy `alembic upgrade head` để thêm 100 món vào `foods` và gắn ảnh cho cả 5 món
ban đầu. Ảnh danh mục được đóng gói trong `app/assets/food_catalog`, không cần
chép vào `FOOD_MEDIA_DIR`; ảnh do Admin hoặc người dùng tải lên vẫn nằm ở thư mục
media đã cấu hình. Danh sách `/foods` trả tới 500 mục để 100 món mới đều hiện
trong màn Tìm món ăn. Số liệu dinh dưỡng tính trên 100 g từ USDA FoodData Central,
chỉ là giá trị tham khảo; công thức, nhãn hàng và cách chế biến thực tế có thể khác.
Nguồn và giấy phép từng ảnh nằm trong `app/assets/food_catalog/ATTRIBUTION.md`.

## Chạy API và cấp Admin

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Mở `/health`, `/docs`. Đăng ký email/mật khẩu hoặc đăng nhập Google để có user. Sau đó
giáo viên tự cấp quyền cho email đã đăng nhập (thay chuỗi trong dấu nháy):

```powershell
python -m app.admin_setup --email "email-tai-khoan-da-tao"
```

Lệnh chỉ cấp role cho user đang hoạt động đã tồn tại. Không có tài khoản
Admin mẫu. Đăng nhập lại React Admin sau khi cấp quyền. Mọi API Admin kiểm tra
quyền tại BE; khóa user thu hồi refresh token và chặn access token đang còn hạn.

Admin Android mới và React Admin web cùng dùng `/auth/me` và `/admin/*`, cùng
tài khoản email hoặc Google đã liên kết, role và database. Android mở cổng quản trị khi đăng nhập Admin;
từ phần sức khỏe mở lại tại Tài khoản → Quản trị viên → Mở quản trị. Thay role
trực tiếp trong DB có hiệu lực với API trên cả hai UI mà không cần cấp lại JWT;
Android cập nhật danh tính khi trở lại app, Tải lại tài khoản hoặc mở Admin.
Sửa danh mục ở một UI rồi tải lại UI còn lại để đọc dữ liệu chung mới nhất.

Chat giữ `answer`, `suggestions`, `disclaimer`; `suggestions` là toàn bộ chi tiết
bữa ăn nằm trong tin AI. Trường `follow_up_questions` mới (mặc định danh sách rỗng,
tối đa 4 câu hỏi ngắn) chỉ phục vụ nút hỏi tiếp. Ngữ cảnh gửi cho AI bao gồm cả
các bữa gợi ý trong lịch sử cũ. Dữ liệu được lưu trong JSON đã có; thay đổi chat
không cần migration riêng. Chưa chạy upgrade database thật.

## Email, mật khẩu và liên kết Google

- `POST /auth/register`: JSON email, full_name, password (8–128 ký tự), trả token pair.
- `POST /auth/login`: JSON email, password. Cùng JWT/refresh/logout và quyền như Google.
- `PUT /auth/password`: cần Bearer; JSON new_password và current_password nếu đã có
  mật khẩu. Google-only có thể thêm mật khẩu khi đang đăng nhập.
- `POST /auth/link-google`: cần Bearer và id_token Google đã xác minh, cùng email.
  Không tự gộp chỉ vì email trùng; đăng nhập bằng phương thức hiện có trước.
- `POST /auth/password/forgot`: email, gửi mã đặt lại nếu là tài khoản email/mật khẩu.
  API trả cùng một câu cho email tồn tại hoặc không tồn tại, tránh lộ danh sách tài khoản.
- `POST /auth/password/reset`: JSON `email`, `token` (đúng 8 chữ số) và
  `new_password`. Mã lưu dạng băm, mặc định có hiệu lực 15 phút, chỉ dùng một lần;
  sau 5 lần nhập sai cần yêu cầu mã mới. Trước khi dùng phải chạy migration
  `20261119_0016`. Sau khi đặt lại, các refresh token cũ bị thu hồi; access JWT
  đã phát hành có thể còn hiệu lực tối đa 30 phút mặc định.
- Android: Tài khoản → Bảo mật tài khoản để thêm/đổi mật khẩu hoặc liên kết Google.
  Ở màn đăng nhập, bấm **Quên mật khẩu?** rồi nhập email, dán mã và mật khẩu mới.
  Web Admin đăng nhập được bằng email hoặc Google, luôn kiểm tra role từ BE.

Email được chuẩn hóa; mật khẩu giữ nguyên cả khoảng trắng, chỉ lưu hash ở BE,
không trả hash/mật khẩu trong API hoặc lỗi validation. Hai phương thức đã liên kết
dùng cùng user ID, hồ sơ, quyền và nhật ký. Mã quên mật khẩu chỉ gửi qua SMTP khi
`SMTP_HOST` và `SMTP_FROM_EMAIL` đã cấu hình trong `.env`. Điền thêm
`SMTP_USERNAME`, `SMTP_PASSWORD` nếu nhà cung cấp yêu cầu đăng nhập;
`SMTP_PORT=587`, `SMTP_STARTTLS=true` là cấu hình mặc định. Sau khi thay `.env`,
khởi động lại BE. Không cần thêm bảng hoặc Alembic cho luồng này. Khi chưa cấu hình,
API quên mật khẩu trả 503 cho mọi email và Android báo cần liên hệ quản trị viên.
Chỉ thử bằng hộp thư của mình; không đưa mật khẩu SMTP lên Git. Mã mặc định hết hạn
sau 15 phút, yêu cầu gửi mã cùng email cách nhau tối thiểu 60 giây trên mỗi tiến trình
BE. Khi chạy nhiều tiến trình, nên đặt thêm giới hạn yêu cầu ở reverse proxy.
Thư viện hash: [argon2-cffi](https://argon2-cffi.readthedocs.io/en/stable/api.html).

## API chính

Tất cả đường dẫn dưới `/api/v1`, trừ `/health` ở origin:

| Nhóm | Endpoint |
|---|---|
| Email/Google/JWT | `/auth/register`, `/auth/login`, `/auth/google`, `/auth/me`, `/auth/refresh`, `/auth/logout`, `/auth/password`, `/auth/password/forgot`, `/auth/password/reset`, `/auth/link-google` |
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
