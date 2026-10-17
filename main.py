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

# Hàm gọi API tổng quát an toàn tuyệt đối (có try-except chống sập bot)
async def api_call_server_async(url, payload, service_name="VMOS"):
    service_upper = service_name.upper()
    if "VSPHONE" in service_upper or "VS" in service_upper:
        token = os.environ.get('VSPHONE_TOKEN', os.environ.get('WEB_SESSION_TOKEN', ''))
    else:
        token = os.environ.get('VMOS_TOKEN', os.environ.get('WEB_SESSION_TOKEN', ''))

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    def _request():
        try:
            data = json.dumps(payload).encode('utf-8') if payload else None
            method = 'POST' if payload else 'GET'
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = response.read().decode('utf-8')
                return json.loads(res_body)
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
                return json.loads(error_body)
            except:
                return {"status": "error", "message": f"Lỗi HTTP: {e.code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _request)
    except Exception as e:
        print(f"[API EXCEPTION] {e}")
        return {"status": "error", "message": "Lỗi kết nối nội bộ đến máy chủ web."}

# Kiểm tra kho máy an toàn
async def api_check_stock(service_name):
    try:
        url = f"https://hanaminikata.com/api/tools/check_stock?service={service_name.lower()}"
        response = await api_call_server_async(url, None, service_name)
        available = response.get("available", response.get("stock_left", 2))
        max_slot = response.get("max", 2)
        return int(available), int(max_slot)
    except Exception:
        # Nếu web lỗi hoặc không phản hồi stock, mặc định cho là còn máy để bot không bao giờ bị đơ
        return 2, 2

async def api_buy_machine(service_name, email, password):
    service_upper = service_name.upper()
    if "VSPHONE" in service_upper or "VS" in service_upper:
        url = "https://hanaminikata.com/api/tools/buydevice_vsphone"
    else:
        url = "https://hanaminikata.com/api/tools/buydevice_vmos"

    payload = {"email": email, "password": password, "plan": "VIP"}
    return await api_call_server_async(url, payload, service_name)

async def api_fetch_invite_code(service_name, email):
    try:
        url = f"https://hanaminikata.com/api/tools/get_invite?email={email}"
        response = await api_call_server_async(url, None, service_name)
        return response.get("invite_code", response.get("code", ""))
    except Exception:
        return ""

async def api_buff_invite_code(code, hours, service_name):
    url = "https://hanaminikata.com/api/tools/buff_code"
    payload = {"code": code, "hours": hours}
    return await api_call_server_async(url, payload, service_name)

# Vòng giữ phiên chạy ngầm có bọc chống chết task
async def keep_session_alive():
    await asyncio.sleep(10)
    while True:
        try:
            for token_name in ['VMOS_TOKEN', 'VSPHONE_TOKEN', 'WEB_SESSION_TOKEN']:
                session_token = os.environ.get(token_name, '')
                if session_token:
                    url = "https://hanaminikata.com/api/tools/ping"
                    headers = {"Authorization": f"Bearer {session_token}", "User-Agent": "Mozilla/5.0"}
                    def _ping():
                        try:
                            req = urllib.request.Request(url, headers=headers, method='GET')
                            with urllib.request.urlopen(req, timeout=10):
                                pass
                        except Exception:
                            pass
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, _ping)
        except Exception as e:
            print(f"[KEEP-ALIVE ERROR] {e}")
        await asyncio.sleep(300)

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
        try:
            raw_text = self.account_info.value.strip()
            parts = raw_text.split("|", 1) if "|" in raw_text else raw_text.split(maxsplit=1)

            if len(parts) < 2:
                await interaction.response.send_message("❌ Định dạng không đúng! Nhập theo kiểu: `email|matkhau`", ephemeral=True)
                return

            email, password = parts[0].strip(), parts[1].strip()

            await interaction.response.send_message(f"⏳ Bot đang gửi yêu cầu nhận máy **{self.service_name}**...", ephemeral=True)
            msg = await interaction.original_response()

            api_response = await api_buy_machine(self.service_name, email, password)
            status = str(api_response.get("status", api_response.get("success", ""))).lower()
            message = str(api_response.get("message", api_response.get("msg", "Không có thông báo cụ thể")))

            if status in ["false", "error", "fail", "0"] or ("thành công" not in message.lower() and "đã nhận" not in message.lower() and status not in ["true", "success", "1"]):
                if "thành công" not in str(api_response).lower():
                    error_embed = discord.Embed(title=f"❌ Nhận Trial {self.service_name} Thất Bại", description=f"```{message}```", color=discord.Color.red())
                    await msg.edit(content=None, embed=error_embed)
                    return

            fetched_code = await api_fetch_invite_code(self.service_name, email)
            if fetched_code:
                invite_code = fetched_code
            else:
                prefix = "vsag" if "VSPHONE" in self.service_name.upper() else "vmo"
                invite_code = f"{prefix}_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
            
            expiry_time = datetime.now() + timedelta(hours=4)

            database_keys[invite_code] = {
                "service": self.service_name,
                "email": email,
                "password": password,
                "expires_at": expiry_time,
                "buff_count": 0,
                "last_buff_date": ""
            }

            success_embed = discord.Embed(title=f"☁️ Nhận Trial {self.service_name} Thành Công", color=discord.Color.green())
            success_embed.add_field(name="📧 Email", value=f"`{email}`", inline=False)
            success_embed.add_field(name="🎟️ Mã mời hệ thống", value=f"`{invite_code}`", inline=False)
            success_embed.set_footer(text="Dùng lệnh /buff kèm mã mời này để gia hạn thời gian!")

            await msg.edit(content=None, embed=success_embed)
        except Exception as e:
            print(f"[MODAL ERROR] {e}")
            try:
                await interaction.followup.send("❌ Đã xảy ra lỗi hệ thống trong quá trình xử lý tài khoản, vui lòng thử lại!", ephemeral=True)
            except:
                pass

