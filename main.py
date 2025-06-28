import discord
from discord.ext import commands
from discord.ui import View, Select
from discord import app_commands
from flask import Flask
from threading import Thread
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

STAFF_ROLE_ID = 1387345452860571719
TICKETS_CATEGORY_NAME = "🔰・Support"
PERIODIC_CHANNEL_ID = 1387920916138295448

# ======= دوال رقم التكت =======
def get_ticket_number():
    try:
        with open("ticket_number.txt", "r") as f:
            number = int(f.read())
    except FileNotFoundError:
        number = 0
    return number

def update_ticket_number(number):
    with open("ticket_number.txt", "w") as f:
        f.write(str(number))

# ====== keep_alive مع Flask ======
app = Flask('')

@app.route('/')
def home():
    return "✅ البوت يعمل"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run, daemon=True).start()

keep_alive()

# ====== أزرار إغلاق التكت ======
class CloseTicketButtons(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🗑️ حذف التكت", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=discord.Embed(description="🗑️ التكت سيتم حذفه الآن...", color=discord.Color.red()), ephemeral=True)
        await interaction.channel.delete()

    @discord.ui.button(label="↩️ إرجاع التكت", style=discord.ButtonStyle.secondary)
    async def reopen(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=discord.Embed(description="🔄 تم إرجاع التكت للعمل مجددًا.", color=discord.Color.green()))
        await interaction.channel.send(view=TicketManageButtons())

# ====== أزرار إدارة التكت ======
class TicketManageButtons(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.claimed_by = None

    @discord.ui.button(label="🎟️ استلام التكت", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id == STAFF_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message(embed=discord.Embed(description="❌ فقط الإدارة يمكنهم استلام التكت.", color=discord.Color.red()), ephemeral=True)
        if self.claimed_by:
            return await interaction.response.send_message(embed=discord.Embed(description=f"❌ التكت مستلم بالفعل من قبل {self.claimed_by.mention}.", color=discord.Color.red()), ephemeral=True)
        self.claimed_by = interaction.user
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ تم استلام التكت من قبل الإداري {interaction.user.mention}", color=discord.Color.green()))

    @discord.ui.button(label="🔓 فك الاستلام", style=discord.ButtonStyle.secondary)
    async def unclaim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.claimed_by or self.claimed_by != interaction.user:
            return await interaction.response.send_message(embed=discord.Embed(description="❌ فقط من استلم التكت يمكنه فك الاستلام.", color=discord.Color.red()), ephemeral=True)
        self.claimed_by = None
        await interaction.response.send_message(embed=discord.Embed(description="✅ تم فك استلامك للتكت.", color=discord.Color.green()))

    @discord.ui.button(label="📁 إغلاق التكت", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id == STAFF_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message(embed=discord.Embed(description="❌ فقط الإدارة يمكنهم إغلاق التكت.", color=discord.Color.red()), ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(description=f"📁 تم إغلاق التكت من قبل {interaction.user.mention}", color=discord.Color.orange()))
        await interaction.channel.send(view=CloseTicketButtons())

# ====== القائمة المنسدلة ======
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="تكت استفسار", description="لفتح تكت استفسار", value="استفسار"),
            discord.SelectOption(label="تكت شكوى", description="لفتح تكت شكوى", value="شكوى"),
            discord.SelectOption(label="تكت على إداري", description="لفتح تكت ضد إداري", value="شكوى على إداري"),
        ]
        super().__init__(placeholder="اختر نوع التكت", options=options)

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        guild = interaction.guild
        author = interaction.user
        category = discord.utils.get(guild.categories, name=TICKETS_CATEGORY_NAME)
        if not category:
            return await interaction.response.send_message("❌ لم أجد كاتيجوري التكتات.", ephemeral=True)
        if discord.utils.get(guild.channels, name=f"ticket-{author.id}"):
            return await interaction.response.send_message("⚠️ لديك تكت مفتوح بالفعل.", ephemeral=True)

        current_number = get_ticket_number() + 1
        update_ticket_number(current_number)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        staff_role = discord.utils.get(guild.roles, id=STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(name=f"🎫 - {current_number}", category=category, overwrites=overwrites)

        ticket_images = {
            "استفسار": "https://cdn.discordapp.com/attachments/1387472866060140674/1387913220819259542/608b0ab822b80764.png",
            "شكوى": "https://cdn.discordapp.com/attachments/1387472866060140674/1387913237172981821/8753aa7e0be43927.png",
            "شكوى على إداري": "https://cdn.discordapp.com/attachments/1387472866060140674/1387913251525755152/dda1698fae207689.png"
        }
        image_url = ticket_images.get(ticket_type)
        if image_url:
            await channel.send(embed=discord.Embed().set_image(url=image_url))

            await channel.send(
                content=f"""سلام عليكم {author.mention}
سوف يتم الرد خلال ثواني.. <@&{STAFF_ROLE_ID}>""",
                view=TicketManageButtons()
            )
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ تم إنشاء تذكرتك: {channel.mention}", color=discord.Color.green()), ephemeral=True)

class TicketSelectView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ====== أمر السلاش /ticket ======
@bot.tree.command(name="ticket", description="إرسال نظام التذاكر في قناة تختارها")
@app_commands.describe(channel="اختر القناة")
async def ticket_command(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ تم إرسال النظام في {channel.mention}", color=discord.Color.green()), ephemeral=True)
    await channel.send("**مرحباً بك في نظام التذاكر في سيرفر WTX 🎟️**")
    await channel.send(view=TicketSelectView())

# ====== الرسائل الدورية بإمبد ======
async def send_periodic_embed():
    await bot.wait_until_ready()
    channel = bot.get_channel(PERIODIC_CHANNEL_ID)
    while True:
        try:
            if channel:
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                embed = discord.Embed(
                    title="رسالة دورية من البوت",
                    description="هذه رسالة إمبد تُرسل كل دقيقة.",
                    color=discord.Color.blue()
                )
                embed.add_field(name="🕒 الوقت الآن", value=now, inline=False)
                embed.set_footer(text="نظام الإرسال التلقائي")
                await channel.send(embed=embed)
        except Exception as e:
            print(f"❌ خطأ في إرسال الرسالة الدورية: {e}")
        await asyncio.sleep(600)

# ====== تشغيل البوت ======
@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ تمت مزامنة {len(synced)} أمر Slash.")
    except Exception as e:
        print(f"❌ فشل في المزامنة: {e}")

    bot.loop.create_task(send_periodic_embed())

    # استبدل بالمعرّف الصحيح للقناة التي تريد إرسال الصور والقائمة فيها
    channel = bot.get_channel(123456789012345678)  # غيّر هذا لـ ID القناة

    if channel:
        embed = discord.Embed()
        embed.set_image(url="https://cdn.discordapp.com/attachments/1387472866060140674/1387914604319080528/52dddfcc96d3b2c9.png")
        await channel.send(embed=embed)

        await channel.send(view=TicketSelectView())

# ====== شغل البوت باستخدام التوكن ======
bot.run(os.getenv("TOKEN"))
