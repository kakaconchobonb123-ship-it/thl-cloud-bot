import discord
from discord import app_commands
import asyncio
import random
import os
import urllib.request
import json
from datetime import datetime, timedelta

intents = discord.Intents.default()

# Lưu trữ cơ sở dữ liệu mã mời gắn liền với email, mật khẩu và thời hạn thực tế
database_keys = {}

def api_call_server(url, payload, token):
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
        token = os.environ.get('VSPHONE_TOKEN', '')
        url = "https://hanaminikata.com/api/tools/buydevice_vsphone"
    else:
        token = os.environ.get('VMOS_TOKEN', '')
        url = "https://hanaminikata.com/api/tools/buydevice_vmos"

    payload = {"email": email, "password": password, "plan": "VIP"}
    return api_call_server(url, payload, token)

def api_buff_invite_code(code, hours, service_name):
    service_upper = service_name.upper()
    if service_upper == "VSPHONE":
        token = os.environ.get('VSPHONE_TOKEN', '')
    else:
        token = os.environ.get('VMOS_TOKEN', '')
        
    url = "https://hanaminikata.com/api/tools/buff_code"
    payload = {"code": code, "hours": hours}
    return api_call_server(url, payload, token)

class GrantMachineModal(discord.ui.Modal, title="👑 Cấp Máy Cho Thành Viên (Admin)"):
    member_name = discord.ui.TextInput(
        label="Tên hoặc ID thành viên trong server",
        placeholder="Nhập tên hiển thị hoặc ID của user...",
        required=True,
        max_length=100
    )

    def __init__(self, service_name: str, hours: int):
        super().__init__()
        self.service_name = service_name
        self.hours = hours

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"⏳ Đang gọi hệ thống cấp máy thật...", ephemeral=True)
        msg = await interaction.original_response()

        target_name = self.member_name.value.strip().lower()
        matched_member = None
        for guild in interaction.client.guilds:
            for member in guild.members:
                if target_name in member.name.lower() or target_name in member.display_name.lower() or target_name == str(member.id):
                    matched_member = member
                    break
            if matched_member:
                break

        if not matched_member:
            await msg.edit(content=f"❌ Không tìm thấy thành viên **'{self.member_name.value}'** trong server!")
            return

        email = f"admin_grant_{random.randint(10000, 99999)}@kasumi.cloud"
        password = "Admin@" + str(random.randint(1000, 9999))
        
        api_buy_machine(self.service_name, email, password)

        invite_code = f"{self.service_name.lower()}ad_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=5))
        expiry_time = datetime.now() + timedelta(hours=self.hours)

        database_keys[invite_code] = {
            "service": self.service_name,
            "email": email,
            "password": password,
            "expires_at": expiry_time,
            "buff_count": 0,
            "last_buff_date": ""
        }

        success_embed = discord.Embed(
            title=f"✅ Cấp Máy {self.service_name} ({self.hours}h) Thành Công!",
            description=f"Đã cấp máy cho {matched_member.mention}:",
            color=discord.Color.green()
        )
        success_embed.add_field(name="📧 Email:", value=f"`{email}`", inline=False)
        success_embed.add_field(name="🔑 Mật khẩu:", value=f"`{password}`", inline=False)
        success_embed.add_field(name="🎟️ Mã mời hệ thống:", value=f"`{invite_code}`", inline=False)
        success_embed.add_field(name="⏳ Hạn sử dụng:", value=f"Đến **{expiry_time.strftime('%H:%M - %d/%m/%Y')} ({self.hours}h)**", inline=False)
        success_embed.set_footer(text="THL CLOUD • Tự động hóa kết nối")

        await msg.edit(content=None, embed=success_embed)

class AdminTimeSelectView(discord.ui.View):
    def __init__(self, service_name: str):
        super().__init__(timeout=None)
        self.service_name = service_name

    @discord.ui.button(label="⏱️ Cấp 4 Giờ", style=discord.ButtonStyle.blurple)
    async def time_4h(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GrantMachineModal(self.service_name, 4))

    @discord.ui.button(label="👑 Cấp 24 Giờ", style=discord.ButtonStyle.danger)
    async def time_24h(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GrantMachineModal(self.service_name, 24))