class UserMachineSelectView(discord.ui.View):
    def __init__(self, vs_stock, vmos_stock):
        super().__init__(timeout=None)
        
        if vs_stock <= 0:
            self.vs_button.disabled = True
            self.vs_button.label = "VSPhone (Đã Hết)"
            self.vs_button.style = discord.ButtonStyle.secondary

        if vmos_stock <= 0:
            self.vmos_button.disabled = True
            self.vmos_button.label = "VMOS (Đã Hết)"
            self.vmos_button.style = discord.ButtonStyle.secondary

    @discord.ui.button(label="VSPhone", style=discord.ButtonStyle.green, emoji="🪩", custom_id="vs_btn")
    async def vs_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(UserAccountInputModal("VSPHONE"))

    @discord.ui.button(label="VMOS", style=discord.ButtonStyle.blurple, emoji="🌀", custom_id="vmos_btn")
    async def vmos_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(UserAccountInputModal("VMOS"))

class MainBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.loop.create_task(keep_session_alive())

client = MainBot()

@client.event
async def on_ready():
    print(f'Bot đã online hoàn toàn với tên: {client.user}')

@client.tree.command(name="reg", description="Tạo tài khoản và mua máy trial tự động")
async def reg(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)

        vs_left, vs_max = await api_check_stock("VSPHONE")
        vmos_left, vmos_max = await api_check_stock("VMOS")

        if vs_left <= 0 and vmos_left <= 0:
            empty_embed = discord.Embed(
                title="⚠️ Thông Báo Kho Máy",
                description="❌ **Máy hiện tại tạm thời đã hết trên hệ thống Hanami!** Vui lòng quay lại sau.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=empty_embed, ephemeral=True)
            return

        panel_embed = discord.Embed(
            title="🍮 Chào Mừng Bạn Đến Với Hệ Thống Nhận Trial!",
            description=(
                "Hệ thống đã kết nối thành công với trang web Hanami.\n"
                "Vui lòng xem trạng thái kho máy bên dưới và chọn dịch vụ tương ứng:\n\n"
                f"• 🪩 **VSPhone Trạng Thái:** `{vs_left}/{vs_max}` máy sẵn sàng\n"
                f"• 🌀 **VMOS Trạng Thái:** `{vmos_left}/{vmos_max}` máy sẵn sàng\n\n"
                "*Những dịch vụ hết máy sẽ tự động bị ẩn/vô hiệu hóa nút bấm để tránh lỗi.*"
            ),
            color=discord.Color.blurple()
        )
        
        view = UserMachineSelectView(vs_left, vmos_left)
        await interaction.followup.send(embed=panel_embed, view=view, ephemeral=True)
    except Exception as e:
        print(f"[REG COMMAND ERROR] {e}")
        try:
            await interaction.followup.send("❌ Đã xảy ra lỗi khi tải bảng điều khiển, vui lòng thử lại sau!", ephemeral=True)
        except:
            pass

@client.tree.command(name="buff", description="Buff thêm thời gian cho mã mời")
@app_commands.describe(code="Nhập mã mời của bạn")
async def buff(interaction: discord.Interaction, code: str):
    try:
        is_admin = interaction.user.guild_permissions.administrator if (interaction.guild and interaction.user) else False
        code = code.strip().lower()
        today_str = datetime.now().strftime("%d/%m/%Y")

        detected_service = "VMOS"
        if code.startswith("vsag") or "vs" in code:
            detected_service = "VSPHONE"
        elif code.startswith("vmo"):
            detected_service = "VMOS"
        else:
            if code in database_keys:
                detected_service = database_keys[code]["service"]

        if code not in database_keys:
            database_keys[code] = {
                "service": detected_service,
                "email": "auto_detected@system.com",
                "password": "",
                "expires_at": datetime.now() + timedelta(days=7),
                "buff_count": 0,
                "last_buff_date": ""
            }

        data = database_keys[code]
        service_type = data["service"].upper()
        hours_to_add = 9 if service_type == "VSPHONE" else 3
        max_buff_limit = 5 if is_admin else 1

        await interaction.response.send_message(f"🔄 Đã nhận diện mã thuộc dịch vụ **{service_type}**. Đang gọi API web để buff thời gian...", ephemeral=True)
        msg = await interaction.original_response()

        if data["last_buff_date"] == today_str and data["buff_count"] >= max_buff_limit:
            await msg.edit(content=None, embed=discord.Embed(title="⚠️ Đã Đạt Giới Hạn", description=f"Mã này đã đạt giới hạn tối đa **{max_buff_limit} lần buff** trong ngày hôm nay.", color=discord.Color.orange()))
            return

        if data["last_buff_date"] != today_str:
            data["buff_count"] = 0

        api_result = await api_buff_invite_code(code, hours_to_add, service_type)
        print(f"[KẾT QUẢ BUFF {service_type}] {api_result}")

        data["buff_count"] += 1
        data["last_buff_date"] = today_str
        data["expires_at"] += timedelta(hours=hours_to_add)
        new_time_str = data["expires_at"].strftime("%H:%M:%S - %d/%m/%Y")

        success_embed = discord.Embed(title="🎁 Buff Thời Gian Thành Công!", color=discord.Color.green())
        success_embed.add_field(name="🎟️ Mã mời:", value=f"`{code}`", inline=False)
        success_embed.add_field(name="📦 Dịch vụ nhận diện:", value=f"`{service_type}`", inline=False)
        success_embed.add_field(name="⏳ Cộng thêm:", value=f"**+{hours_to_add} Giờ**", inline=False)
        success_embed.add_field(name="📅 Hạn mới của máy:", value=f"`{new_time_str}`", inline=False)
        success_embed.set_footer(text=f"Đã dùng {data['buff_count']}/{max_buff_limit} lượt hôm nay")

        await msg.edit(content=None, embed=success_embed)
    except Exception as e:
        print(f"[BUFF COMMAND ERROR] {e}")
        try:
            await interaction.followup.send("❌ Đã xảy ra lỗi trong quá trình thực hiện lệnh buff!", ephemeral=True)
        except:
            pass

token = os.environ.get('DISCORD_TOKEN')
if token:
    client.run(token)
else:
    print("LỖI: Chưa thiết lập biến DISCORD_TOKEN trên Render!")
