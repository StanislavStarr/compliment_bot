from aiogram import Bot

from app.application.orders.notices import CounterpartNotice, NoticeKind


def format_counterpart_notice(notice: CounterpartNotice) -> str:
    author = f"@{notice.author_username}" if notice.author_username else "заказчик"
    recipient = f"@{notice.recipient_username}" if notice.recipient_username else "адресат"
    if notice.kind is NoticeKind.RECIPIENT_DECLINED:
        return f"{recipient} отказался получать сообщения по вашему заказу."
    if notice.kind is NoticeKind.AUTHOR_CANCELLED:
        return f"{author} отменил заказ. Сообщения больше не будут приходить."
    return f"{recipient} остановил получение сообщений."


async def deliver_counterpart_notice(bot: Bot, notice: CounterpartNotice) -> None:
    await bot.send_message(notice.telegram_chat_id, format_counterpart_notice(notice))
