import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.EMAIL_FROM
        message["To"] = to_email
        
        text_part = MIMEText(body, "plain", "utf-8")
        message.attach(text_part)
        
        if html_body:
            html_part = MIMEText(html_body, "html", "utf-8")
            message.attach(html_part)
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, message.as_string())
        
        logger.info(f"Email успішно відправлено на {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Помилка відправки email на {to_email}: {e}")
        return False

def send_booking_confirmation_email(user_email: str, user_name: str, booking_id: int, room_name: str, start_time, end_time) -> bool:
    subject = "✅ Підтвердження бронювання"
    
    body = f"""
Шановний(а) {user_name},

Дякуємо за ваше бронювання! 🎉

📋 Деталі бронювання:
• Номер бронювання: #{booking_id}
• Номер кімнати: {room_name}
• Дата заїзду: {start_time.strftime('%d.%m.%Y о %H:%M')}
• Дата виїзду: {end_time.strftime('%d.%m.%Y о %H:%M')}

Ваше бронювання підтверджено та очікує на вас.

ℹ️ Важлива інформація:
• Час заїзду: після {start_time.strftime('%H:%M')}
• Час виїзду: до {end_time.strftime('%H:%M')}
• Для будь-яких питань зв'яжіться з нами

З повагою,
Команда Booking System
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
        <h2 style="color: #28a745;">✅ Підтвердження бронювання</h2>
        <p>Шановний(а) {user_name},</p>
        <p>Дякуємо за ваше бронювання! 🎉</p>
        
        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>📋 Деталі бронювання:</h3>
            <ul>
                <li><strong>Номер бронювання:</strong> #{booking_id}</li>
                <li><strong>Номер кімнати:</strong> {room_name}</li>
                <li><strong>Дата заїзду:</strong> {start_time.strftime('%d.%m.%Y о %H:%M')}</li>
                <li><strong>Дата виїзду:</strong> {end_time.strftime('%d.%m.%Y о %H:%M')}</li>
            </ul>
        </div>
        
        <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px;">
            <h4>ℹ️ Важлива інформація:</h4>
            <ul>
                <li>Час заїзду: після {start_time.strftime('%H:%M')}</li>
                <li>Час виїзду: до {end_time.strftime('%H:%M')}</li>
                <li>Для будь-яких питань зв'яжіться з нами</li>
            </ul>
        </div>
        
        <p style="margin-top: 30px;">З повагою,<br>Команда Booking System</p>
    </div>
</body>
</html>
"""
    
    return send_email(user_email, subject, body, html_body)

def send_booking_cancellation_email(user_email: str, user_name: str, booking_id: int) -> bool:
    subject = "❌ Скасування бронювання"
    
    body = f"""
Шановний(а) {user_name},

Ваше бронювання #{booking_id} було скасовано.

Якщо ви не скасовували бронювання, будь ласка, негайно зв'яжіться з нами.

📞 Контактна інформація:
• Телефон: +380 XX XXX XX XX
• Email: support@booking.com

З повагою,
Команда Booking System
"""
    
    return send_email(user_email, subject, body)

def send_booking_reminder_email(user_email: str, user_name: str, booking_id: int, room_name: str, start_time) -> bool:
    subject = "⏰ Нагадування про майбутнє бронювання"
    
    body = f"""
Шановний(а) {user_name},

Нагадуємо, що ваше бронювання #{booking_id} починається завтра!

📋 Деталі бронювання:
• Номер кімнати: {room_name}
• Час заїзду: {start_time.strftime('%d.%m.%Y о %H:%M')}

Будь ласка, будьте вчасно. Чекаємо на вас! 😊

З повагою,
Команда Booking System
"""
    
    return send_email(user_email, subject, body)
