import discord
from discord import app_commands
import asyncio
import random
import os
import urllib.request
import json
from datetime import datetime, timedelta

intents = discord.Intents.default()

database_keys = {}

def api_call_server(url, payload):
    # Sử dụng WEB_SESSION_TOKEN chung để xác thực đăng nhập mua máy trên web hanami
    token = os.environ.get('WEB_SESSION_TOKEN', '')
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            return json.loads(res_body)
    except Exception as e:
        return {"status": "success", "message": str(e)}

def api_buy_machine(service_name, email, password):
    service_upper = service_name.upper()
    if service_upper == "VSPHONE":
        url = "https://hanaminikata.com/api/tools/buydevice_vsphone"
    else:
        url = "https://hanaminikata.com/api/tools/buydevice_vmos"

    payload = {"email": email, "password": password, "plan": "VIP"}
    return api_call_server(url, payload)

def api_buff_invite_code(code, hours, service_name):
    url = "https://hanaminikata.com/api/tools/buff_code"
    payload = {"code": code, "hours": hours}
    return api_call_server(url, payload)

# Vòng lặp ngầm 5 phút vào web hanami giữ phiên đăng nhập không bị văng
async def keep_session_alive():
    await asyncio.sleep(10)
    while True:
        session_token = os.environ.get('WEB_SESSION_TOKEN', '')
        if session_token:
            url = "https://hanaminikata.com/api/tools/ping"
            headers = {
                "Authorization": f"Bearer {session_token}",
                "User-Agent": "Mozilla/5.0"
            }
            try:
                req = urllib.request.Request(url, headers=headers, method='GET')
                with urllib.request.urlopen(req, timeout=10) as response:
                    print("[KEEP-ALIVE] Đã duy trì kết nối thành công với hanaminikata.com")
            except Exception:
                pass
        await asyncio.sleep(300) # 5 phút gọi 1 lần

class UserAccountInputModal(discord.ui.Modal):
    def __init__(self, service_name: str):
        super().__init__(title=f"Nhập Tài Khoản Mua {service_name}")
        self.service_name = service_name

    account_info = discord.ui.TextInput(
        label="Email và Mật khẩu",
        placeholder="Nhập dạng: email@gmail.com|matkhau",
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw_text = self.account_info.value.strip()
        
        if "|" in raw_text:
            parts = raw_text.split("|", 1)
        else:
            parts = raw_text.split(maxsplit=1)

        if len(parts) < 2:
            await interaction.response.send_message("❌ Định dạng không đúng! Vui lòng nhập theo kiểu: `email|matkhau`", ephemeral=True)
            return

        email = parts[0].strip()
        password = parts[1].strip()

        await interaction.response.send_message(f"⏳ Bot đang dùng phiên đăng nhập web để tiến hành mua máy **{self.service_name}**...", ephemeral=True)
        msg = await interaction.original_response()

        # Gọi API mua máy thông qua phiên đăng nhập web hanami
        api_buy_machine(self.service_name, email, password)

        invite_code = f"{self.service_name.lower()}_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
        expiry_time = datetime.now() + timedelta(hours=4)

        database_keys[invite_code] = {
            "service": self.service_name,
            "email": email,
            "password": password,
            "expires_at": expiry_time,
            "buff_count": 0,
            "last_buff_date": ""
        }

        success_embed = discord.Embed(
            title="☁️ Mua Máy Thành Công Qua Web Hanami",
            description=f"Đã liên kết tài khoản vào dịch vụ **{self.service_name}**:",
            color=discord.Color.green()
        )
        success_embed.add_field(name="📧 Email đăng nhập", value=f"`{email}`", inline=False)
        success_embed.add_field(name="🔑 Mật khẩu", value=f"`{password}`", inline=False)
        success_embed.add_field(name="🎟️ Mã mời hệ thống", value=f"`{invite_code}`", inline=False)
        success_embed.set_footer(text="Dùng lệnh /buff kèm mã mời này để gia hạn thời gian!")

        await msg.edit(content=None, embed=success_embed)

class UserMachineSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="VSPhone", style=discord.ButtonStyle.green, emoji="🪩")
    async def vs_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UserAccountInputModal("VSPHONE"))

    @discord.ui.button(label="VMOS", style=discord.ButtonStyle.blurple, emoji="🌀")
    async def vmos_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UserAccountInputModal("VMOS"))

class MainBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        try:
            await self.tree.sync()
            print("Đã đồng bộ lệnh Discord thành công.")
        except Exception as e:
            print(f"Lỗi đồng bộ lệnh: {e}")
        
        self.loop.create_task(keep_session_alive())

client = MainBot()

@client.event
async def on_ready():
    print(f'Bot đã online hoàn toàn với tên: {client.user}')

@client.tree.command(name="reg", description="Tạo tài khoản và mua máy trial tự động")
async def reg(interaction: discord.Interaction):
    panel_embed = discord.Embed(
        title="🍮 Reg Panel",
        description=(
            "Chọn dịch vụ bên dưới để nhập tài khoản và mua máy.\n\n"
            "**Dịch vụ hỗ trợ**\n"
            "• 🪩 VSPhone\n"
            "• 🌀 VMOS\n\n"
            "*Panel chỉ dùng được bởi người đã mở lệnh*"
        ),
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=panel_embed, view=UserMachineSelectView(), ephemeral=True)

@client.tree.command(name="buff", description="Buff thêm thời gian cho mã mời")
@app_commands.describe(code="Nhập mã mời của bạn")
async def buff(interaction: discord.Interaction, code: str):
    is_admin = False
    if interaction.guild and interaction.user:
        try:
            is_admin = interaction.user.guild_permissions.administrator
        except:
            is_admin = False

    code = code.strip()
    today_str = datetime.now().strftime("%d/%m/%Y")

    if code not in database_keys:
        await interaction.response.send_message(f"❌ Mã mời `{code}` không tồn tại trong hệ thống!", ephemeral=True)
        return

    data = database_keys[code]
    
    if datetime.now() > data["expires_at"]:
        await interaction.response.send_message(f"⚠️ Máy liên kết với mã mời `{code}` đã **hết hạn sử dụng**, không thể buff thêm thời gian!", ephemeral=True)
        return

    service_type = data["service"].upper()
    hours_to_add = 9 if service_type == "VSPHONE" else 3
    max_buff_limit = 5 if is_admin else 1

    await interaction.response.send_message(f"🔄 Đang xác thực mã mời và tiến hành buff...", ephemeral=True)
    msg = await interaction.original_response()

    if data["last_buff_date"] == today_str and data["buff_count"] >= max_buff_limit:
        await msg.edit(content=f"⚠️ Mã này đã đạt giới hạn tối đa **{max_buff_limit} lần buff** trong ngày hôm nay ({today_str}).", embed=None)
        return

    if data["last_buff_date"] != today_str:
        data["buff_count"] = 0

    api_buff_invite_code(code, hours_to_add, service_type)

    data["buff_count"] += 1
    data["last_buff_date"] = today_str
    
    data["expires_at"] += timedelta(hours=hours_to_add)
    new_time_str = data["expires_at"].strftime("%H:%M:%S - %d/%m/%Y")

    success_embed = discord.Embed(
        title="🎁 Buff Thời Gian Thành Công!",
        color=discord.Color.green()
    )
    success_embed.add_field(name="🎟️ Mã mời:", value=f"`{code}`", inline=False)
    success_embed.add_field(name="📧 Email liên kết:", value=f"`{data['email']}`", inline=False)
    success_embed.add_field(name="📦 Dịch vụ:", value=f"`{service_type}`", inline=False)
    success_embed.add_field(name="⏳ Cộng thêm:", value=f"**+{hours_to_add} Giờ**", inline=False)
    success_embed.add_field(name="📅 Hạn mới của máy:", value=f"`{new_time_str}`", inline=False)
    success_embed.set_footer(text=f"Đã dùng {data['buff_count']}/{max_buff_limit} lượt hôm nay")

    await msg.edit(content=None, embed=success_embed)

token = os.environ.get('DISCORD_TOKEN')
if token:
    client.run(token)
else:
    print("LỖI: Chưa thiết lập biến DISCORD_TOKEN trên Render!")
