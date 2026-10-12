import discord
from discord import app_commands
import asyncio
import random
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

database_keys = {}

stock_status = {
    "VSPHONE": True,
    "VMOS": True
}

# Modal để Admin nhập tên/ID thành viên trong server khi cấp máy
class GrantMachineModal(discord.ui.Modal, title="👑 Cấp Máy Cho Thành Viên"):
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
        target_name = self.member_name.value.strip().lower()
        
        # Tìm kiếm thành viên trong server (guild)
        matched_member = None
        for member in interaction.guild.members:
            if target_name in member.name.lower() or target_name in member.display_name.lower() or target_name == str(member.id):
                matched_member = member
                break

        if not matched_member:
            await interaction.response.send_message(f"❌ Không tìm thấy thành viên **'{self.member_name.value}'** trong server này. Vui lòng kiểm tra lại tên!", ephemeral=True)
            return

        await interaction.response.send_message(f"🔍 Đang tìm người chơi **{matched_member.display_name}** trong server để cấp máy **{self.service_name}** ({self.hours}h)...")
        msg = await interaction.original_response()

        for percent in range(30, 101, 35):
            embed = discord.Embed(
                title="⏳ Đang khởi tạo máy cho thành viên...",
                description=f"Đang thiết lập hệ thống cho `{matched_member.display_name}`...\n`[ {'█' * (percent // 10)}{'░' * (10 - percent // 10)} ] {percent}%`",
                color=discord.Color.yellow()
            )
            await msg.edit(embed=embed)
            await asyncio.sleep(0.4)

        email = f"thl_admin_{random.randint(10000, 99999)}@gmail.com"
        password = "Admin@" + str(random.randint(1000, 9999))
        invite_code = f"{self.service_name.lower()}ad_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=5))
        expiry_time = datetime.now() + timedelta(hours=self.hours)

        database_keys[invite_code] = {
            "service": self.service_name,
            "expires_at": expiry_time,
            "buff_count": 0,
            "last_buff_date": ""
        }

        success_embed = discord.Embed(
            title=f"✅ Cấp Máy {self.hours}h Thành Công!",
            description=f"Đã cấp thành công máy ảo cho {matched_member.mention}:",
            color=discord.Color.green()
        )
        success_embed.add_field(name="📦 Loại máy:", value=f"`{self.service_name}`", inline=False)
        success_embed.add_field(name="📧 Tài khoản (Email):", value=f"`{email}`", inline=False)
        success_embed.add_field(name="🔑 Mật khẩu:", value=f"`{password}`", inline=False)
        success_embed.add_field(name="🎟️ Mã mời hệ thống:", value=f"`{invite_code}`", inline=False)
        success_embed.add_field(name="⏳ Hạn sử dụng:", value=f"Đến **{expiry_time.strftime('%H:%M - %d/%m/%Y')} ({self.hours}h)**", inline=False)
        success_embed.set_footer(text="THL CLOUD • Cấp phát máy quản trị thành công")

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
                await interaction.response.edit_message(content="⚙️ Bạn đã chọn **VSPHONE**. Chọn mức thời gian để cấp cho thành viên:", view=view)
            vs_btn.callback = vs_callback
            self.add_item(vs_btn)

        if stock_status["VMOS"]:
            vmos_btn = discord.ui.Button(label="VMOS", style=discord.ButtonStyle.blurple, emoji="🔵")
            async def vmos_callback(interaction: discord.Interaction):
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Bạn không có quyền Quản trị viên!", ephemeral=True)
                    return
                view = AdminTimeSelectView("VMOS")
                await interaction.response.edit_message(content="⚙️ Bạn đã chọn **VMOS**. Chọn mức thời gian để cấp cho thành viên:", view=view)
            vmos_btn.callback = vmos_callback
            self.add_item(vmos_btn)

class MainBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("THL CLOUD đã đồng bộ lệnh và sẵn sàng.")

client = MainBot()

@client.event
async def on_ready():
    print(f'Bot THL CLOUD đã online: {client.user}')

