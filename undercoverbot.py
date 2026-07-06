import discord
from discord import app_commands
import os
import json
import random
import math
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

try:
    ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
except (TypeError, ValueError):
    ADMIN_USER_ID = None

class Client(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'logged on as {self.user} !')

        try:
            guild = discord.Object(id=GUILD_ID)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} command to guild {guild.id}')

        except Exception as e:
            print(f'error: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.guild is None and ADMIN_USER_ID is not None:
            if message.author.id == ADMIN_USER_ID:
                if message.content.strip().lower() == "restart":
                    await message.channel.send("收到，正在重啟...")
                    sys.exit(0)

guild = discord.Object(id=GUILD_ID)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = Client(intents=intents)

undercover_player_dict = {}
undercover_order_dict = {}
undercover_spy_dict = {}
undercover_whiteboard_dict = {}
undercover_word_dict = {}
vote_active_dict = {}

def create_pages(page_num, interaction_guild_id):
    with open('verbdata/default.json', 'r', encoding='utf-8') as j:
        data = json.load(j)
        verb = data.copy()
    
    verb_list = list(verb.items())
    max_pages = math.ceil(len(verb_list)/20)
    start = (page_num - 1) * 20 
    end = page_num * 20
    current_page = verb_list[start: end]

    verb_str = '\n'.join(f'{verb_id}. {verb_name[0]}⇄{verb_name[1]}' for verb_id, verb_name in enumerate(current_page, start=start+1))
    verb_embed = discord.Embed(title='詞彙列表')
    verb_embed.add_field(name='', value=verb_str)
    return verb_embed, max_pages

def custom_pages(page_num, interaction_guild_id):
    guild_file_path = f"verbdata/{interaction_guild_id}.json"
    
    if os.path.exists(guild_file_path):
        with open(f'verbdata/{interaction_guild_id}.json', 'r', encoding='utf-8') as i:
            guild_data = json.load(i)
            custom_verb = guild_data.copy()
        
        if not custom_verb:
            verb_embed = discord.Embed(title='自訂詞彙列表', description='目前沒有自訂詞彙')
            return verb_embed, 1

    else:
        verb_embed = discord.Embed(title='自訂詞彙列表', description='目前沒有自訂詞彙')
        return verb_embed, 1
    
    verb_list = list(custom_verb.items())

    max_pages = math.ceil(len(verb_list)/20)
    start = (page_num - 1) * 20 
    end = page_num * 20
    current_page = verb_list[start: end]

    verb_str = '\n'.join(f'{verb_id}. {verb_name[0]}⇄{verb_name[1]}' for verb_id, verb_name in enumerate(current_page, start=start+1))
    verb_embed = discord.Embed(title='自訂詞彙列表')
    verb_embed.add_field(name='', value=verb_str)
    return verb_embed, max_pages

async def dm_player(member, word, spy):
    dm_embed = discord.Embed(title='你的詞彙', description=word)

    if spy:
        dm_embed.add_field(name='你的身分', value='臥底')

    else:
        dm_embed.add_field(name='你的身分', value='平民')

    await member.send(embed=dm_embed)

async def whiteboard_dm(member, word):
    dm_embed = discord.Embed(title='你的詞彙', description=word)
    await member.send(embed=dm_embed)

def player_embed(playerlist):
    pl_embed = discord.Embed(title='遊戲開始')
    player_str = '\n'.join(f'<@{pid}>' for pid in playerlist)
    pl_embed.add_field(name='請按以下順序發言', value=player_str)
    return pl_embed

def spy_victory(spy_name, spy_word, civilian_word):
    end = discord.Embed(title='遊戲結束')
    end.add_field(name='臥底獲勝', value=f'臥底{spy_name}沒有被淘汰。')
    end.add_field(name=f'平民詞彙是：{civilian_word}', value='', inline=False)
    end.add_field(name=f'臥底詞彙是：{spy_word}', value='', inline=False)
    return end

def civilian_victory(spy_name, spy_word, civilian_word):
    end = discord.Embed(title='遊戲結束')
    end.add_field(name='平民獲勝', value=f'臥底{spy_name}已被淘汰。')
    end.add_field(name=f'平民詞彙是：{civilian_word}', value='', inline=False)
    end.add_field(name=f'臥底詞彙是：{spy_word}', value='', inline=False)
    return end

class start_button(discord.ui.View):
    def __init__(self, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.children[5].disabled = True
    
    @discord.ui.button(label='加入', style=discord.ButtonStyle.blurple)
    async def join_button(self, interaction, button):
        if interaction.user.id not in undercover_player_dict[interaction.guild.id]:
            undercover_player_dict[interaction.guild.id].append(interaction.user.id)
            new_embed = interaction.message.embeds[0].copy()
            new_str = '\n'.join(f'<@{pid}>' for pid in undercover_player_dict[interaction.guild.id])
            new_embed.set_field_at(1, name='玩家', value=new_str, inline=False)
            await interaction.response.edit_message(embed=new_embed)
        else:
            await interaction.response.send_message('你已經加入遊戲了！', ephemeral=True)
    
    @discord.ui.button(label='離開', style=discord.ButtonStyle.red)
    async def leave_button(self, interaction, button):
        if interaction.user.id in undercover_player_dict[interaction.guild.id]:
            holder = undercover_player_dict[interaction.guild.id][0]
            undercover_player_dict[interaction.guild.id].remove(interaction.user.id)

            if not undercover_player_dict[interaction.guild.id]:
                del undercover_player_dict[interaction.guild.id]
                new_embed = discord.Embed(title='遊戲已結束')
                await interaction.response.edit_message(embed=new_embed, view=None)

            elif interaction.user.id == holder:
                new_embed = discord.Embed(title='遊戲已結束')
                await interaction.response.edit_message(embed=new_embed, view=None)
                await interaction.followup.send(f'因房主<@{holder}>離開遊戲，遊戲結束。', allowed_mentions=discord.AllowedMentions.none())
                del undercover_player_dict[interaction.guild.id]

            else:
                new_embed = interaction.message.embeds[0].copy()
                new_str = '\n'.join(f'<@{pid}>' for pid in undercover_player_dict[interaction.guild.id])
                new_embed.set_field_at(1, name='玩家', value=new_str)
                await interaction.response.edit_message(embed=new_embed)
        else:
            await interaction.response.send_message('你不在遊戲內！', ephemeral=True)

    @discord.ui.button(label='開始遊戲', style=discord.ButtonStyle.blurple)
    async def start_button(self, interaction, button):
        if interaction.user.id != undercover_player_dict[interaction.guild.id][0]:
            await interaction.response.send_message('你無法開始遊戲！', ephemeral=True)
        
        else:
            for child in self.children:
                child.disabled = True

            playerlist = undercover_player_dict[interaction.guild.id].copy()
            random.shuffle(playerlist)

            undercover_order_dict[interaction.guild.id] = playerlist
            vote_active_dict[interaction.guild.id] = 0
            
            playerembed = player_embed(undercover_order_dict[interaction.guild.id])
            await interaction.response.send_message(embed=playerembed)
            await interaction.message.edit(view=self)
            with open('verbdata/default.json', 'r', encoding='utf-8') as j:
                data = json.load(j)
                verb = data.copy() 

                guild_file_path = f"verbdata/{interaction.guild.id}.json"
                if os.path.exists(guild_file_path):
                    with open(guild_file_path, 'r', encoding='utf-8') as j:
                        data = json.load(j)
                        verb.update(data)

            word1, word2 = random.choice(list(verb.items()))

            if random.choice([True, False]):
                civilian = word1
                spy = word2

            else:
                civilian = word2
                spy = word1

            undercover_word_dict[interaction.guild.id] = {'spy': spy, 'civilian': civilian}

            spy_player = random.choice(undercover_player_dict[interaction.guild.id])
            undercover_spy_dict[interaction.guild.id] = spy_player

            for player_id in undercover_player_dict[interaction.guild.id]:
                member = await interaction.guild.fetch_member(player_id)

                if member is not None:
                    game_data = undercover_whiteboard_dict.get(interaction.guild.id)
                    if not game_data:
                        if player_id == spy_player:
                            await dm_player(member, spy, 1)

                        else:
                            await dm_player(member, civilian, 0)

                    else:
                        if player_id == spy_player:
                            await whiteboard_dm(member, spy)

                        else:
                            await whiteboard_dm(member, civilian)

                            
    
    @discord.ui.button(label='關閉遊戲', style=discord.ButtonStyle.grey)
    async def close_button(self, interaction, button):
        if interaction.user.id == undercover_player_dict[interaction.guild.id][0]:
            new_embed = discord.Embed(title='遊戲已結束')
            del undercover_player_dict[interaction.guild.id]
            await interaction.response.edit_message(embed=new_embed, view=None)
        
        else:
            await interaction.response.send_message('你無法關閉遊戲！', ephemeral=True)

    @discord.ui.button(label='白板模式', style=discord.ButtonStyle.grey)
    async def whiteboard(self, interaction, button):
        if interaction.user.id not in undercover_player_dict[interaction.guild.id]:
            await interaction.response.send_message('你無法更改模式！', ephemeral=True)

        else:
            undercover_whiteboard_dict[interaction.guild.id] = 1
            new_embed = interaction.message.embeds[0].copy()
            new_embed.set_footer(text='白板模式：開')
            button.disabled = True
            self.children[5].disabled = False
            await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label='一般模式', style=discord.ButtonStyle.grey)
    async def normal(self, interaction, button):
        if interaction.user.id not in undercover_player_dict[interaction.guild.id]:
            await interaction.response.send_message('你無法更改模式！', ephemeral=True)

        else:
            undercover_whiteboard_dict[interaction.guild.id] = 0
            new_embed = interaction.message.embeds[0].copy()
            new_embed.set_footer(text='白板模式：關')
            button.disabled = True
            self.children[4].disabled = False
            await interaction.response.edit_message(embed=new_embed, view=self)

class verblist_button(discord.ui.View):
    def __init__(self, max_pages, list_type, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.current_page = 1
        self.max_pages = max_pages
        self.children[0].disabled = True
        self.children[3].disabled = True
        self.list_type = list_type

    def check_button(self):
        if self.current_page == 1:
            self.children[0].disabled = True
        else:
            self.children[0].disabled = False

        if self.current_page == self.max_pages:
            self.children[1].disabled = True
        else:
            self.children[1].disabled = False

    def check_default(self):
        if self.list_type == 'default':
            self.children[2].disabled = False
            self.children[3].disabled = True
            
        else:
            self.children[2].disabled = True
            self.children[3].disabled = False

    @discord.ui.button(label='上一頁', style=discord.ButtonStyle.grey)
    async def lastpage(self, interaction, button):

        self.current_page -= 1
        self.check_button()
        if self.list_type == 'default':
            new_embed, _ = create_pages(self.current_page, interaction.guild.id)

        else:
            new_embed, _ = custom_pages(self.current_page, interaction.guild.id)

        await interaction.response.edit_message(embed=new_embed, view=self)


    @discord.ui.button(label='下一頁', style=discord.ButtonStyle.grey)
    async def nextpage(self, interaction, button):

        self.current_page += 1
        self.check_button()

        if self.list_type == 'default':
            new_embed, _ = create_pages(self.current_page, interaction.guild.id)

        else:
            new_embed, _ = custom_pages(self.current_page, interaction.guild.id)

        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label='查看自訂詞彙', style=discord.ButtonStyle.blurple)
    async def custom_verbs(self, interaction, button):
        self.list_type = 'custom'
        self.check_default()
        self.current_page = 1
        new_embed, self.max_pages = custom_pages(self.current_page, interaction.guild.id)
        self.check_button()

        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label='查看默認詞彙', style=discord.ButtonStyle.blurple)
    async def default_verbs(self, interaction, button):
        self.list_type = 'default'
        self.check_default()
        self.current_page = 1
        new_embed, self.max_pages = create_pages(self.current_page, interaction.guild.id)
        self.check_button()
        
        await interaction.response.edit_message(embed=new_embed, view=self)

