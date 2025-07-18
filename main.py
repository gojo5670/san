import logging
import requests
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "7814043110:AAFcxulQdXjDNpDj5zCDRsVi_xbi-kFE0KM"
API_BASE_URL = "https://keeping-word-contain-johnson.trycloudflare.com"  # Change this if your API is hosted elsewhere
ADMIN_IDS = [7013965994]  # Add your Telegram user ID here
CONFIG_FILE = "bot_config.json"

# Default configuration
default_config = {
    "enabled_groups": {},
    "admin_ids": ADMIN_IDS
}

# Load or create configuration
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
                # Make sure admin_ids is properly initialized from the file
                if "admin_ids" not in config_data or not config_data["admin_ids"]:
                    config_data["admin_ids"] = ADMIN_IDS
                return config_data
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    # Create default config file if it doesn't exist
    default_conf = {
        "enabled_groups": {},
        "admin_ids": ADMIN_IDS
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(default_conf, f, indent=4)
    
    return default_conf

# Save configuration
def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

# Load configuration
config = load_config()

# Check if user is admin
def is_admin(user_id):
    # Convert to integer for comparison
    user_id = int(user_id)
    admin_ids = config.get("admin_ids", ADMIN_IDS)
    
    # Debug log to see what's happening
    logger.info(f"Checking if user {user_id} is admin. Admin IDs: {admin_ids}")
    
    result = user_id in admin_ids
    logger.info(f"Admin check result for {user_id}: {result}")
    return result

# Check if bot is enabled in a group
def is_enabled(chat_id):
    chat_id_str = str(chat_id)
    # DMs with the bot are only enabled for admins
    if chat_id > 0:
        return False  # Will check admin status separately
    
    return chat_id_str in config.get("enabled_groups", {}) and config["enabled_groups"][chat_id_str]

# Reload configuration - call this before checking permissions
def reload_config():
    global config
    config = load_config()
    logger.info(f"Config reloaded: {config}")
    
    # Ensure admin_ids is a list and contains at least the default admin
    if "admin_ids" not in config or not config["admin_ids"]:
        config["admin_ids"] = ADMIN_IDS
        save_config(config)
        logger.warning(f"Admin IDs were missing, reset to defaults: {ADMIN_IDS}")

# Command handlers
async def start_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check if in private chat and if user is admin
    if chat_id > 0:  # Private chat
        if not is_admin(user_id):
            await update.message.reply_text(
                "⛔ This bot is only available for administrators in private chats.\n"
                "Please use the bot in a group where it's enabled."
            )
            return
    # Check if in a group and if the bot is enabled for this group
    elif not is_enabled(chat_id):
        if is_admin(user_id):
            await update.message.reply_text(
                "Bot is currently disabled in this group. Use /enable to enable it."
            )
        return
    
    await update.message.reply_text(
        "Welcome to the User Search Bot!\n\n"
        "You can search for users by:\n"
        "• Mobile number: /mobile <number>\n"
        "• Aadhaar: /aadhaar <number>\n"
        "• Email: /email <email>\n\n"
        "Use /help to see all available commands."
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    is_user_admin = is_admin(user_id)
    
    # Check if in private chat and if user is admin
    if chat_id > 0:  # Private chat
        if not is_user_admin:
            await update.message.reply_text("⛔ This bot is only available for administrators in private chats.")
            return
    # Check if in a group and if the bot is enabled for this group
    elif not is_enabled(chat_id):
        if is_user_admin:
            await update.message.reply_text("Bot is currently disabled in this group. Use /enable to enable it.")
        return
    
    basic_help = (
        "Available commands:\n\n"
        "/mobile <number> - Search by mobile number\n"
        "/aadhaar <number> - Search by Aadhaar number\n"
        "/email <email> - Search by email\n"
        "/start - Show welcome message\n"
        "/help - Show this help message"
    )
    
    admin_help = (
        "\n\n<b>Admin Commands:</b>\n"
        "/enable - Enable bot in this group\n"
        "/disable - Disable bot in this group\n"
        "/addadmin <user_id> - Add a new admin\n"
        "/removeadmin <user_id> - Remove an admin\n"
        "/status - Show bot status"
    )
    
    if is_user_admin:
        await update.message.reply_text(basic_help + admin_help, parse_mode="HTML")
    else:
        await update.message.reply_text(basic_help)

async def enable_command(update: Update, context: CallbackContext) -> None:
    """Enable the bot in a group."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_title = update.effective_chat.title
    
    logger.info(f"Enable command called by user {user_id} in chat {chat_id}")
    
    # Reload config before checking permissions
    reload_config()
    
    # Only admins can enable the bot
    if not is_admin(user_id):
        logger.warning(f"Permission denied: User {user_id} tried to enable bot but is not admin")
        await update.message.reply_text(f"⛔ You don't have permission to use this command. Your ID: {user_id}")
        return
    
    # Can only be used in groups
    if chat_id > 0:
        await update.message.reply_text("This command can only be used in groups.")
        return
    
    # Enable the bot for this group
    chat_id_str = str(chat_id)
    config["enabled_groups"][chat_id_str] = True
    if save_config(config):
        logger.info(f"Bot enabled in group {chat_id} ({chat_title}) by admin {user_id}")
        await update.message.reply_text(f"✅ Bot has been enabled in {chat_title}.")
    else:
        logger.error(f"Failed to save config when enabling bot in group {chat_id}")
        await update.message.reply_text("Failed to save configuration.")

async def disable_command(update: Update, context: CallbackContext) -> None:
    """Disable the bot in a group."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_title = update.effective_chat.title
    
    logger.info(f"Disable command called by user {user_id} in chat {chat_id}")
    
    # Reload config before checking permissions
    reload_config()
    
    # Only admins can disable the bot
    if not is_admin(user_id):
        logger.warning(f"Permission denied: User {user_id} tried to disable bot but is not admin")
        await update.message.reply_text(f"⛔ You don't have permission to use this command. Your ID: {user_id}")
        return
    
    # Can only be used in groups
    if chat_id > 0:
        await update.message.reply_text("This command can only be used in groups.")
        return
    
    # Disable the bot for this group
    chat_id_str = str(chat_id)
    config["enabled_groups"][chat_id_str] = False
    if save_config(config):
        logger.info(f"Bot disabled in group {chat_id} ({chat_title}) by admin {user_id}")
        await update.message.reply_text(f"❌ Bot has been disabled in {chat_title}.")
    else:
        logger.error(f"Failed to save config when disabling bot in group {chat_id}")
        await update.message.reply_text("Failed to save configuration.")

async def add_admin_command(update: Update, context: CallbackContext) -> None:
    """Add a new admin."""
    user_id = update.effective_user.id
    
    # Reload config before checking permissions
    reload_config()
    
    # Only admins can add admins
    if not is_admin(user_id):
        await update.message.reply_text(f"You don't have permission to use this command. Your ID: {user_id}")
        return
    
    # Check if user ID is provided
    if not context.args:
        await update.message.reply_text("Please provide a user ID. Example: /addadmin 123456789")
        return
    
    try:
        new_admin_id = int(context.args[0])
        
        # Add the new admin if not already an admin
        if new_admin_id not in config.get("admin_ids", []):
            config.setdefault("admin_ids", []).append(new_admin_id)
            if save_config(config):
                await update.message.reply_text(f"User {new_admin_id} has been added as an admin.")
            else:
                await update.message.reply_text("Failed to save configuration.")
        else:
            await update.message.reply_text(f"User {new_admin_id} is already an admin.")
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.")

async def remove_admin_command(update: Update, context: CallbackContext) -> None:
    """Remove an admin."""
    user_id = update.effective_user.id
    
    # Reload config before checking permissions
    reload_config()
    
    # Only admins can remove admins
    if not is_admin(user_id):
        await update.message.reply_text(f"You don't have permission to use this command. Your ID: {user_id}")
        return
    
    # Check if user ID is provided
    if not context.args:
        await update.message.reply_text("Please provide a user ID. Example: /removeadmin 123456789")
        return
    
    try:
        admin_id = int(context.args[0])
        
        # Cannot remove yourself if you're the only admin
        if admin_id == user_id and len(config.get("admin_ids", [])) <= 1:
            await update.message.reply_text("Cannot remove yourself as you are the only admin.")
            return
        
        # Remove the admin
        if admin_id in config.get("admin_ids", []):
            config["admin_ids"].remove(admin_id)
            if save_config(config):
                await update.message.reply_text(f"User {admin_id} has been removed from admins.")
            else:
                await update.message.reply_text("Failed to save configuration.")
        else:
            await update.message.reply_text(f"User {admin_id} is not an admin.")
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.")

async def status_command(update: Update, context: CallbackContext) -> None:
    """Show bot status."""
    user_id = update.effective_user.id
    
    # Reload config before checking permissions
    reload_config()
    
    # Only admins can see status
    if not is_admin(user_id):
        await update.message.reply_text(f"You don't have permission to use this command. Your ID: {user_id}")
        return
    
    # Get enabled groups
    enabled_groups = [group_id for group_id, enabled in config.get("enabled_groups", {}).items() if enabled]
    
    # Get admins
    admins = config.get("admin_ids", [])
    
    status_message = (
        "<b>Bot Status</b>\n\n"
        f"<b>Enabled Groups:</b> {len(enabled_groups)}\n"
        f"<b>Admins:</b> {len(admins)}\n"
        f"<b>Admin IDs:</b> {', '.join(map(str, admins))}"
    )
    
    await update.message.reply_text(status_message, parse_mode="HTML")

async def search_mobile(update: Update, context: CallbackContext) -> None:
    """Search by mobile number."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check if in private chat and if user is admin
    if chat_id > 0:  # Private chat
        if not is_admin(user_id):
            await update.message.reply_text("⛔ This bot is only available for administrators in private chats.")
            return
    # Check if in a group and if the bot is enabled for this group
    elif not is_enabled(chat_id):
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a mobile number. Example: /mobile 9876543210")
        return
    
    mobile = context.args[0]
    await perform_search(update, "mobile", mobile)

async def search_aadhaar(update: Update, context: CallbackContext) -> None:
    """Search by Aadhaar number."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check if in private chat and if user is admin
    if chat_id > 0:  # Private chat
        if not is_admin(user_id):
            await update.message.reply_text("⛔ This bot is only available for administrators in private chats.")
            return
    # Check if in a group and if the bot is enabled for this group
    elif not is_enabled(chat_id):
        return
    
    if not context.args:
        await update.message.reply_text("Please provide an Aadhaar number. Example: /aadhaar 123456789012")
        return
    
    aadhaar = context.args[0]
    await perform_search(update, "id", aadhaar)

async def search_email(update: Update, context: CallbackContext) -> None:
    """Search by email."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check if in private chat and if user is admin
    if chat_id > 0:  # Private chat
        if not is_admin(user_id):
            await update.message.reply_text("⛔ This bot is only available for administrators in private chats.")
            return
    # Check if in a group and if the bot is enabled for this group
    elif not is_enabled(chat_id):
        return
    
    if not context.args:
        await update.message.reply_text("Please provide an email. Example: /email user@example.com")
        return
    
    email = context.args[0]
    await perform_search(update, "email", email)

async def handle_text(update: Update, context: CallbackContext) -> None:
    """Handle text messages."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check if in private chat and if user is admin
    if chat_id > 0:  # Private chat
        if not is_admin(user_id):
            await update.message.reply_text("⛔ This bot is only available for administrators in private chats.")
            return
    # Check if in a group and if the bot is enabled for this group
    elif not is_enabled(chat_id):
        return
    
    # Provide help for text messages
    await update.message.reply_text(
        "Please use one of these commands to search:\n\n"
        "/mobile <number> - Search by mobile number\n"
        "/aadhaar <number> - Search by Aadhaar number\n"
        "/email <email> - Search by email\n\n"
        "For more help, use /help command."
    )

async def perform_search(update: Update, search_type: str, value: str) -> None:
    """Perform the search and format the results."""
    try:
        response = requests.get(f"{API_BASE_URL}/search/{search_type}", params={"value": value})
        
        if response.status_code == 200:
            results = response.json()
            if not results:
                await update.message.reply_text(f"No results found for {search_type}: {value}")
                return
            
            # Send header message
            await update.message.reply_text(f"<b>Found {len(results)} results for {search_type}: {value}</b>", parse_mode="HTML")
            
            # Process results in batches to avoid message length limit
            MAX_MESSAGE_LENGTH = 3800  # Telegram limit is 4096, leaving room for formatting
            current_message = ""
            
            for i, result in enumerate(results):
                result_text = format_result(result, i+1)
                
                # If adding this result would make the message too long, send current message and start a new one
                if len(current_message) + len(result_text) + 30 > MAX_MESSAGE_LENGTH:
                    if current_message:
                        await update.message.reply_text(current_message, parse_mode="HTML")
                    current_message = result_text
                else:
                    if current_message:
                        current_message += "\n" + "—" * 20 + "\n\n" + result_text
                    else:
                        current_message = result_text
            
            # Send any remaining results
            if current_message:
                await update.message.reply_text(current_message, parse_mode="HTML")
                
        else:
            error = response.json().get("error", "Unknown error")
            await update.message.reply_text(f"Error: {error}")
    
    except Exception as e:
        logger.error(f"Error performing search: {e}")
        await update.message.reply_text("An error occurred while searching. Please try again later.")

def format_result(result: dict, index: int) -> str:
    """Format a single result for display."""
    message = f"<b>Result #{index}</b>\n\n"
    
    # Add priority fields first
    if "name" in result:
        message += f"<b>Name:</b> {result['name']}\n"
    if "mobile" in result:
        message += f"<b>Mobile:</b> {result['mobile']}\n"
    if "alt" in result:
        message += f"<b>Alt Number:</b> {result['alt']}\n"
    if "id" in result:
        message += f"<b>ID:</b> {result['id']}\n"
    
    # Add remaining fields
    for key, value in result.items():
        if key not in ["name", "mobile", "alt", "id"]:
            # Format the key with proper capitalization
            formatted_key = key.replace("_", " ").title()
            message += f"<b>{formatted_key}:</b> {value}\n"
    
    return message

async def myid_command(update: Update, context: CallbackContext) -> None:
    """Show the user's Telegram ID."""
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    chat_id = update.effective_chat.id
    is_user_admin = is_admin(user_id)
    
    # The myid command is always available to everyone
    # This helps users know their ID to request admin access
    
    admin_status = "You are an admin of this bot." if is_user_admin else "You are not an admin of this bot."
    
    if chat_id > 0 and not is_user_admin:
        admin_status += "\nNote: This bot is only available for administrators in private chats."
    
    await update.message.reply_text(
        f"Your Telegram information:\n\n"
        f"Name: {user_name}\n"
        f"User ID: <code>{user_id}</code>\n\n"
        f"{admin_status}\n\n"
        f"If you need admin access, ask an existing admin to run:\n"
        f"<code>/addadmin {user_id}</code>",
        parse_mode="HTML"
    )

async def reset_admin_command(update: Update, context: CallbackContext) -> None:
    """Reset admin list to default (emergency recovery)."""
    user_id = update.effective_user.id
    
    # This command can only be used in private chat with the bot
    if update.effective_chat.type != "private":
        await update.message.reply_text("For security reasons, this command can only be used in private chat with the bot.")
        return
    
    # Check if the user provided the correct reset code
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "⚠️ This is an emergency command to reset admin permissions.\n\n"
            "To reset admin list to default, use:\n"
            "/resetadmin RESET_CODE\n\n"
            "Where RESET_CODE is the bot token's first 8 characters."
        )
        return
    
    reset_code = context.args[0]
    token_prefix = BOT_TOKEN.split(':')[0][:8]
    
    if reset_code != token_prefix:
        logger.warning(f"Failed admin reset attempt by user {user_id} with incorrect code")
        await update.message.reply_text("Incorrect reset code.")
        return
    
    # Reset admin list to default
    global config
    config["admin_ids"] = ADMIN_IDS
    if save_config(config):
        logger.warning(f"Admin list reset to default by user {user_id}")
        await update.message.reply_text(
            "✅ Admin list has been reset to default.\n\n"
            f"Default admin ID: {ADMIN_IDS[0]}"
        )
    else:
        logger.error(f"Failed to save config during admin reset by user {user_id}")
        await update.message.reply_text("Failed to save configuration.")

def main() -> None:
    """Start the bot."""
    # Initialize configuration
    global config
    config = load_config()
    
    # Force reset admin IDs to default on startup to ensure access
    if ADMIN_IDS and ADMIN_IDS[0] not in config.get("admin_ids", []):
        logger.warning(f"Default admin {ADMIN_IDS[0]} not in config, adding...")
        config.setdefault("admin_ids", []).append(ADMIN_IDS[0])
        save_config(config)
    
    logger.info(f"Bot starting with config: {config}")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("mobile", search_mobile))
    application.add_handler(CommandHandler("aadhaar", search_aadhaar))
    application.add_handler(CommandHandler("email", search_email))
    application.add_handler(CommandHandler("myid", myid_command))
    
    # Add admin command handlers
    application.add_handler(CommandHandler("enable", enable_command))
    application.add_handler(CommandHandler("disable", disable_command))
    application.add_handler(CommandHandler("addadmin", add_admin_command))
    application.add_handler(CommandHandler("removeadmin", remove_admin_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("resetadmin", reset_admin_command))
    
    # Remove the callback query handler for buttons
    
    # Add message handler for text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start the Bot
    print("Starting bot...")
    application.run_polling()

if __name__ == "__main__":
    main() 
