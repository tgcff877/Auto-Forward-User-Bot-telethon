import os
from dotenv import load_dotenv
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from settings import setup_extra_handlers, load_initial_settings, is_admin, DEFAULT_ADMINS
from settings import get_all_target_channels, add_target_channel, remove_target_channel

load_dotenv()
# ===== WOODcraft ==== SudoR2spr ==== #
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
PORT = int(os.getenv("PORT", 8080))
# ===== WOODcraft ==== SudoR2spr ==== #

woodcraft = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
app = Flask(__name__)
forwarding_enabled = True

## === MongoDB সেটআপ === WOODcraft ==== SudoR2spr ==== # 
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["forwardBot"]
collection = db["forwarded_files"]
collection.create_index([("message_id", 1), ("target_id", 1)], unique=True)

async def is_forwarded_for_target(msg_id, target_id):
    return collection.find_one({"message_id": msg_id, "target_id": target_id}) is not None

async def mark_as_forwarded_for_target(msg_id, target_id):
    try:
        collection.insert_one({"message_id": msg_id, "target_id": target_id})
    except DuplicateKeyError:
        pass

async def send_without_tag(original_msg):
    try:
        targets = await get_all_target_channels()
        if not targets:
            print("⚠️ There is no target channel!")
            return False

        forwarded = False
        for target in targets:
            if await is_forwarded_for_target(original_msg.id, target):
                print(f"⏩ Skip: {original_msg.id} (Target: {target})")
                continue

            print(f"➡️ Forwarding: {original_msg.id} to {target}")
            
            # ===== WOODcraft ==== SudoR2spr ==== মিডিয়া মেসেজ হ্যান্ডলিং === # 
            if original_msg.media:
                await woodcraft.send_file(
                    entity=target,
                    file=original_msg.media,
                    caption=original_msg.text,
                    silent=True
                )
            # ===== WOODcraft ==== SudoR2spr ==== টেক্সট মেসেজ হ্যান্ডলিং === #
            else:
                await woodcraft.send_message(
                    entity=target,
                    message=original_msg.text,
                    formatting_entities=original_msg.entities,
                    silent=True
                )
            
            await mark_as_forwarded_for_target(original_msg.id, target)
            forwarded = True
            await asyncio.sleep(woodcraft.delay_seconds)

        return forwarded
    except FloodWaitError as e:
        print(f"⏳ FloodWait: {e.seconds} সেকেন্ড অপেক্ষা করুন")
        await asyncio.sleep(e.seconds + 5)
        return await send_without_tag(original_msg)
    except Exception as e:
        print(f"🚨 Error: {str(e)}")
        return False

async def forward_old_messages():
    print("⏪ Start forwarding old messages...")
    async for message in woodcraft.iter_messages(SOURCE_CHAT_ID, reverse=True):
        if forwarding_enabled:
            await send_without_tag(message)
            await asyncio.sleep(woodcraft.delay_seconds)

async def forward_old_messages_to_new_target(new_target_id):
    print(f"🔄 Forward to new target: {new_target_id}")
    async for message in woodcraft.iter_messages(SOURCE_CHAT_ID, reverse=True):
        if await is_forwarded_for_target(message.id, new_target_id):
            continue
        try:
            # ===== WOODcraft ==== SudoR2spr ==== মিডিয়া মেসেজ === #
            if message.media:
                await woodcraft.send_file(
                    new_target_id,
                    file=message.media,
                    caption=message.text,
                    silent=True
                )
            # ===== WOODcraft ==== SudoR2spr ==== টেক্সট মেসেজ === #
            else:
                await woodcraft.send_message(
                    new_target_id,
                    message.text,
                    formatting_entities=message.entities,
                    silent=True
                )
            await mark_as_forwarded_for_target(message.id, new_target_id)
            print(f"✅ {message.id} -> {new_target_id}")
            await asyncio.sleep(woodcraft.delay_seconds)
        except FloodWaitError as e:
            print(f"⏳ FloodWait: {e.seconds}s অপেক্ষা")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"🚨 Error: {str(e)}")
            break

@woodcraft.on(events.NewMessage(pattern=r'^/status$'))
async def status(event):
    if not is_admin(event.sender_id):
        await event.reply("❌ No permission!")
        return
    status = "Active ✅" if forwarding_enabled else "inactive ❌"
    await event.reply(f"◉ Status: {status}\n◉ Dealy: {woodcraft.delay_seconds}s\n◉ Skip: {woodcraft.skip_next_message}")

@woodcraft.on(events.NewMessage(pattern=r'^/off$'))
async def off_handler(event):
    global forwarding_enabled
    if not is_admin(event.sender_id):
        return
    forwarding_enabled = False
    await event.reply("❌ Forwarding is off")

@woodcraft.on(events.NewMessage(pattern=r'^/on$'))
async def on_handler(event):
    global forwarding_enabled
    if not is_admin(event.sender_id):
        return
    forwarding_enabled = True
    await event.reply("✅ Forwarding is on")

@woodcraft.on(events.NewMessage(pattern=r'^/addtarget\s+(-?\d+)$'))
async def addtarget_handler(event):
    if not is_admin(event.sender_id):
        await event.reply("❌ No permission!")
        return
    chat_id = int(event.pattern_match.group(1))
    await add_target_channel(chat_id)
    await event.reply(f"✅ Add target: `{chat_id}`")
    await forward_old_messages_to_new_target(chat_id)

@woodcraft.on(events.NewMessage(pattern=r'^/removetarget\s+(-?\d+)$'))
async def removetarget_handler(event):
    if not is_admin(event.sender_id):
        return
    chat_id = int(event.pattern_match.group(1))
    await remove_target_channel(chat_id)
    await event.reply(f"❌ Target Remove: `{chat_id}`")

@woodcraft.on(events.NewMessage(pattern=r'^/listtargets$'))
async def list_targets_handler(event):
    targets = await get_all_target_channels()
    msg = "**🎯 Target channel:**\n" + "\n".join(f"`{tid}`" for tid in targets) if targets else "No target!"
    await event.reply(msg)

@woodcraft.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def new_message_handler(event):
    global forwarding_enabled
    if forwarding_enabled and not woodcraft.skip_next_message:
        await asyncio.sleep(woodcraft.delay_seconds)
        await send_without_tag(event.message)
    elif woodcraft.skip_next_message:
        print("⏭️ Message skipped.")
        woodcraft.skip_next_message = False

@app.route("/")
def home():
    return "🤖 Activate the Angel bot!", 200

async def main():
    await woodcraft.start()
    print("✅ Successfully Launch the bot!")
    await load_initial_settings(woodcraft)
    setup_extra_handlers(woodcraft)
    
    targets = await get_all_target_channels()
    if not targets:
        print("⚠️ /addtarget Use")
    
    asyncio.create_task(forward_old_messages())
    await woodcraft.run_until_disconnected()

if __name__ == "__main__":
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": PORT}).start()
    asyncio.run(main())
