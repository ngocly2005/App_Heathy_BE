"""SMTP delivery for password-reset messages. No credentials are logged."""

from email.message import EmailMessage
import smtplib
import ssl

from app.core.config import Settings


def reset_mail_configured(settings: Settings) -> bool:
    auth_complete = bool(settings.smtp_username) == bool(settings.smtp_password)
    return bool(settings.smtp_host and settings.smtp_from_email and auth_complete)


def send_password_reset_mail(recipient: str, token: str, settings: Settings) -> None:
    if not reset_mail_configured(settings):
        raise RuntimeError("Password reset SMTP is not configured")
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = "FitChat: mã đặt lại mật khẩu"
    message.set_content(
        "Bạn đã yêu cầu đặt lại mật khẩu FitChat.\n\n"
        "Mở ứng dụng, chọn Quên mật khẩu rồi dán mã sau vào ô xác nhận:\n\n"
        f"{token}\n\n"
        f"Mã có hiệu lực trong {settings.password_reset_minutes} phút và chỉ dùng một lần. "
        "Nếu bạn không yêu cầu, hãy bỏ qua email này.\n"
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        client.ehlo()
        if settings.smtp_starttls:
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        client.send_message(message)