@client.tree.command(name="reg", description="Hệ thống quản lý và cấp phát máy trial của THL CLOUD")
async def reg(interaction: discord.Interaction):
    is_admin = interaction.user.guild_permissions.administrator

    if is_admin:
        view = AdminMachineView()
        if len(view.children) == 0:
            await interaction.response.send_message("⚠️ Hiện tại tất cả các loại máy ảo đều đang **hết hàng**.", ephemeral=True)
            return

        embed = discord.Embed(
            title="👑 THL CLOUD — Quản Trị Cấp Máy",
            description=f"🌸 Chào Admin {interaction.user.mention}, hãy chọn loại máy ảo cần cấp:",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        # Người dùng thường khi tạo sẽ nhận sẵn máy 4h
        await interaction.response.send_message(f"⏳ Hệ thống đang tự động khởi tạo máy trial **4 Giờ** cho bạn...", ephemeral=True)
        msg = await interaction.original_response()

        for percent in range(50, 101, 50):
            embed = discord.Embed(
                title="⏳ Đang khởi tạo...",
                description=f"Đang chuẩn bị máy trial 4h...\n`[ {'█' * (percent // 10)}{'░' * (10 - percent // 10)} ] {percent}%`",
                color=discord.Color.yellow()
            )
            await msg.edit(embed=embed)
            await asyncio.sleep(0.4)

        email = f"thl_user_{random.randint(10000, 99999)}@gmail.com"
        password = "User@" + str(random.randint(1000, 9999))
        invite_code = f"user_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=5))
        expiry_time = datetime.now() + timedelta(hours=4)

        database_keys[invite_code] = {
            "service": "VSPHONE",
            "expires_at": expiry_time,
            "buff_count": 0,
            "last_buff_date": ""
        }

        success_embed = discord.Embed(
            title="☁️ Khởi Tạo Máy 4h Thành Công",
            description="Thông tin tài khoản máy ảo trial sẵn có của bạn:",
            color=discord.Color.green()
        )
        success_embed.add_field(name="📧 Tài khoản (Email):", value=f"`{email}`", inline=False)
        success_embed.add_field(name="🔑 Mật khẩu:", value=f"`{password}`", inline=False)
        success_embed.add_field(name="🎟️ Mã mời hệ thống:", value=f"`{invite_code}`", inline=False)
        success_embed.add_field(name="⏳ Hạn sử dụng:", value=f"Đến **{expiry_time.strftime('%H:%M - %d/%m/%Y')} (4h)**", inline=False)
        success_embed.set_footer(text="Dùng lệnh /buff kèm mã mời để gia hạn thêm thời gian!")

        await msg.edit(content=None, embed=success_embed)

@client.tree.command(name="buff", description="Buff thêm thời gian sử dụng cho mã mời")
@app_commands.describe(code="Nhập mã mời của bạn vào đây")
async def buff(interaction: discord.Interaction, code: str):
    is_admin = interaction.user.guild_permissions.administrator
    code = code.strip()
    today_str = datetime.now().strftime("%d/%m/%Y")

    hours_to_add = 9 if is_admin else 4
    max_buff_limit = 5 if is_admin else 1

    await interaction.response.send_message(f"🔄 Đang xác nhận mã mời và thực hiện buff (+{hours_to_add}h)...", ephemeral=True)
    msg = await interaction.original_response()

    for percent in range(50, 101, 50):
        embed = discord.Embed(
            title="⏳ Đang xử lý...",
            description=f"Đang kiểm tra mã `{code}` để cộng +{hours_to_add}h...\n`[ {'█' * (percent // 10)}{'░' * (10 - percent // 10)} ] {percent}%`",
            color=discord.Color.yellow()
        )
        await msg.edit(embed=embed)
        await asyncio.sleep(0.4)

    if code not in database_keys:
        database_keys[code] = {
            "service": "VSPHONE",
            "expires_at": datetime.now() + timedelta(hours=4),
            "buff_count": 0,
            "last_buff_date": ""
        }

    data = database_keys[code]

    if data["last_buff_date"] == today_str and data["buff_count"] >= max_buff_limit:
        role_name = "Quản trị viên" if is_admin else "Thành viên thường"
        await msg.edit(content=f"⚠️ Mã mời này đã đạt giới hạn tối đa **{max_buff_limit} lần buff** trong ngày cho {role_name} ({today_str}).", embed=None)
        return

    if data["last_buff_date"] != today_str:
        data["buff_count"] = 0

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
    success_embed.add_field(name="⏳ Thời gian cộng thêm:", value=f"**+{hours_to_add} Giờ**", inline=False)
    success_embed.add_field(name="📅 Hạn mới của máy:", value=f"`{new_time_str}`", inline=False)
    success_embed.set_footer(text=f"THL CLOUD • Đã dùng {data['buff_count']}/{max_buff_limit} lượt hôm nay")

    await msg.edit(content=None, embed=success_embed)

client.run('MTU1OTE0NTk2MTM4Nzg1MTg1OA.GtmP7R.CMU7CD8GfaPzMKehl4MppCR_lbibMS-aDNXlVU')

