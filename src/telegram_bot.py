"""
Telegram бот для управления ProductRadar
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from . import bot_config
from . import parser_runner
from . import summary_manager
from . import logger

log = logger.get_logger("TelegramBot")

# Глобальный объект для управления парсером
parser_runner_instance = parser_runner.ParserRunner()

# Состояния пользователей (для обработки ввода настроек)
user_states: Dict[int, str] = {}


def check_auth(func):
    """Декоратор для проверки авторизации"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not bot_config.is_user_allowed(user_id):
            await update.message.reply_text(
                "❌ Доступ запрещен. Ваш user_id не в списке разрешенных."
            )
            return
        return await func(update, context)
    return wrapper


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🔄 Запустить парсер", callback_data="start_parser")],
        [InlineKeyboardButton("📊 Просмотр саммари", callback_data="view_summaries")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("📈 Статус", callback_data="status")],
    ]
    
    if parser_runner_instance.is_running():
        keyboard.append([InlineKeyboardButton("🛑 Остановить парсер", callback_data="stop_parser")])
    
    return InlineKeyboardMarkup(keyboard)


@check_auth
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    log.info(f"🚀 Команда /start (пользователь: {user.id} - {user.first_name})")
    
    text = f"👋 Привет, {user.first_name}!\n\n"
    text += "🤖 ProductRadar Bot - управление парсером\n\n"
    text += "Выберите действие:"
    
    await update.message.reply_text(text, reply_markup=get_main_menu())


@check_auth
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    user = update.effective_user
    await query.answer()
    
    data = query.data
    log.info(f"🔘 Кнопка нажата: {data} (пользователь: {user.id} - {user.first_name})")
    
    if data == "start_parser":
        await handle_start_parser(query, context)
    elif data == "stop_parser":
        await handle_stop_parser(query, context)
    elif data == "view_summaries":
        await handle_view_summaries(query, context)
    elif data == "status":
        await handle_status(query, context)
    elif data == "settings":
        await handle_settings(query, context)
    elif data.startswith("products_"):
        # Выбор количества товаров: products_3, products_5, etc.
        count = int(data.split("_")[1])
        await handle_start_parser_with_count(query, context, count)
    elif data.startswith("summary_"):
        # Просмотр конкретного саммари: summary_0, summary_1, etc.
        idx = int(data.split("_")[1])
        await handle_view_summary(query, context, idx)
    elif data == "back_to_menu":
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=get_main_menu()
        )


async def handle_start_parser(query, context):
    """Обработка запуска парсера - выбор количества товаров"""
    if parser_runner_instance.is_running():
        await query.edit_message_text(
            "⚠️ Парсер уже запущен!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
            ]])
        )
        return
    
    keyboard = [
        [
            InlineKeyboardButton("3 товара", callback_data="products_3"),
            InlineKeyboardButton("5 товаров", callback_data="products_5"),
        ],
        [
            InlineKeyboardButton("10 товаров", callback_data="products_10"),
            InlineKeyboardButton("25 товаров", callback_data="products_25"),
        ],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")],
    ]
    
    await query.edit_message_text(
        "🔄 Запуск парсера\n\nВыберите количество товаров:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_start_parser_with_count(query, context, count: int):
    """Запуск парсера с указанным количеством товаров"""
    user = query.from_user
    log.info(f"🔄 Запуск парсера: {count} товаров (пользователь: {user.id})")
    
    await query.edit_message_text(f"⏳ Запуск парсера на {count} товаров...")
    
    # Небольшая задержка для обновления сообщения
    await asyncio.sleep(0.5)
    
    try:
        success = parser_runner_instance.start(min_products=count)
        log.info(f"   → Результат start(): {success}")
        
        if success:
            # Проверяем, что процесс действительно запустился
            await asyncio.sleep(1)  # Даем процессу время запуститься
            
            is_running = parser_runner_instance.is_running()
            log.info(f"   → Процесс запущен: {is_running}")
            
            if is_running:
                status = parser_runner_instance.get_status()
                log.info(f"   → Статус процесса: PID={status.get('pid')}, running={status.get('running')}")
                
                await query.edit_message_text(
                    f"✅ Парсер запущен!\n\n"
                    f"Количество товаров: {count}\n"
                    f"PID: {status.get('pid')}\n"
                    f"Ожидайте завершения...\n\n"
                    f"Я уведомлю вас, когда парсер завершит работу.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📈 Статус", callback_data="status"),
                        InlineKeyboardButton("🛑 Остановить", callback_data="stop_parser"),
                    ]])
                )
                
                # Запускаем отслеживание процесса
                asyncio.create_task(monitor_parser(query.message.chat_id, context))
            else:
                # Процесс не запустился или сразу завершился
                status = parser_runner_instance.get_status()
                return_code = status.get("return_code")
                
                log.error(f"   ❌ Процесс не запустился! return_code={return_code}")
                log.error(f"   → Полный статус: {status}")
                
                # Пытаемся прочитать stderr для диагностики
                if parser_runner_instance.process:
                    try:
                        stdout, stderr = parser_runner_instance.process.communicate(timeout=1)
                        if stderr:
                            log.error(f"   → stderr: {stderr[:500]}")
                        if stdout:
                            log.info(f"   → stdout (первые 500 символов): {stdout[:500]}")
                    except:
                        pass
                
                error_msg = f"❌ Парсер не запустился"
                if return_code is not None:
                    error_msg += f"\n\nКод ошибки: {return_code}"
                error_msg += "\n\nПроверьте логи в терминале."
                
                await query.edit_message_text(
                    error_msg,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
                    ]])
                )
        else:
            log.error(f"   ❌ parser_runner_instance.start() вернул False")
            await query.edit_message_text(
                "❌ Не удалось запустить парсер. Проверьте логи.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
                ]])
            )
    except Exception as e:
        log.error(f"   ❌ Исключение при запуске парсера: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Ошибка при запуске: {str(e)}\n\nПроверьте логи в терминале.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
            ]])
        )