class sample_button(discord.ui.Button):
    def __init__(self, pid: int, label_name: str, timeout=60):
        super().__init__(label=label_name, style=discord.ButtonStyle.grey)
        self.pid = pid

    async def callback(self, interaction: discord.Interaction):
        view: 'vote_button' = self.view
        voter_id = interaction.user.id

        if voter_id in view.voted_users:
            await interaction.response.send_message('你已經投過票了！', ephemeral=True)

        else:
            view.voted_users.add(voter_id)
            view.votes[self.pid] += 1
            await interaction.response.send_message(f'你投給了{self.label}。', ephemeral=True)
            if len(view.voted_users) == len(undercover_order_dict[view.guild.id]):
                await view.end_voting()

class vote_button(discord.ui.View):
    def __init__(self, order_list: list, guild: discord.Guild, channel: discord.TextChannel, *, timeout = 60):
        super().__init__(timeout=None)
        self.votes = {pid: 0 for pid in order_list}
        self.voted_users = set()
        self.guild = guild
        self.channel = channel
        self.message = None
        self.is_ended = False

        for pid in order_list:
            member = guild.get_member(pid)
            member_name = member.display_name
            self.add_item(sample_button(pid=pid, label_name=member_name))
    
    async def start_strict_timer(self, seconds: int):
        await asyncio.sleep(seconds)
        await self.end_voting()


    async def end_voting(self):
        if self.is_ended:
            return
        
        self.is_ended = True

        self.stop()
        highest_vote = max(self.votes.values())
        highest_voted_player = [pid for pid, v in self.votes.items() if v == highest_vote]

        vote_result_embed = discord.Embed(title='投票結果')
        result = '\n'.join(f'<@{pid}>: {v}票' for pid, v in self.votes.items())
        vote_result_embed.add_field(name='', value=result)
        
        if len(highest_voted_player) > 1:
            continue_embed = player_embed(undercover_order_dict[self.guild.id])
            await self.channel.send(embeds=[vote_result_embed, continue_embed])
            vote_active_dict[self.guild.id] = 0

        #game over
        elif highest_voted_player[0] == undercover_spy_dict[self.guild.id]:
            spy = await self.guild.fetch_member(undercover_spy_dict[self.guild.id])
            spy_name = spy.display_name
            game_word = undercover_word_dict[self.guild.id]
            spy_word = game_word['spy']
            civilian_word = game_word['civilian']
            end_embed = civilian_victory(spy_name=spy_name, spy_word=spy_word, civilian_word=civilian_word)
            del undercover_order_dict[self.guild.id]
            del undercover_player_dict[self.guild.id]
            del undercover_spy_dict[self.guild.id]
            del undercover_word_dict[self.guild.id]
            undercover_whiteboard_dict.pop(self.guild.id, None)
            await self.channel.send(embeds=[vote_result_embed, end_embed])
            vote_active_dict.pop(self.guild.id, None)

        #game over
        elif highest_voted_player[0] in undercover_order_dict[self.guild.id] and len(undercover_order_dict[self.guild.id]) == 3 or len(undercover_order_dict[self.guild.id]) == 2:
            undercover_order_dict[self.guild.id].remove(highest_voted_player[0])
            spy = await self.guild.fetch_member(undercover_spy_dict[self.guild.id])
            spy_name = spy.display_name
            game_word = undercover_word_dict[self.guild.id]
            spy_word = game_word['spy']
            civilian_word = game_word['civilian']
            end_embed = spy_victory(spy_name=spy_name, spy_word=spy_word, civilian_word=civilian_word)
            del undercover_order_dict[self.guild.id]
            del undercover_player_dict[self.guild.id]
            del undercover_spy_dict[self.guild.id]
            del undercover_word_dict[self.guild.id]
            undercover_whiteboard_dict.pop(self.guild.id, None)
            await self.channel.send(embeds=[vote_result_embed, end_embed])
            vote_active_dict[self.guild.id] = 0

        else:
            vote_result_embed = discord.Embed(title='投票結果')
            result = '\n'.join(f'<@{pid}>: {v}票' for pid, v in self.votes.items())
            vote_result_embed.add_field(name='', value=result, inline=False)
            vote_result_embed.add_field(name='', value=f'<@{highest_voted_player[0]}>被淘汰了！', inline=False)
            undercover_order_dict[self.guild.id].remove(highest_voted_player[0])
            continue_embed = player_embed(undercover_order_dict[self.guild.id])
            await self.channel.send(embeds=[vote_result_embed, continue_embed])
            vote_active_dict[self.guild.id] = 0

