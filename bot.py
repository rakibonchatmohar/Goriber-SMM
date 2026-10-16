import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# Configuration
TELEGRAM_BOT_TOKEN = "8986638020:AAGvPJNtBsrA088-qUzj3uztyOtTh4rtFx4"  # আপনার বটের টোকেন
SMM_API_URL = "https://goribersmm.cyou/api/v1"
SMM_API_KEY = "33645fabd1ca760de9b4781c4399cab524418536"

# Conversation States
SERVICE_ID, LINK, QUANTITY = range(3)

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def smm_request(payload):
    payload["key"] = SMM_API_KEY
    try:
        response = requests.post(SMM_API_URL, data=payload, timeout=15)
        return response.json()
    except Exception as e:
        return {"error": f"API Request Failed: {str(e)}"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 চেক ব্যালেন্স", callback_data="check_balance")],
        [InlineKeyboardButton("📜 সার্ভিসের তালিকা", callback_data="list_services")],
        [InlineKeyboardButton("🛒 নতুন অর্ডার করুন", callback_data="new_order")],
        [InlineKeyboardButton("🔍 অর্ডার স্ট্যাটাস", callback_data="check_status")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_msg = (
        "👋 **SMM Panel Telegram Bot-এ স্বাগতম!**\n\n"
        "নিচের অপশনগুলো ব্যবহার করে সহজেই অর্ডার দিন বা স্ট্যাটাস চেক করুন।"
    )
    if update.message:
        await update.message.reply_text(welcome_msg, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(welcome_msg, parse_mode="Markdown", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_balance":
        res = smm_request({"action": "balance"})
        if "balance" in res:
            msg = f"💵 **আপনার বর্তমান ব্যালেন্স:** {res['balance']} {res.get('currency', 'USD')}"
        else:
            msg = f"❌ **ত্রুটি:** {res.get('error', 'ব্যালেন্স লোড করা সম্ভব হয়নি')}"
        await query.message.reply_text(msg, parse_mode="Markdown")

    elif query.data == "list_services":
        res = smm_request({"action": "services"})
        if isinstance(res, list):
            msg = "📋 **সার্ভিস তালিকা (প্রথম ১০ টি):**\n\n"
            for s in res[:10]:
                msg += f"🔹 **ID:** `{s['service']}`\n📌 **নাম:** {s['name']}\n💰 **রেট:** ${s['rate']}\n📉 **Min/Max:** {s['min']} - {s['max']}\n\n"
            await query.message.reply_text(msg, parse_mode="Markdown")
        else:
            await query.message.reply_text(f"❌ **ত্রুটি:** {res.get('error', 'সার্ভিস তালিকা পাওয়া যায়নি')}")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = smm_request({"action": "balance"})
    if "balance" in res:
        await update.message.reply_text(f"💵 **ব্যালেন্স:** {res['balance']} {res.get('currency', 'USD')}")
    else:
        await update.message.reply_text(f"❌ **ত্রুটি:** {res.get('error', 'ব্যালেন্স পাওয়া যায়নি')}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ অনুগ্রহ করে অর্ডার আইডি প্রদান করুন।\nযেমন: `/status 1242`", parse_mode="Markdown")
        return
    order_id = context.args[0]
    res = smm_request({"action": "status", "order": order_id})
    
    if "status" in res:
        msg = (
            f"📦 **অর্ডার স্ট্যাটাস (ID: {order_id}):**\n"
            f"• **স্ট্যাটাস:** {res.get('status')}\n"
            f"• **শুরুর সংখ্যা:** {res.get('start_count', 'N/A')}\n"
            f"• **বাকি আছে:** {res.get('remains', 'N/A')}\n"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ **ত্রুটি:** {res.get('error', 'অর্ডার পাওয়া যায়নি')}")

async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text("🔢 অনুগ্রহ করে **Service ID** টি লিখুন:")
    else:
        await update.message.reply_text("🔢 অনুগ্রহ করে **Service ID** টি লিখুন:")
    return SERVICE_ID

async def get_service_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['service_id'] = update.message.text
    await update.message.reply_text("🔗 এবার আপনার **লিংক (Link)** প্রদান করুন:")
    return LINK

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['link'] = update.message.text
    await update.message.reply_text("📊 কত **পরিমাণ (Quantity)** নিতে চান তা লিখুন:")
    return QUANTITY

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['quantity'] = update.message.text
    
    payload = {
        "action": "add",
        "service": context.user_data['service_id'],
        "link": context.user_data['link'],
        "quantity": context.user_data['quantity']
    }
    
    res = smm_request(payload)
    
    if "order" in res:
        await update.message.reply_text(f"✅ **অর্ডার সফল হয়েছে!**\n🎉 আপনার অর্ডার ID: `{res['order']}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ **অর্ডার ব্যর্থ হয়েছে!**\nকারণ: {res.get('error', 'অজানা সমস্যা')}")
        
    return ConversationHandler.END

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ অর্ডার প্রক্রিয়া বাতিল করা হয়েছে।")
    return ConversationHandler.END

def main():
    # Application Config with increased timeouts
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )

    # Conversation handler with per_message=False warning fix
    order_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_order, pattern="^new_order$"),
            CommandHandler("order", start_order)
        ],
        states={
            SERVICE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_service_id)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quantity)],
        },
        fallbacks=[CommandHandler("cancel", cancel_order)],
        per_message=False
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(order_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 SMM Bot is running...")
    app.run_polling(poll_interval=1.0)

if __name__ == "__main__":
    main()
