import os
import sys
import asyncio
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telethon import events
from angel_db import collection
from angel_db import settings_col, admin_col, extra_targets_col

load_dotenv()

# ================= Configuration =================
WOODCRAFT_URL = os.getenv("WOODCRAFT_URL")
NOOR_URL = os.getenv("NOOR_URL")
DEFAULT_ADMINS = [int(x) for x in os.getenv("DEFAULT_ADMINS", "").split(",") if x.strip()]

# ================== Functions ====================
async def add_target_channel(chat_id):
    if not extra_targets_col.find_one({"chat_id": chat_id}):
        extra_targets_col.insert_one({"chat_id": chat_id})

async def remove_target_channel(chat_id):
    extra_targets_col.delete_one({"chat_id": chat_id})

async def get_all_target_channels():
    return [doc["chat_id"] for doc in extra_targets_col.find()]

def is_admin(user_id):
    try:
        user_id = int(user_id)
        return user_id in DEFAULT_ADMINS or admin_col.find_one({"user_id": user_id})
    except:
        return False

def add_admin(user_id):
    try:
        user_id = int(user_id)
        admin_col.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id}},
            upsert=True
        )
    except Exception as e:
        print(f"Add admin error: {e}")

def remove_admin(user_id):
    try:
        user_id = int(user_id)
        admin_col.delete_one({"user_id": user_id})
    except Exception as e:
        print(f"Remove admin error: {e}")