@client.tree.command(name='臥底', description='建立一個誰是臥底遊戲', guild=guild)
async def undercover(interaction: discord.Interaction):
    undercover_player_dict[interaction.guild.id] = [interaction.user.id]
    player_str = '\n'.join(f'<@{pid}>' for pid in undercover_player_dict[interaction.guild.id])
    undercover_embed = discord.Embed(title="誰是臥底？")
    undercover_embed.add_field(name='房主', value=interaction.user.name, inline=False)
    undercover_embed.add_field(name='玩家', value=player_str, inline=False)
    undercover_embed.set_footer(text='白板模式：關')
    await interaction.response.send_message(embed=undercover_embed, view=start_button())

@client.tree.command(name='臥底投票', description='選出你認為的臥底', guild=guild)
async def vote(interaction: discord.Interaction):
    if not vote_active_dict[interaction.guild.id]:
        vote_active_dict[interaction.guild.id] = 1
        vote_embed = discord.Embed(title='選出你認為的臥底')
        vote_str = '\n'.join(f'<@{pid}>' for pid in undercover_order_dict[interaction.guild.id])
        vote_view = vote_button(undercover_order_dict[interaction.guild.id], interaction.guild, interaction.channel)
        asyncio.create_task(vote_view.start_strict_timer(60))
        await interaction.response.send_message(embed=vote_embed, view=vote_view)

    else:
        await interaction.response.send_message('已經開始投票了！', ephemeral=True)