async def handle_stop_parser(query, context):
    """Остановка парсера"""
    user = query.from_user
    log.info(f"🛑 Остановка парсера (пользователь: {user.id})")
    
    if not parser_runner_instance.is_running():
        log.info(f"   → Парсер не запущен")
        await query.edit_message_text(
            "ℹ️ Парсер не запущен",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
            ]])
        )
        return
    
    status_before = parser_runner_instance.get_status()
    log.info(f"   → Статус до остановки: PID={status_before.get('pid')}")
    
    success = parser_runner_instance.stop()
    log.info(f"   → Результат остановки: {success}")
    
    if success:
        await query.edit_message_text(
            "🛑 Парсер остановлен",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
            ]])
        )
    else:
        log.error(f"   ❌ Не удалось остановить парсер")
        await query.edit_message_text(
            "❌ Не удалось остановить парсер",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
            ]])
        )


async def handle_view_summaries(query, context):
    """Просмотр списка саммари"""
    user = query.from_user
    log.info(f"📊 Просмотр саммари (пользователь: {user.id})")
    
    summaries = summary_manager.get_latest_summaries(10)
    log.info(f"   → Найдено саммари: {len(summaries)}")
    
    if not summaries:
        await query.edit_message_text(
            "📊 Саммари не найдены",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
            ]])
        )
        return
    
    # Сохраняем список в контексте для доступа при выборе
    context.user_data["summaries"] = summaries
    
    text = summary_manager.format_summary_list(summaries)
    text += "\n\nВыберите итерацию для просмотра:"
    
    keyboard = []
    for idx in range(min(len(summaries), 10)):
        keyboard.append([
            InlineKeyboardButton(
                f"#{idx + 1}",
                callback_data=f"summary_{idx}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_view_summary(query, context, idx: int):
    """Просмотр конкретного саммари"""
    user = query.from_user
    log.info(f"📄 Просмотр саммари #{idx + 1} (пользователь: {user.id})")
    
    summaries = context.user_data.get("summaries", [])
    
    if idx >= len(summaries):
        log.warning(f"   ⚠️ Индекс {idx} выходит за пределы списка (всего: {len(summaries)})")
        await query.answer("Саммари не найдено", show_alert=True)
        return
    
    summary_path = summaries[idx]
    log.info(f"   → Файл: {summary_path.name}")
    
    try:
        full_content = summary_manager.read_summary(summary_path)
        log.info(f"   → Размер файла: {len(full_content)} символов")
        
        # Создаем краткую выжимку
        extract = summary_manager.create_summary_extract(full_content)
        log.info(f"   → Размер выжимки: {len(extract)} символов")
        
        # Разбиваем на части, если слишком длинное
        parts = summary_manager.split_message(extract, max_length=4000)
        log.info(f"   → Разбито на {len(parts)} частей")
        
        # Отправляем первую часть
        await query.edit_message_text(
            f"📊 Саммари #{idx + 1} (краткая выжимка)\n\n{parts[0]}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад к списку", callback_data="view_summaries")
            ]])
        )
        
        # Отправляем остальные части отдельными сообщениями
        for i, part in enumerate(parts[1:], 1):
            log.info(f"   → Отправка части {i + 1}/{len(parts)}")
            await query.message.reply_text(part)
    except Exception as e:
        log.error(f"   ❌ Ошибка при чтении саммари: {e}", exc_info=True)
        await query.answer(f"Ошибка: {str(e)}", show_alert=True)