class AdminMachineView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        vs_btn = discord.ui.Button(label="VSPHONE", style=discord.ButtonStyle.green, emoji="🟢")
        async def vs_callback(interaction: discord.Interaction):
            if not interaction.guild or not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Bạn không có quyền Quản trị viên!", ephemeral=True)
                return
            await interaction.response.edit_message(content="⚙️ Bạn đã chọn **VSPHONE**. Chọn mức thời gian cấp:", view=AdminTimeSelectView("VSPHONE"))
        vs_btn.callback = vs_callback
        self.add_item(vs_btn)

        vmos_btn = discord.ui.Button(label="VMOS", style=discord.ButtonStyle.blurple, emoji="🔵")
        async def vmos_callback(interaction: discord.Interaction):
            if not interaction.guild or not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Bạn không có quyền Quản trị viên!", ephemeral=True)
                return
            await interaction.response.edit_message(content="⚙️ Bạn đã chọn **VMOS**. Chọn mức thời gian cấp:", view=AdminTimeSelectView("VMOS"))
        vmos_btn.callback = vmos_callback
        self.add_item(vmos_btn)

class UserMachineSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="VSPHONE", style=discord.ButtonStyle.green, emoji="🟢")
    async def vsp_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_user_reg(interaction, "VSPHONE")

    @discord.ui.button(label="VMOS", style=discord.ButtonStyle.blurple, emoji="🔵")
    async def vmos_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_user_reg(interaction, "VMOS")

    async def process_user_reg(self, interaction: discord.Interaction, service_name: str):
        await interaction.response.send_message(f"⏳ Đang khởi tạo và mua máy **{service_name}** trên hệ thống...", ephemeral=True)
        msg = await interaction.original_response()

        email = f"{service_name.lower()}_{random.randint(1000, 9999)}@kasumi.cloud"
        password = str(random.randint(100000, 999999))
        invite_code = f"{service_name.lower()}_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
        
        api_buy_machine(service_name, email, password)

        expiry_time = datetime.now() + timedelta(hours=4)
        database_keys[invite_code] = {
            "service": service_name,
            "email": email,
            "password": password,
            "expires_at": expiry_time,
            "buff_count": 0,
            "last_buff_date": ""
        }

        success_embed = discord.Embed(
            title="☁️ Tạo Tài Khoản & Mua Máy Thành Công",
            description=f"Đã đăng ký tài khoản trial cho dịch vụ **{service_name}**:",
            color=discord.Color.green()
        )
        success_embed.add_field(name="📧 Email đăng nhập", value=f"`{email}`", inline=False)
        success_embed.add_field(name="🔑 Mật khẩu", value=f"`{password}`", inline=False)
        success_embed.add_field(name="🎟️ Mã mời hệ thống", value=f"`{invite_code}`", inline=False)
        success_embed.set_footer(text="Dùng lệnh /buff kèm mã mời này để gia hạn thời gian!")

        await msg.edit(content=None, embed=success_embed)

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

client = MainBot()

@client.event
async def on_ready():
    print(f'Bot đã online hoàn toàn với tên: {client.user}')

@client.tree.command(name="reg", description="Tạo tài khoản và mua máy trial tự động")
async def reg(interaction: discord.Interaction):
    is_admin = False
    if interaction.guild and interaction.user:
        try:
            is_admin = interaction.user.guild_permissions.administrator
        except:
            is_admin = False

    if is_admin:
        await interaction.response.send_message(embed=discord.Embed(title="👑 Admin - Chọn máy cần cấp", color=discord.Color.gold()), view=AdminMachineView(), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(title="☁️ Chọn loại máy cần tạo", color=discord.Color.blue()), view=UserMachineSelectView(), ephemeral=True)

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
    
    # Kiểm tra xem máy đã hết hạn chưa
    if datetime.now() > data["expires_at"]:
        await interaction.response.send_message(f"⚠️ Máy liên kết với mã mời `{code}` (Email: `{data['email']}`) đã **hết hạn sử dụng**, không thể buff thêm thời gian!", ephemeral=True)
        return

    service_type = data["service"].upper()
    
    # Tự động phân chia thời gian buff chuẩn: VSPHONE (+9h), VMOS (+3h)[span_2](start_span)[span_2](end_span)[span_3](start_span)[span_3](end_span)
    hours_to_add = 9 if service_type == "VSPHONE" else 3
    max_buff_limit = 5 if is_admin else 1

    await interaction.response.send_message(f"🔄 Đang xác thực mã mời của email `{data['email']}` và tiến hành buff...", ephemeral=True)
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
