from random import randrange
import discord
from discord.ext import commands
import sqlite3
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
bot = discord.Bot(command_prefix='!', intents=intents)

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

def get_pp(user_id):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('SELECT pp FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_pp(user_id, amount):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, pp) VALUES (?, 0)', (user_id,))
    c.execute('UPDATE users SET pp = pp + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_percentage(user_id):    
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('SELECT participation_percentage FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_percentage(user_id, amount):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, participation_percentage) VALUES (?, 0)', (user_id,))
    c.execute('UPDATE users SET participation_percentage = participation_percentage + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def reset_percentages():
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('UPDATE users SET participation_percentage = 0.0')
    conn.commit()
    conn.close()

def fetch_non_zero_participants():
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('SELECT user_id, username, participation_percentage FROM users WHERE participation_percentage != 0.0')
    users = c.fetchall()
    conn.close()
    return users


# add currency to all users every 5 seconds
async def add_currency_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        conn = sqlite3.connect('currency.db')
        c = conn.cursor()
        c.execute('SELECT user_id FROM users')
        users = c.fetchall()

        for user in users:
            user_id = user[0]
            pp = get_pp(user_id)
            num = (round(pp/10)) + 18
            update_balance(user_id, num)  # 1 vbuck to each user

        conn.close()

        await asyncio.sleep(60)  # sleep for 60 seconds before adding vbucks again

# check user's balance
@bot.command(description="Check someone's balance. If no arguments supplied, check your own balance.")
async def balance(ctx, member: discord.Member = None):
    user = member or ctx.author
    user_id = user.id
    balance = get_balance(user_id)
    if member:
        await ctx.respond(f'Their balance is {balance} Vbucks.')
    else:
        await ctx.respond(f'Your balance is {balance} Vbucks.')

# Show all contribution to the current kill
@bot.command(description="Display participation percentages for all users on the current Ricardo.")
async def show_contributions(ctx):
    participants = fetch_non_zero_participants()
    if not participants:
        await ctx.send("No contributions to display.")
        return

    message = "All contributors:\nUsername        | Contribution\n-------------------------------\n"
    for user_id, username, percentage in participants:
        percentage_display = percentage * 100
        message += f"{username:<15} | {percentage_display:.2f}%\n"

    await ctx.send(f"```\n{message}\n```")

    # check user's pp
@bot.command(description="Check someone's Participation Points. If no arguments supplied, check your own PP.")
async def pp(ctx, member: discord.Member = None):
    user = member or ctx.author
    user_id = user.id
    pp = get_pp(user_id)
    income = round(pp/10)
    if member:
        await ctx.respond(f'They have is {pp} PP. This nets them {income} extra Vbucks per minute')
    else:
        await ctx.respond(f'You have {pp} PP. This nets you {income} extra Vbucks per minute')

@bot.command(description="This is top secret")
async def add(ctx, amount: int, id):
    if ctx.author.id == 165630744826347520:
      update_balance(id, amount)
      balance = get_balance(id)
      await ctx.respond(f'{amount} Vbucks have been added. Their new balance is {balance} Vbucks.')

# transfer vbuckks
@bot.command(description="Transfer Vbucks to another user. Usage: !transfer recipient amount")
async def transfer(ctx, member: discord.Member, amount: int):
    if amount < 0:
        await ctx.respond("Fuck you Matt")
        return
    sender_id = ctx.author.id
    receiver_id = member.id
    sender_balance = get_balance(sender_id)

    if sender_balance < amount:
        await ctx.respond('You do not have enough Vbucks to complete this transfer.')
        return

    update_balance(sender_id, -amount)
    update_balance(receiver_id, amount)
    await ctx.respond(f'{amount} Vbucks have been transferred to {member.mention}.')

@bot.command(description="Shows Ricardo's death count")
async def deaths(ctx):
    hp, death_count, initial_hp = get_ricardo_stats()
    await ctx.respond(f'Ricardo has been killed {death_count} times.')

# TROLL RICARDO
@bot.command(description="KILL RICARDO")
async def heal(ctx, amount):
    if isinstance(amount, str) and amount != "all":
        return
    if ctx.author.id != RICARDO_ID:
        await ctx.respond(f'Only Ricardo can heal himself :(')
        return
    if balance < amount:
        await ctx.respond(f'You don\'t have enough Vbucks to heal yourself :( You only have {balance} Vbucks')
        return
    if amount <= 0:
        await ctx.respond(f'Fuck you again Matt')
        return
    hp, death_count, initial_hp = get_ricardo_stats()

    new_hp = hp - amount

    if new_hp <= 0:
        amount = min(hp, amount)
        death_count += 1
        new_initial_hp = int(initial_hp * 1.05)
        respawn_ricardo(new_initial_hp, death_count, new_initial_hp)
        num = randrange(0,len(LTG_CLIPS),1)
        await ctx.respond(f'KILL Ricardo! He has been killed {death_count} times. His new HP is {new_initial_hp}. {LTG_CLIPS[num]}')
    else:
        update_ricardo_hp(new_hp)
        await ctx.respond(f'SIKE YOU JUST TOOK {amount} DAMAGE RICARDO 😂😂😂😂😂😂')

    update_balance(RICARDO_ID, -amount)

# KILL RICARDO
@bot.command(description="KILL RICARDO. Enter an integer value or 'all'")
async def kill(ctx, amount: str):
    user_id = ctx.author.id
    balance = get_balance(user_id)
    if amount.lower() == "all":
        amount = balance
    else:
        try:
            amount = int(amount)
        except ValueError:
            await ctx.respond(f'Invalid amount: {amount}. Please enter a valid number or "all".')
            return

    if balance < amount:
        await ctx.respond(f'You don\'t have enough Vbucks to attack Ricardo :( You only have {balance} Vbucks')
        return
    
    if amount <= 0:
        await ctx.respond(f'Fuck you again Matt')
        return

    hp, death_count, initial_hp = get_ricardo_stats()

    ran = randrange(1, 100, 1)
    if ran < 10:
        crit = True
        await ctx.respond(f'CRITICAL')
        amount = int(amount * 1.5)  # Ensure amount is an integer after multiplication
    else:
        crit = False

    new_hp = hp - amount
    percentage = amount/initial_hp
    if new_hp <= 0:
        if crit:
            amount = int(amount / 1.5)  # Convert back to original amount before crit multiplier
        amount = min(hp, amount)
        percentage = amount/initial_hp # Remove overkill amount from percent contribution

        update_percentage(user_id, percentage)

        death_count += 1
        new_initial_hp = int(initial_hp * 1.05)
        respawn_ricardo(new_initial_hp, death_count, new_initial_hp)
        num = randrange(0, len(LTG_CLIPS), 1)
        ricardo_mention = f'<@{RICARDO_ID}>'
        participants = fetch_non_zero_participants()

        message = f'KILL {ricardo_mention}! He has been killed {death_count} times. His new HP is {new_initial_hp}. {LTG_CLIPS[num]}\n'
        for user_id, username, percentage in participants: # Award PP to every user who contributed to the kill
            percentage *= 100
            pp_gain = round(percentage)
            message += f"{username} contributed {percentage:.2f}% and gained {pp_gain} PP!\n"
            update_pp(user_id, pp_gain)
        await ctx.respond(f'{message}')
        reset_percentages()
        
    else:
        update_ricardo_hp(new_hp)
        update_percentage(user_id, percentage)
        await ctx.respond(f'You dealt {amount} damage to Ricardo. His remaining HP is {new_hp}.')

    update_balance(user_id, -amount)




# Handle unknown commands
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.respond('''This isn't a real command <:Weirdge:1250870748944404490> Type !description''')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.respond('Check your args <:Weirdge:1250870748944404490>')
    # else:
    #     await ctx.respond('Something went wrong with this command')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  
    if message.author.bot: return
    
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

@bot.command(description="Shows Ricardo's HP")
async def hp(ctx):
    hp, death_count, initial_hp = get_ricardo_stats()
    await ctx.respond(f'Ricardo: {hp}/{initial_hp}')
    
# display top 10
@bot.command(description="Shows the top ten highest balances")
async def leaderboards(ctx):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    
    # display top 10 in descending order
    c.execute('SELECT user_id, username, balance FROM users ORDER BY balance DESC LIMIT 10')
    users = c.fetchall()
    
    conn.close()

    if not users:
        await ctx.respond('No users found in the database.')
        return
    
    # display table
    table_str = '```Username       | Balance\n'
    table_str += '--------------------------\n'
    for user in users:
        table_str += f'{user[1]:<14} | {user[2]}\n'
    table_str += '```'

    await ctx.respond(table_str)

    
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    bot.loop.create_task(add_currency_task())  

bot.run(TOKEN)