@client.tree.command(name='結束臥底遊戲', description='結束目前的臥底遊戲', guild=guild)
async def quit(interaction: discord.Interaction):
    if interaction.guild.id not in undercover_order_dict:
        await interaction.response.send_message('目前沒有臥底遊戲正在進行。', ephemeral=True)

    elif interaction.user.id not in undercover_order_dict[interaction.guild.id]:
        await interaction.response.send_message('你不在遊戲內！', ephemeral=True)

    else:
        del undercover_order_dict[interaction.guild.id]
        del undercover_player_dict[interaction.guild.id]
        del undercover_spy_dict[interaction.guild.id]
        del undercover_word_dict[interaction.guild.id]
        undercover_whiteboard_dict.pop(interaction.guild.id, None)
        await interaction.response.send_message('臥底遊戲已被強制結束。')
        
@client.tree.command(name='查看詞彙列表', description='查看誰是臥底的詞彙列表', guild=guild)
async def verblist(interaction: discord.Interaction):
    verb_embed, max_pages= create_pages(1, interaction.guild.id)
    myview = verblist_button(max_pages, 'default')
    await interaction.response.send_message(embed=verb_embed, view=myview)

@client.tree.command(name='新增自訂詞彙', description='新增自訂的誰是臥底詞彙', guild=guild)
async def new_custom_word(interaction: discord.Interaction, 詞彙1: str, 詞彙2: str):
    guild_file_path = f"verbdata/{interaction.guild.id}.json"

    if os.path.exists(guild_file_path):
        with open(guild_file_path, 'r', encoding='utf-8') as i:
            guild_data = json.load(i)
            custom_verb = guild_data.copy()

        if 詞彙1 in custom_verb:
            詞彙1, 詞彙2 = 詞彙2, 詞彙1

        if 詞彙1 in custom_verb:
            await interaction.response.send_message('這組詞彙已經存在！', ephemeral=True)
            return
        
        custom_verb[詞彙1] = 詞彙2

    else:
        custom_verb = {}
        custom_verb[詞彙1] = 詞彙2

    with open(guild_file_path, 'w', encoding='utf-8') as i:
        json.dump(custom_verb, i, ensure_ascii=False, indent=4)

    custom_verb_embed = discord.Embed(title='已新增自訂詞彙', description=f'{詞彙1} ⇄ {詞彙2}')
    await interaction.response.send_message(embed=custom_verb_embed)

