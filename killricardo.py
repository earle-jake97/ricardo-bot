from random import randrange
import discord
from discord.ext import commands
import sqlite3
import datetime
import asyncio

with open('token.txt', 'r') as file:
    TOKEN = file.read().rstrip()
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = True
intents.messages = True

LTG_CLIPS = ["https://cdn.discordapp.com/attachments/130154381717798912/1250678808768675850/ltg_kys_2.mp4?ex=666bd0e8&is=666a7f68&hm=559b873447a4eed5eead9d56631eaf07206333739889636b3048fb643209c774&", "https://cdn.discordapp.com/attachments/130154381717798912/1250684405408595999/ltg_kys.mp4?ex=666bd61e&is=666a849e&hm=539b579e28402abfd078cc9996bc72b22e10a02b51fc2125616e37948165ffc3&", "https://cdn.discordapp.com/attachments/130154381717798912/1250684482441445469/ltg_180.mp4?ex=666bd631&is=666a84b1&hm=cefc3f71006de9ddab3a08243843fc9e1179eacb314474c42a116cf15fb31f03&"]

KILL_COST = 8640
RICARDO_ID = 233077250675703808

# specify prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# Custom Help Command
class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Bot Commands", color=discord.Color.blue())
        for cog, commands in mapping.items():
            filtered_commands = await self.filter_commands(commands, sort=True)
            command_signatures = [self.get_command_signature(c) for c in filtered_commands if c.name != 'add']
            if command_signatures:
                embed.add_field(name=cog.qualified_name if cog else "No Category", value="\n".join(command_signatures), inline=False)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=self.get_command_signature(command), description=command.help or "No help available", color=discord.Color.blue())
        channel = self.get_destination()
        await channel.send(embed=embed)

# Set the custom help command
bot.help_command = CustomHelpCommand()

# Function to get Ricardo's HP and death count
def get_ricardo_stats():
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('SELECT hp, death_count, initial_hp FROM ricardo_hp WHERE id = 1')
    result = c.fetchone()
    conn.close()
    return result

def update_ricardo_hp(new_hp):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('UPDATE ricardo_hp SET hp = ? WHERE id = 1', (new_hp,))
    conn.commit()
    conn.close()

def respawn_ricardo(new_hp, death_count, initial_hp):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('UPDATE ricardo_hp SET hp = ?, death_count = ?, initial_hp = ? WHERE id = 1', (new_hp, death_count, initial_hp))
    conn.commit()
    conn.close()



# get balance
def get_balance(user_id):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def fetch_users():
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    users = c.fetchall()
    conn.close()
    return users

# update command
def update_balance(user_id, amount):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)', (user_id,))
    c.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

# add currency to all users every 5 seconds
async def add_currency_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        conn = sqlite3.connect('currency.db')
        c = conn.cursor()
        c.execute('SELECT user_id FROM users')
        users = c.fetchall()

        for user_id in users:
            update_balance(user_id[0], 1)  # 1 vbuck to each user

        conn.close()

        await asyncio.sleep(5)  # sleep for 5 seconds before adding vbucks again

# check user's balance
@bot.command(help="Check someone's balance. If no arguments supplied, check your own balance.")
async def balance(ctx, member: discord.Member = None):
    user = member or ctx.author
    user_id = user.id
    balance = get_balance(user_id)
    if member:
        await ctx.send(f'Their balance is {balance} Vbucks.')
    else:
        await ctx.send(f'Your balance is {balance} Vbucks.')

@bot.command(help="This is top secret")
async def add(ctx, amount: int, ID):
    if ctx.author.id == 165630744826347520:
      update_balance(ID, amount)
      balance = get_balance(ID)
      await ctx.send(f'{amount} Vbucks have been added. Their new balance is {balance} Vbucks.')

# transfer vbuckks
@bot.command(help="Transfer Vbucks to another user. Usage: !transfer recipient amount")
async def transfer(ctx, member: discord.Member, amount: int):
    if amount < 0:
        await ctx.send("Fuck you Matt")
        return
    sender_id = ctx.author.id
    receiver_id = member.id
    sender_balance = get_balance(sender_id)

    if sender_balance < amount:
        await ctx.send('You do not have enough Vbucks to complete this transfer.')
        return

    update_balance(sender_id, -amount)
    update_balance(receiver_id, amount)
    await ctx.send(f'{amount} Vbucks have been transferred to {member.mention}.')

@bot.command(help="Shows Ricardo's death count")
async def deaths(ctx):
    hp, death_count, initial_hp = get_ricardo_stats()
    await ctx.send(f'Ricardo has been killed {death_count} times.')

# KILL RICARDO
@bot.command(help="KILL RICARDO")
async def kill(ctx, amount: int):
    user_id = ctx.author.id
    username = str(ctx.author)
    balance = get_balance(user_id)

    if balance < amount:
        await ctx.send(f'You don\'t have enough Vbucks to attack Ricardo :( You only have {balance} Vbucks')
        return
    if amount <= 0:
        await ctx.send(f'Fuck you again Matt')
        return
    
    hp, death_count, initial_hp = get_ricardo_stats()
    new_hp = hp - amount

    if new_hp <= 0:
        death_count += 1
        new_initial_hp = int(initial_hp * 1.15)
        respawn_ricardo(new_initial_hp, death_count, new_initial_hp)
        num = randrange(0,len(LTG_CLIPS),1)
        await ctx.send(f'KILL Ricardo! He has been killed {death_count} times. His new HP is {new_initial_hp}. {LTG_CLIPS[num]}')
    else:
        update_ricardo_hp(new_hp)
        await ctx.send(f'You dealt {amount} damage to Ricardo. His remaining HP is {new_hp}.')

    update_balance(user_id, -amount)



# Handle unknown commands
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('''This isn't a real command <:Weirdge:1250870748944404490> Type !help''')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Check your args <:Weirdge:1250870748944404490>')
    # else:
    #     await ctx.send('Something went wrong with this command')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  
    
    user_id = message.author.id
    username = str(message.author)

    # check if in database
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()

    if not result:
        # add user if not in database
        c.execute('INSERT INTO users (user_id, username, balance) VALUES (?, ?, 0)', (user_id, username))
        conn.commit()
        print(f'Added {username} to the database.')

    conn.close()

    await bot.process_commands(message)

@bot.command(help="Shows Ricardo's HP")
async def hp(ctx):
    hp, death_count, initial_hp = get_ricardo_stats()
    await ctx.send(f'Ricardo: {hp}/{initial_hp}')
    
# display top 10
@bot.command(help="Shows the top ten highest balances")
async def leaderboards(ctx):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    
    # display top 10 in descending order
    c.execute('SELECT user_id, username, balance FROM users ORDER BY balance DESC LIMIT 10')
    users = c.fetchall()
    
    conn.close()

    if not users:
        await ctx.send('No users found in the database.')
        return
    
    # display table
    table_str = '```Username       | Balance\n'
    table_str += '--------------------------\n'
    for user in users:
        table_str += f'{user[1]:<14} | {user[2]}\n'
    table_str += '```'

    await ctx.send(table_str)

    
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    bot.loop.create_task(add_currency_task())  

bot.run(TOKEN)