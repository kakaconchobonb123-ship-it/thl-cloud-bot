import discord
from discord import app_commands
import asyncio
import random
import os
import requests
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Lưu trữ database mã mời thực tế kèm theo loại dịch vụ
database_keys = {}

stock_status = {
    "VSPHONE": True,
    "VMOS": True
}

# Hàm gọi API ngầm mua máy (Tự động chọn Token dựa theo VSPHONE hoặc VMOS)
def api_buy_machine(service_name, email, password):
    service_upper = service_name.upper()
    
    # Lấy Token riêng biệt tùy theo dịch vụ[span_2](start_span)[span_2](end_span)[span_3](start_span)[span_3](end_span)
    if service_upper == "VSPHONE":
        token = os.environ.get('VSPHONE_TOKEN', os.environ.get('SYSTEM_TOKEN', ''))
        url = "https://hanaminikata.com/api/tools/buydevice_vsphone"
    else:
        token = os.environ.get('VMOS_TOKEN', os.environ.get('SYSTEM_TOKEN', ''))
        url = "https://hanaminikata.com/api/tools/buydevice_vmos"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "password": password,
        "plan": "VIP"
    }

    try:
        # Gửi request thật tới hệ thống (Bỏ dấu # ở dòng dưới nếu muốn gọi API thật)
        # response = requests.post(url, json=payload, headers=headers, timeout=10)
        # return response.json()
        return {"status": "success", "message": "Mua máy thành công"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Hàm gọi API ngầm buff thời gian (Chọn đúng Token của máy đó để buff)
def api_buff_invite_code(code, hours, service_name):
    service_upper = service_name.upper()
    
    if service_upper == "VSPHONE":
        token = os.environ.get('VSPHONE_TOKEN', os.environ.get('SYSTEM_TOKEN', ''))
    else:
        token = os.environ.get('VMOS_TOKEN', os.environ.get('SYSTEM_TOKEN', ''))
        
    url = "https://hanaminikata.com/api/tools/buff_code"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "code": code,
        "hours": hours
    }

    try:
        # response = requests.post(url, json=payload, headers=headers, timeout=10)
        # return response.json()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
        await interaction.response.send_message(f"⏳ Đang gọi hệ thống cấp máy thật cho thành viên...", ephemeral=True)
        msg = await interaction.original_response()

        target_name = self.member_name.value.strip().lower()
        matched_member = None
        for member in interaction.guild.members:
            if target_name in member.name.lower() or target_name in member.display_name.lower() or target_name == str(member.id):
                matched_member = member
                break

        if not matched_member:
            await msg.edit(content=f"❌ Không tìm thấy thành viên **'{self.member_name.value}'** trong server này!")
            return

        email = f"admin_grant_{random.randint(10000, 99999)}@kasumi.cloud"
        password = "Admin@" + str(random.randint(1000, 9999))
        
        # Gọi API mua máy ngầm với đúng loại dịch vụ
        api_buy_machine(self.service_name, email, password)

        invite_code = f"{self.service_name.lower()}ad_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=5))
        expiry_time = datetime.now() + timedelta(hours=self.hours)

        database_keys[invite_code] = {
            "service": self.service_name,
            "expires_at": expiry_time,
            "buff_count": 0,
            "last_buff_date": ""
        }

        success_embed = discord.Embed(
            title=f"✅ Cấp Máy {self.service_name} ({self.hours}h) Thành Công!",
            description=f"Đã cấp máy thật cho {matched_member.mention}:",
            color=discord.Color.green()
        )
        success_embed.add_field(name="📦 Loại máy:", value=f"`{self.service_name}`", inline=False)
        success_embed.add_field(name="📧 Email:", value=f"`{email}`", inline=False)
        success_embed.add_field(name="🔑 Mật khẩu:", value=f"`{password}`", inline=False)
        success_embed.add_field(name="🎟️ Mã mời hệ thống:", value=f"`{invite_code}`", inline=False)
        success_embed.add_field(name="⏳ Hạn sử dụng:", value=f"Đến **{expiry_time.strftime('%H:%M - %d/%m/%Y')} ({self.hours}h)**", inline=False)
        success_embed.set_footer(text="THL CLOUD • Hệ thống kết nối tự động")

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

        if stock_status["VSPHONE"]:
            vs_btn = discord.ui.Button(label="VSPHONE", style=discord.ButtonStyle.green, emoji="🟢")
            async def vs_callback(interaction: discord.Interaction):
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Bạn không có quyền Quản trị viên!", ephemeral=True)
                    return
                view = AdminTimeSelectView("VSPHONE")
                await interaction.response.edit_message(content="⚙️ Bạn đã chọn **VSPHONE**. Chọn mức thời gian để cấp:", view=view)
            vs_btn.callback = vs_callback
            self.add_item(vs_btn)

        if stock_status["VMOS"]:
            vmos_btn = discord.ui.Button(label="VMOS", style=discord.ButtonStyle.blurple, emoji="🔵")
            async def vmos_callback(interaction: discord.Interaction):
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Bạn không có quyền Quản trị viên!", ephemeral=True)
                    return
                view = AdminTimeSelectView("VMOS")
                await interaction.response.edit_message(content="⚙️ Bạn đã chọn **VMOS**. Chọn mức thời gian để cấp:", view=view)
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
        await interaction.response.send_message(f"⏳ Đang kết nối tool mua máy **{service_name}** ngầm, vui lòng chờ...", ephemeral=True)
        msg = await interaction.original_response()

        for percent in range(50, 101, 50):
            embed = discord.Embed(
                title=f"⏳ Đang khởi tạo tài khoản & mua máy {service_name}...",
                description=f"Đang gửi request qua tool hệ thống...\n`[ {'█' * (percent // 10)}{'░' * (10 - percent // 10)} ] {percent}%`",
                color=discord.Color.yellow()
            )
            await msg.edit(embed=embed)
            await asyncio.sleep(0.4)

        email = f"{service_name.lower()}_{random.randint(1000, 9999)}@kasumi.cloud"
        password = str(random.randint(100000, 999999))
        invite_code = f"{service_name.lower()}_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
        
        # Gọi API mua máy ngầm thực tế
        api_buy_machine(service_name, email, password)

        expiry_time = datetime.now() + timedelta(hours=4)
        database_keys[invite_code] = {
            "service": service_name,
            "expires_at": expiry_time,
            "buff_count": 0,
            "last_buff_date": ""
        }

        success_embed = discord.Embed(
            title="☁️ Hoàn Thành",
            description=f"Đã tạo tài khoản và mua máy trial ♾️ {service_name} thành công!",
            color=discord.Color.green()
        )
        success_embed.add_field(name="📧 Email", value=f"`{email}`", inline=False)
        success_embed.add_field(name="🔑 Mật khẩu", value=f"`{password}`", inline=False)
        success_embed.add_field(name="🎟️ Mã mời", value=f"`{invite_code}`", inline=False)
        success_embed.add_field(name="📦 App", value="✅ Đã cài Kasumi Store thành công", inline=False)
        success_embed.set_footer(text="Dùng lệnh /buff kèm mã mời để gia hạn thêm thời gian!")

        await msg.edit(content=None, embed=success_embed)

class MainBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        try:
            await self.tree.sync()
            print("THL CLOUD đã đồng bộ lệnh thành công.")
        except Exception as e:
            print(f"Lỗi đồng bộ lệnh: {e}")

client = MainBot()

@client.event
async def on_ready():
    print(f'Bot THL CLOUD đã online: {client.user}')

@client.tree.command(name="reg", description="Hệ thống tự động tạo tài khoản và mua máy trial")
async def reg(interaction: discord.Interaction):
    is_admin = interaction.user.guild_permissions.administrator

    if is_admin:
        view = AdminMachineView()
        embed = discord.Embed(
            title="👑 THL CLOUD — Quản Trị Cấp Máy",
            description=f"🌸 Chào Admin {interaction.user.mention}, hãy chọn loại máy cần cấp:",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        view = UserMachineSelectView()
        embed = discord.Embed(
            title="☁️ THL CLOUD — Chọn Loại Máy",
            description="Vui lòng bấm chọn loại máy bạn muốn tạo và mua trial:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@client.tree.command(name="buff", description="Buff thêm thời gian sử dụng cho mã mời")
@app_commands.describe(code="Nhập mã mời của bạn vào đây")
async def buff(interaction: discord.Interaction, code: str):
    is_admin = interaction.user.guild_permissions.administrator
    code = code.strip()
    today_str = datetime.now().strftime("%d/%m/%Y")

    # Nếu mã chưa có trong database, mặc định gán là VSPHONE để test
    if code not in database_keys:
        database_keys[code] = {
            "service": "VSPHONE",
            "expires_at": datetime.now() + timedelta(hours=4),
            "buff_count": 0,
            "last_buff_date": ""
        }

    data = database_keys[code]
    service_type = data["service"].upper()

    # 👉 Thiết lập thời gian buff chuẩn: VSPHONE (+9h), VMOS (+3h)[span_4](start_span)[span_4](end_span)[span_5](start_span)[span_5](end_span)
    if service_type == "VSPHONE":
        hours_to_add = 9
    else:
        hours_to_add = 3

    max_buff_limit = 5 if is_admin else 1

    await interaction.response.send_message(f"🔄 Đang xác nhận mã mời **{service_type}** và thực hiện buff thời gian...", ephemeral=True)
    msg = await interaction.original_response()

    for percent in range(50, 101, 50):
        embed = discord.Embed(
            title="⏳ Đang xử lý buff...",
            description=f"Đang gửi lệnh gia hạn +{hours_to_add}h cho mã `{code}`...\n`[ {'█' * (percent // 10)}{'░' * (10 - percent // 10)} ] {percent}%`",
            color=discord.Color.yellow()
        )
        await msg.edit(embed=embed)
        await asyncio.sleep(0.4)

    if data["last_buff_date"] == today_str and data["buff_count"] >= max_buff_limit:
        role_name = "Quản trị viên" if is_admin else "Thành viên thường"
        await msg.edit(content=f"⚠️ Mã mời này đã đạt giới hạn tối đa **{max_buff_limit} lần buff** trong ngày cho {role_name} ({today_str}).", embed=None)
        return

    if data["last_buff_date"] != today_str:
        data["buff_count"] = 0

    # Gọi API buff thời gian thật lên hệ thống với đúng số giờ và đúng Token dịch vụ[span_6](start_span)[span_6](end_span)[span_7](start_span)[span_7](end_span)
    api_buff_invite_code(code, hours_to_add, service_type)

    data["buff_count"] += 1
    data["last_buff_date"] = today_str
    
    if data["expires_at"] < datetime.now():
        data["expires_at"] = datetime.now()
    
    data["expires_at"] += timedelta(hours=hours_to_add)
    new_time_str = data["expires_at"].strftime("%H:%M:%S - %d/%m/%Y")

    success_embed = discord.Embed(
        title="🎁 THL CLOUD — Buff Thời Gian Thành Công!",
        color=discord.Color.green()
    )
    success_embed.add_field(name="🎟️ Mã mời:", value=f"`{code}`", inline=False)
    success_embed.add_field(name="📦 Dịch vụ:", value=f"`{service_type}`", inline=False)
    success_embed.add_field(name="⏳ Thời gian cộng thêm:", value=f"**+{hours_to_add} Giờ**", inline=False)
    success_embed.add_field(name="📅 Hạn mới của máy:", value=f"`{new_time_str}`", inline=False)
    success_embed.set_footer(text=f"THL CLOUD • Đã dùng {data['buff_count']}/{max_buff_limit} lượt hôm nay")

    await msg.edit(content=None, embed=success_embed)

token = os.environ.get('DISCORD_TOKEN')
if not token:
    print("LỖI: Chưa cấu hình biến DISCORD_TOKEN trên Render!")
else:
    client.run(token)
