cat << 'EOF' > bot.py
import os
import uuid
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError

APP_ID = 32467601
API_HASH = "4c4f019c3eacb6794ec5cdcc8030595e"
TG_BOT_TOKEN = "8936917389:AAFj8Po7X3qTb52XzbkPcfrjCg3HpgCm-wA"
OWNER_ID = 7702879838

CHANNEL_USERNAME = "@Animes_Arise"

# Using user session string or fallback to bot session
client = TelegramClient('file_store_bot', APP_ID, API_HASH)

waiting_for_file = set()
waiting_for_image = set()
waiting_for_custom_batch = set()
waiting_for_batch_first = set()
waiting_for_batch_last = set()
BATCH_FIRST_MSG = {}

BATCH_STORAGE = {}
FILE_DATABASE = {}

async def check_channel_membership(user_id):
    if not CHANNEL_USERNAME or CHANNEL_USERNAME == "@YourChannelName":
        return True
    try:
        await client(GetParticipantRequest(channel=CHANNEL_USERNAME, user_id=user_id))
        return True
    except UserNotParticipantError:
        return False
    except Exception:
        return True

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    user_name = event.sender.first_name if event.sender else "User"
    args = event.raw_text.split()
    
    if len(args) > 1 and (args[1].startswith('file_') or args[1].startswith('batch_')):
        link_key = args[1]
        
        is_member = await check_channel_membership(user_id)
        if not is_member:
            join_markup = Button.inline("📢 Join Our Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
            await event.respond(
                "🔒 **Access Denied!**\n\n"
                "You must subscribe to our official channel to unlock and download this content. "
                "Please join the channel below and click the link again!",
                buttons=join_markup
            )
            return

        if link_key.startswith('file_') and link_key in FILE_DATABASE:
            original_msg = FILE_DATABASE[link_key]
            file_caption = original_msg.text or original_msg.message or "✨ *Here is your file!*"
            await event.respond("📂 **Here is your requested file:**")
            await client.send_file(event.chat_id, original_msg.media, caption=file_caption)
            return
            
        elif link_key.startswith('batch_') and link_key in BATCH_STORAGE:
            messages = BATCH_STORAGE[link_key]
            await event.respond(f"📦 **Here is your requested batch ({len(messages)} files):**")
            for msg in messages:
                caption = msg.text or msg.message or ""
                await client.send_file(event.chat_id, msg.media, caption=caption)
            return
        else:
            await event.respond("❌ **Oops!** This link has expired, is invalid, or no longer exists.")
            return

    welcome_caption = (
        f"✨ **Konnichiwa, {user_name}!** ✨\n\n"
        f"🌸 **Welcome to Mega File Store Bot!** 🌸\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Commands:**\n"
        f"1️⃣ /genlink - Single file link\n"
        f"2️⃣ /batch - Range batch (First & Last message link/forward)\n"
        f"3️⃣ /custombatch - Add files one by one with buttons\n"
        f"4️⃣ /setimage - Update banner (Admin)\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    
    img_file = 'anime.jpg' 
    try:
        if os.path.exists(img_file):
            await client.send_file(event.chat_id, img_file, caption=welcome_caption)
        else:
            await event.respond(welcome_caption)
    except Exception:
        await event.respond(welcome_caption)

@client.on(events.NewMessage(pattern='/genlink'))
async def genlink_handler(event):
    if event.sender_id != OWNER_ID:
        await event.respond("⛔ **Access Restricted:** You do not have permissions.")
        return

    waiting_for_custom_batch.discard(event.sender_id)
    waiting_for_batch_first.discard(event.sender_id)
    waiting_for_batch_last.discard(event.sender_id)
    waiting_for_file.add(event.sender_id)
    await event.respond("📂 **Send me the file, video, or document now!**")

# --- CUSTOM BATCH LOGIC ---
@client.on(events.NewMessage(pattern='/custombatch'))
async def custom_batch_handler(event):
    if event.sender_id != OWNER_ID:
        await event.respond("⛔ **Access Restricted:** You do not have permissions.")
        return

    waiting_for_file.discard(event.sender_id)
    waiting_for_batch_first.discard(event.sender_id)
    waiting_for_batch_last.discard(event.sender_id)
    
    setattr(event.client, f"custom_batch_list_{event.sender_id}", [])
    waiting_for_custom_batch.add(event.sender_id)
    
    buttons = [
        [Button.inline("⏸️ PAUSE", data="cb_pause"), Button.inline("🔗 GENERATE LINK", data="cb_generate")],
        [Button.inline("❌ CANCEL", data="cb_cancel")]
    ]
    await event.respond(
        "📦 **Stored Messages: 0**\n\n*Want to add another message? Just send it!*",
        buttons=buttons
    )

@client.on(events.CallbackQuery(data=b'cb_pause'))
async def cb_pause(event):
    if event.sender_id != OWNER_ID:
        return
    await event.answer("⏸️ Batch session paused. Send files anytime to resume.", alert=True)

@client.on(events.CallbackQuery(data=b'cb_generate'))
async def cb_generate(event):
    user_id = event.sender_id
    if user_id != OWNER_ID:
        return
    if user_id not in waiting_for_custom_batch:
        await event.answer("⚠️ No active custom batch session.", alert=True)
        return

    batch_messages = getattr(event.client, f"custom_batch_list_{user_id}", [])
    if not batch_messages:
        await event.answer("❌ No files added yet!", alert=True)
        return

    random_hash = uuid.uuid4().hex
    batch_key = f"batch_{random_hash}"
    BATCH_STORAGE[batch_key] = batch_messages
    waiting_for_custom_batch.discard(user_id)
    
    me = await client.get_me()
    link = f"https://t.me/{me.username}?start={batch_key}"
    await event.edit(f"✅ **Custom Batch Generated Successfully!**\n\n🔗 **Link:**\n`{link}`")

@client.on(events.CallbackQuery(data=b'cb_cancel'))
async def cb_cancel(event):
    user_id = event.sender_id
    if user_id != OWNER_ID:
        return
    waiting_for_custom_batch.discard(user_id)
    await event.edit("❌ Custom Batch cancelled.")


# --- RANGE BATCH LOGIC (/batch) ---
@client.on(events.NewMessage(pattern='/batch'))
async def batch_range_handler(event):
    if event.sender_id != OWNER_ID:
        await event.respond("⛔ **Access Restricted:** You do not have permissions.")
        return

    waiting_for_file.discard(event.sender_id)
    waiting_for_custom_batch.discard(event.sender_id)
    waiting_for_batch_last.discard(event.sender_id)
    
    waiting_for_batch_first.add(event.sender_id)
    await event.respond(
        "Forward The Batch **First Message** From your Batch Channel (With Forward Tag)...\n"
        "or Give Me Batch First Message **link** from your batch channel."
    )


@client.on(events.NewMessage(pattern='/cancel'))
async def cancel_handler(event):
    if event.sender_id != OWNER_ID:
        return
    waiting_for_custom_batch.discard(event.sender_id)
    waiting_for_batch_first.discard(event.sender_id)
    waiting_for_batch_last.discard(event.sender_id)
    waiting_for_file.discard(event.sender_id)
    waiting_for_image.discard(event.sender_id)
    await event.respond("❌ Current operation cancelled successfully.")

@client.on(events.NewMessage(pattern='/setimage'))
async def setimage_handler(event):
    if event.sender_id != OWNER_ID:
        await event.respond("⛔ **Unauthorized:** Admins only.")
        return
    waiting_for_image.add(event.sender_id)
    await event.respond("🖼️ **Please send your new welcome photo now!**")

@client.on(events.NewMessage(func=lambda e: e.is_private))
async def file_receiver(event):
    user_id = event.sender_id
    
    if user_id == OWNER_ID and user_id in waiting_for_image:
        if event.photo:
            waiting_for_image.remove(user_id)
            await event.download_media('anime.jpg')
            await event.respond("✅ **Success!** Welcome banner updated.")
            return
        else:
            await event.respond("⚠️ Please send a valid image/photo.")
            return

    # Handle Custom Batch Incoming Files
    if user_id in waiting_for_custom_batch:
        if event.text and event.text.startswith('/'):
            return
        if event.media:
            batch_list = getattr(event.client, f"custom_batch_list_{user_id}", [])
            batch_list.append(event.message)
            setattr(event.client, f"custom_batch_list_{user_id}", batch_list)
            
            buttons = [
                [Button.inline("⏸️ PAUSE", data="cb_pause"), Button.inline("🔗 GENERATE LINK", data="cb_generate")],
                [Button.inline("❌ CANCEL", data="cb_cancel")]
            ]
            await event.respond(
                f"📦 **Stored Messages: {len(batch_list)}**\n\n*Want to add another message? Just send it!*",
                buttons=buttons
            )
        else:
            await event.respond("⚠️ Please send a valid file/media.")
        return

    # Handle Range Batch First Message
    if user_id in waiting_for_batch_first:
        if event.text and event.text.startswith('/'):
            return
        
        msg_id = None
        chat_id = None
        
        if event.forward:
            if event.forward.chat:
                chat_id = event.forward.chat.id
                msg_id = event.forward.channel_post
        elif event.text and "t.me/" in event.text:
            try:
                parts = event.text.strip().split('/')
                msg_id = int(parts[-1])
                channel_username_or_id = parts[-2]
                if channel_username_or_id.isdigit():
                    chat_id = int(f"-100{channel_username_or_id}")
                else:
                    entity = await client.get_entity(f"@{channel_username_or_id}")
                    chat_id = entity.id
            except Exception:
                pass

        if not msg_id or not chat_id:
            await event.respond("❌ Invalid forward or link! Please forward the first message with tag or send correct message link.")
            return

        BATCH_FIRST_MSG[user_id] = {"chat_id": chat_id, "msg_id": msg_id}
        waiting_for_batch_first.discard(user_id)
        waiting_for_batch_last.add(user_id)
        
        await event.respond("Now Forward The Batch **Last Message** From your Batch Channel (With Forward Tag)...\nor Give Me Last Message **link**.")
        return

    # Handle Range Batch Last Message (Using client.get_messages instead of iter_messages to bypass restriction)
    if user_id in waiting_for_batch_last:
        if event.text and event.text.startswith('/'):
            return
        
        last_msg_id = None
        last_chat_id = None
        
        if event.forward:
            if event.forward.chat:
                last_chat_id = event.forward.chat.id
                last_msg_id = event.forward.channel_post
        elif event.text and "t.me/" in event.text:
            try:
                parts = event.text.strip().split('/')
                last_msg_id = int(parts[-1])
                channel_username_or_id = parts[-2]
                if channel_username_or_id.isdigit():
                    last_chat_id = int(f"-100{channel_username_or_id}")
                else:
                    entity = await client.get_entity(f"@{channel_username_or_id}")
                    last_chat_id = entity.id
            except Exception:
                pass

        if not last_msg_id or not last_chat_id:
            await event.respond("❌ Invalid forward or link for last message! Try again.")
            return

        first_data = BATCH_FIRST_MSG.get(user_id)
        waiting_for_batch_last.discard(user_id)

        if not first_data or first_data["chat_id"] != last_chat_id:
            await event.respond("❌ Chat ID mismatch or session expired. Start `/batch` again.")
            return

        start_id = first_data["msg_id"]
        end_id = last_msg_id
        if start_id > end_id:
            start_id, end_id = end_id, start_id

        # Fetch messages using get_messages batch method to avoid GetHistoryRequest bot restriction
        fetched_msgs = []
        try:
            msg_ids = list(range(start_id, end_id + 1))
            # Fetch in chunks of 100 to avoid limits
            for i in range(0, len(msg_ids), 100):
                chunk = msg_ids[i:i+100]
                messages = await client.get_messages(last_chat_id, ids=chunk)
                if messages:
                    for msg in messages:
                        if msg and msg.media:
                            fetched_msgs.append(msg)
        except Exception as e:
            await event.respond(f"❌ Error fetching messages: {str(e)}")
            return

        if not fetched_msgs:
            await event.respond("❌ No media found in this range!")
            return

        random_hash = uuid.uuid4().hex
        batch_key = f"batch_{random_hash}"
        BATCH_STORAGE[batch_key] = fetched_msgs
        
        me = await client.get_me()
        link = f"https://t.me/{me.username}?start={batch_key}"
        
        await event.respond(
            f"✅ **Batch Link Generated Successfully!**\n\n"
            f"📦 **Total Files:** `{len(fetched_msgs)}`\n"
            f"🔗 **Link:**\n`{link}`"
        )
        return

    if user_id in waiting_for_file:
        if event.text and event.text.startswith('/'):
            return
        try:
            random_hash = uuid.uuid4().hex
            file_key = f"file_{random_hash}"
            FILE_DATABASE[file_key] = event.message
            waiting_for_file.remove(user_id)
            
            me = await client.get_me()
            shareable_link = f"https://t.me/{me.username}?start={file_key}"
            await event.respond(f"✅ **Secure Link Generated:**\n`{shareable_link}`")
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
    else:
        if event.text and not event.text.startswith('/'):
            await event.respond("⚠️ Direct uploads disabled. Use `/genlink`, `/batch` or `/custombatch`.")

def main():
    print("Bot is running with distinct Batch (Range) and Custom Batch logic...")
    client.start(bot_token=TG_BOT_TOKEN)
    client.run_until_disconnected()

if __name__ == '__main__':
    main()
EOF