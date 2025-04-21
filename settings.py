import os
from dotenv import load_dotenv
from telethon import events
from pymongo import MongoClient

load_dotenv()
# ===== WOODcraft ==== SudoR2spr ==== #

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["forwardBot"]
settings_col = db["settings"]
admin_col = db["admins"]
extra_targets_col = db["extra_targets"]

# ============== Your user ID ============= #
# DEFAULT_ADMINS = [6112735328]  Your user ID #
DEFAULT_ADMINS = [int(x) for x in os.getenv("DEFAULT_ADMINS", "").split(",") if x.strip()]
# ============== Your user ID ============= #

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
        admin_col.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
    except Exception as e:
        print(f"Add admin error: {e}")

def remove_admin(user_id):
    try:
        user_id = int(user_id)
        admin_col.delete_one({"user_id": user_id})
    except Exception as e:
        print(f"Remove admin error: {e}")

def setup_extra_handlers(woodcraft):
    @woodcraft.on(events.NewMessage(pattern=r'^/setdelay (\d+)$'))
    async def set_delay(event):
        if not is_admin(event.sender_id):
            return
        seconds = int(event.pattern_match.group(1))
        settings_col.update_one({"key": "delay"}, {"$set": {"value": seconds}}, upsert=True)
        woodcraft.delay_seconds = seconds
        await event.reply(f"⏱️ Delay set: {seconds}s")

    @woodcraft.on(events.NewMessage(pattern=r'^/skip$'))
    async def skip_msg(event):
        if not is_admin(event.sender_id):
            return
        settings_col.update_one({"key": "skip_next"}, {"$set": {"value": True}}, upsert=True)
        woodcraft.skip_next_message = True
        await event.reply("⏭️ The next message will be skipped")

    @woodcraft.on(events.NewMessage(pattern=r'^/resume$'))
    async def resume(event):
        if not is_admin(event.sender_id):
            return
        settings_col.update_one({"key": "skip_next"}, {"$set": {"value": False}}, upsert=True)
        woodcraft.skip_next_message = False
        await event.reply("▶️ Forwarding is on")

    # ===== WOODcraft ==== SudoR2spr ==== #
    @woodcraft.on(events.NewMessage(pattern=r'^/woodcraft$'))
    async def woodcraft_handler(event):
        if not is_admin(event.sender_id):
            await event.reply("❌ Not allowed!")
            return
            
        help_text = """
        **All commands list 🌟** 

        ```👉 Click to copy command```

        `/status` 
        ```⚡ View bot status```  
        `/setdelay [Sec]` 
        ```⏱️ Set the delay time.```  
        `/skip` 
        ```🛹 Skip to next message```  
        `/resume` 
        ```🏹 Start forwarding```  
        `/on` 
        ```✅ Launch the bot```   
        `/off` 
        ```📴 Close the bot``` 
        `/addtarget [ID]` 
        ```✅ Add target```  
        `/removetarget [ID]` 
        ```😡 Remove target```  
        `/listtargets` 
        ```🆔 View Target ID```

        ```🖤⃝💔 𝐖𝐎𝐎𝐃𝐜𝐫𝐚𝐟𝐭 🖤⃝💔```
        """
        await event.reply(help_text, parse_mode='md')

    @woodcraft.on(events.NewMessage(pattern=r'^/addadmin$'))
    async def handle_add_admin(event):
        if not is_admin(event.sender_id):
            return await event.reply("❌ You are not an admin.")
        if not event.is_reply:
            return await event.reply("Reply to the user you want to make admin.")
        target_user_id = event.message.reply_to_msg_id
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

async def load_initial_settings(woodcraft):
    # ===== WOODcraft ==== SudoR2spr ==== #
    delay = settings_col.find_one({"key": "delay"})
    woodcraft.delay_seconds = delay["value"] if delay else 5
    
    skip_next = settings_col.find_one({"key": "skip_next"})
    woodcraft.skip_next_message = skip_next["value"] if skip_next else False
