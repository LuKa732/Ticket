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
import time

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

        # رقم التكت المتسلسل
        current_number = get_ticket_number() + 1
        update_ticket_number(current_number)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        staff_role = discord.utils.get(guild.roles, id=STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(name=f"🎫-{current_number}", category=category, overwrites=overwrites)

        ticket_images = {
            "استفسار": "https://cdn.discordapp.com/attachments/1387472866060140674/1387913220819259542/608b0ab822b80764.png?ex=686063ea&is=685f126a&hm=1e03c21e0caddf8407050df218807257f1c42f8dcd70d95d88bbbe2f8e5a21ab&",
            "شكوى": "https://cdn.discordapp.com/attachments/1387472866060140674/1387913237172981821/8753aa7e0be43927.png?ex=686063ed&is=685f126d&hm=fa13562d79d231ea9f8ec35994d3e522841f3a50b71175e6109ad4a4f09b0a95&",
            "شكوى على إداري": "https://cdn.discordapp.com/attachments/1387472866060140674/1387913251525755152/dda1698fae207689.png?ex=686063f1&is=685f1271&hm=8b25b97f1e0994a3bc85b87bd897ec77f7ca63f4d1e5611bf1cb440eb799c84b&"
        }
        image_url = ticket_images.get(ticket_type)
        if image_url:
            await channel.send(image_url)

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

    # رسالة الترحيب النصية
    await channel.send("**مرحباً بك في نظام التذاكر في سيرفر WTX 🎟️**")

    # رسالة الصورة (Discord يعرضها تلقائياً)
    await channel.send("https://cdn.discordapp.com/attachments/1387472866060140674/1387914604319080528/52dddfcc96d3b2c9.png?ex=68606533&is=685f13b3&hm=61ec067d5ba5fc7825ed9c21a5dc9e7e85ee6ac3f93de51e1c43a1037a673d03&")

    # رسالة القائمة مع الأزرار (View)
    await channel.send(view=TicketSelectView())

ADMIN_ROLE_ID = 1387345452860571719

@bot.command()
async def ping(ctx):
    if any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles):
        start = time.monotonic()
        message = await ctx.send("جارٍ القياس...")
        end = time.monotonic()

        bot_latency = round(bot.latency * 1000)
        api_latency = round((end - start) * 1000)

        embed = discord.Embed(
            title="📡 Ping",
            description=f"** ping :** `{bot_latency}ms`\n** API :** `{api_latency}ms`",
            color=discord.Color.green()
        )
        await message.edit(content=None, embed=embed)
    else:
        await ctx.send("🚫 هذا الأمر مخصص للإدارة فقط.")

# ====== شغل البوت باستخدام التوكن ======
bot.run(os.getenv("TOKEN"))