async def handle_status(query, context):
    """Показать статус"""
    user = query.from_user
    log.info(f"📈 Запрос статуса (пользователь: {user.id})")
    
    status = parser_runner_instance.get_status()
    log.info(f"   → Статус: {status}")
    
    text = "📈 Статус парсера\n\n"
    
    if status["running"]:
        text += "🟢 Статус: Работает\n"
        if status.get("duration") and isinstance(status["duration"], (int, float)):
            minutes = int(status["duration"] // 60)
            seconds = int(status["duration"] % 60)
            text += f"⏱ Время работы: {minutes}м {seconds}с\n"
        if status.get("pid"):
            text += f"🔢 PID: {status['pid']}\n"
    else:
        text += "🔴 Статус: Свободен\n"
        return_code = status.get("return_code")
        if return_code is not None:
            if return_code == 0:
                text += "✅ Последний запуск: Успешно\n"
            else:
                text += f"❌ Последний запуск: Ошибка (код {return_code})\n"
    
    # Последняя итерация
    summaries = summary_manager.get_latest_summaries(1)
    if summaries:
        info = summary_manager.parse_summary_info(summaries[0])
        text += f"\n📊 Последняя итерация:\n"
        text += f"   {info['status']} Успешно: {info['successful']}, Проверено: {info['checked']}"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
        ]])
    )


async def handle_settings(query, context):
    """Настройки"""
    settings = parser_runner.load_settings()
    
    text = "⚙️ Настройки парсера\n\n"
    text += f"📦 Количество товаров: {settings['min_products']}\n"
    text += f"👁️ Минимум impressions: {settings['min_impressions']}\n"
    text += f"📅 Дней назад: {settings['days_back']}\n"
    text += f"🖥️ Режим браузера: {'Headless' if settings['headless'] else 'Headful'}\n"
    text += "\n💡 Изменение настроек:\n"
    text += "Отредактируйте файл `config/bot_settings.json`\n"
    text += "и перезапустите бота."
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
        ]])
    )


async def monitor_parser(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Отслеживание процесса парсера"""
    check_interval = 30  # Проверять каждые 30 секунд
    start_time = datetime.now()
    
    log.info(f"👁️ Начало мониторинга парсера (chat_id: {chat_id})")
    
    check_count = 0
    while parser_runner_instance.is_running():
        check_count += 1
        await asyncio.sleep(check_interval)
        status = parser_runner_instance.get_status()
        if status.get("duration") and isinstance(status["duration"], (int, float)):
            minutes = int(status["duration"] // 60)
            log.info(f"   → Проверка #{check_count}: парсер работает ({minutes}м)")
    
    # Парсер завершился
    duration = (datetime.now() - start_time).total_seconds()
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    log.info(f"   ✅ Парсер завершился. Длительность мониторинга: {minutes}м {seconds}с")
    
    # Получаем статус перед очисткой
    status = parser_runner_instance.get_status()
    return_code = status.get("return_code")
    log.info(f"   → Код возврата: {return_code}")
    
    # Получаем последнее саммари
    summaries = summary_manager.get_latest_summaries(1)
    
    text = "✅ Парсер завершил работу!\n\n"
    
    if return_code == 0:
        text += "🎉 Успешно завершено\n\n"
    elif return_code is not None:
        text += f"⚠️ Завершено с кодом: {return_code}\n\n"
    else:
        text += "ℹ️ Завершено\n\n"
    
    if summaries:
        info = summary_manager.parse_summary_info(summaries[0])
        text += f"📊 Результаты:\n"
        text += f"   Успешно: {info['successful']}\n"
        text += f"   Проверено: {info['checked']}\n"
        text += f"   Пропущено: {info['skipped']}"
        log.info(f"   → Результаты: успешно={info['successful']}, проверено={info['checked']}")
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=get_main_menu()
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    user_id = update.effective_user.id if update and update.effective_user else "unknown"
    log.error(f"❌ Ошибка в боте (пользователь: {user_id}): {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"❌ Произошла ошибка: {str(context.error)[:200]}\n\nПопробуйте позже или проверьте логи."
            )
        except:
            log.error("   ❌ Не удалось отправить сообщение об ошибке")


def create_application() -> Application:
    """Создать и настроить приложение бота"""
    # Проверка конфигурации
    is_valid, error = bot_config.validate_config()
    if not is_valid:
        log.error(f"❌ Ошибка конфигурации: {error}")
        raise ValueError(f"Ошибка конфигурации: {error}")
    
    log.info("Создание приложения бота...")
    
    # Создаем приложение
    application = Application.builder().token(bot_config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    log.info("✅ Обработчики зарегистрированы")
    
    return application


def run_bot():
    """Запустить бота"""
    log.info("Запуск Telegram бота...")
    
    application = create_application()
    
    log.info("Бот запущен. Нажмите Ctrl+C для остановки.")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