@client.tree.command(name='刪除自訂詞彙', description='刪除自訂的誰是臥底詞彙', guild=guild)
async def del_custom_word(interaction: discord.Interaction, 詞彙1: str, 詞彙2: str):
    guild_file_path = f"verbdata/{interaction.guild.id}.json"
    word_exist = False

    if not os.path.exists(guild_file_path):
        await interaction.response.send_message('目前還沒有自訂詞彙！', ephemeral=True)
        return
    
    with open(guild_file_path, 'r', encoding='utf-8') as i:
        guild_data = json.load(i)
        custom_verb = guild_data.copy()

    if 詞彙1 in custom_verb and custom_verb[詞彙1] == 詞彙2:
        word_exist = True

    elif 詞彙1 in custom_verb.values() and custom_verb[詞彙2] == 詞彙1:
        word_exist = True
        詞彙1, 詞彙2 = 詞彙2, 詞彙1

    if word_exist:
        del custom_verb[詞彙1]
        with open(guild_file_path, 'w', encoding='utf-8') as i:
            json.dump(custom_verb, i, ensure_ascii=False, indent=4)

        del_embed = discord.Embed(title='已刪除詞彙', description=f'{詞彙1} ⇄ {詞彙2}')
        await interaction.response.send_message(embed=del_embed)

    else:
        await interaction.response.send_message('此組自訂詞彙不存在！')
    

client.run(token)