# ============== Event Handlers ================
def setup_extra_handlers(woodcraft):
    @woodcraft.on(events.NewMessage(pattern=r'^/setdelay (\d+)$'))
    async def set_delay(event):
        if not is_admin(event.sender_id):
            return
        seconds = int(event.pattern_match.group(1))
        settings_col.update_one(
            {"key": "delay"},
            {"$set": {"value": seconds}},
            upsert=True
        )
        woodcraft.delay_seconds = seconds
        await event.reply(f"⏱️ Delay set: {seconds}s")

    @woodcraft.on(events.NewMessage(pattern=r'^/skip$'))
    async def skip_msg(event):
        if not is_admin(event.sender_id):
            return
        settings_col.update_one(
            {"key": "skip_next"},
            {"$set": {"value": True}},
            upsert=True
        )
        woodcraft.skip_next_message = True
        await event.reply("⏭️ The next message will be skipped")

    @woodcraft.on(events.NewMessage(pattern=r'^/resume$'))
    async def resume(event):
        if not is_admin(event.sender_id):
            return
        settings_col.update_one(
            {"key": "skip_next"},
            {"$set": {"value": False}},
            upsert=True
        )
        woodcraft.skip_next_message = False
        await event.reply("▶️ Forwarding is on")

    @woodcraft.on(events.NewMessage(pattern=r'^/woodcraft$'))
    async def woodcraft_handler(event):
        if not is_admin(event.sender_id):
            await event.reply("❌ Not allowed!")
            return

        caption = """
**🔧 All commands list 🌟**

```👉 Click to copy command```

/status `/status`  
```⚡ View bot status```

/setdelay [Sec] `/setdelay`
```⏱️ Set the delay time.```

/skip `/skip`  
```🛹 Skip to next message```

/resume `/resume`  
```🏹 Start forwarding```

/on `/on` 
```✅ Launch the bot```

/off `/off` 
```📴 Close the bot```

/addtarget [ID] `/addtarget`  
```✅ Add target```

/removetarget [ID] `/removetarget` 
```😡 Remove target```

/listtargets `/listtargets` 
```🆔 View Target ID```

```✅ How to Use:  
Reply to a user’s message and send the command:  
/addadmin```

/addadmin `/addadmin` 
```➕ Promote a user to admin (non-permanent).```

/removeadmin `/removeadmin`
```➖ Remove a user from admin who was added using /addadmin.```

 /listadmins `/listadmins`
 ```📋 View the list of all current admins (both from .env and database).```

/noor `/noor`
```👀 Shows a detailed status report including:```

/count `/count`
```📊 Total Forwarded Files```

/restart `/restart`
```♻️ Restarts the bot safely.```

🖤⃝💔 𝐖𝐎𝐎𝐃𝐜𝐫𝐚𝐟𝐭 🖤⃝💔
"""

        await woodcraft.send_file(
            event.chat_id,
            file=WOODCRAFT_URL,
            caption=caption,
            parse_mode='md'
        )

    @woodcraft.on(events.NewMessage(pattern=r'^/addadmin$'))
    async def handle_add_admin(event):
        if not is_admin(event.sender_id):
            return await event.reply("❌ You are not an admin.")
        if not event.is_reply:
            return await event.reply("Reply to the user you want to make admin.")
        target_msg = await event.get_reply_message()
        if target_msg:
            add_admin(target_msg.sender_id)
            await event.reply(f"✅ User `{target_msg.sender_id}` added as admin.")

    @woodcraft.on(events.NewMessage(pattern=r'^/removeadmin$'))
    async def handle_remove_admin(event):
        if not is_admin(event.sender_id):
            return await event.reply("❌ You are not an admin.")
        if not event.is_reply:
            return await event.reply("Reply to the admin you want to remove.")
        target_msg = await event.get_reply_message()
        if target_msg:
            remove_admin(target_msg.sender_id)
            await event.reply(f"❌ User `{target_msg.sender_id}` removed from admins.")

    @woodcraft.on(events.NewMessage(pattern=r'^/listadmins$'))
    async def list_admins(event):
        if not is_admin(event.sender_id):
            return await event.reply("❌ You are not an admin.")
        env_admins = [str(uid) for uid in DEFAULT_ADMINS]
        db_admins_cursor = admin_col.find({}, {"_id": 0, "user_id": 1})
        db_admins = [str(doc["user_id"]) for doc in db_admins_cursor]
        total_admins = env_admins + [uid for uid in db_admins if uid not in env_admins]
        if total_admins:
            admin_list = "\n".join([f"`{uid}`" for uid in total_admins])
            await event.reply(f"**👮 Admin List:**\n\n{admin_list}", parse_mode='md')
        else:
            await event.reply("No admins found.")

    @woodcraft.on(events.NewMessage(pattern=r'^/restart$'))
    async def restart_bot(event):
        if not is_admin(event.sender_id):
            return await event.reply("❌ You are not an admin.")
        await event.reply("♻️ Successfully restarting bot ✅")
        await asyncio.sleep(2)
        sys.exit(0)

    @woodcraft.on(events.NewMessage(pattern=r'^/noor$'))
    async def noor_handler(event):
        if not is_admin(event.sender_id):
            await event.reply("❌ You are not an admin.")
            return

        admins = [str(doc["user_id"]) for doc in admin_col.find()]
        targets = [str(doc["chat_id"]) for doc in extra_targets_col.find()]

        delay_data = settings_col.find_one({"key": "delay"})
        delay = delay_data["value"] if delay_data else 5

        skip_data = settings_col.find_one({"key": "skip_next"})
        skip_next = skip_data["value"] if skip_data else False

        current_time = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

        message = (
            "📦 **Bot status**\n\n"
            f"👑 **Admin ({len(admins)}):**\n`{', '.join(admins)}`\n\n"
            f"🎯 **Target Channel ({len(targets)}):**\n`{', '.join(targets)}`\n\n"
            f"⏱️ **Delay:** `{delay} Sec`\n"
            f"⏭️ **Skip to next message:** `{skip_next}`\n\n"
            f"🕒 **Last backup:** `{current_time}`\n\n"
            f"⫷〇❖◉◉◉ 𝐖𝐎𝐎𝐃𝐜𝐫𝐚𝐟𝐭 ◉◉◉❖〇⫸"
        )

        try:
            await woodcraft.send_file(
                entity=event.chat_id,
                file=NOOR_URL,
                caption=message,
                parse_mode='md',
                force_document=False
            )
        except Exception as e:
            await event.reply(f"Error: {e}")


# ============ Initial Settings Loader ============
async def load_initial_settings(woodcraft):
    delay = settings_col.find_one({"key": "delay"})
    woodcraft.delay_seconds = delay["value"] if delay else 5

    skip_next = settings_col.find_one({"key": "skip_next"})
    woodcraft.skip_next_message = skip_next["value"] if skip_next else False
