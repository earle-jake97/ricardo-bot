import math
from random import randrange
import discord
from discord.ext import commands, tasks
import sqlite3
import asyncio
import json

with open('config.json', 'r') as file:
    config = json.load(file)

with open('token.txt', 'r') as file:
    TOKEN = file.read().rstrip()

with open('clips.txt', 'r') as file:
    CLIPS = [link.strip().strip('""') for link in file.read().split(',')]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = True
intents.messages = True

BOSS_ID = config.get('BOSS_ID', 0)
BOSS_NAME = config.get('BOSS_NAME', "Fella")
BASE_INCOME = config.get('BASE_INCOME', 18)
PP_MULTIPLIER = config.get('PP_MULTIPLIER', 0.1)
PAY_INTERVAL = config.get('PAY_INTERVAL', 60) # How often the bot distributes funds, in seconds
BASE_CRIT_CHANCE = config.get('BASE_CRIT_CHANCE', 0.1)
BASE_CRIT_DAMAGE = config.get('BASE_CRIT_DAMAGE', 1.5)



class DatabaseHandler:
    def __init__(self, db_path='currency.db'):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_ricardo_current_hp(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT hp FROM ricardo_hp WHERE id = 1')
            return c.fetchone()

    def update_ricardo_current_hp(self, new_hp):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE ricardo_hp SET hp = ? WHERE id = 1', (new_hp,))
            conn.commit()

    def get_ricardo_deaths(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT death_count FROM ricardo_hp WHERE id = 1')
            return c.fetchone()

    def update_ricardo_deaths(self, death_count):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE ricardo_hp SET death_count = ? WHERE id = 1', (death_count,))
            conn.commit()

    def get_ricardo_max_hp(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT initial_hp FROM ricardo_hp WHERE id = 1')
            return c.fetchone()

    def update_ricardo_max_hp(self, new_max_hp):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE ricardo_hp SET initial_hp = ? WHERE id = 1', (new_max_hp,))
            conn.commit()

    def update_all_ricardo(self, new_hp, new_death_count, new_max_hp):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE ricardo_hp SET hp = ?, death_count = ?, initial_hp = ? WHERE id = 1',
                      (new_hp, new_death_count, new_max_hp))
            conn.commit()

    # This will fetch everything in the user table
    def fetch_all_users(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users')
            return c.fetchall()

    # This will fetch everyone who has dealt damage to Ricardo on his current life
    def fetch_non_zero_participants(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'SELECT user_id, username, participation_percentage FROM users WHERE participation_percentage != 0.0')
            return c.fetchall()

    # This is intended to be used to set everyone's participation percentage after a kill back to 0.
    def reset_percentages(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET participation_percentage = 0.0')
            conn.commit()

    def get_username(self, user_id):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
            return c.fetchone()

    # This will probably never get used
    def update_username(self, user_id, username):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
            c.execute('UPDATE users SET username = ? WHERE user_id = ?',
                      (username, user_id))
            conn.commit()

    def get_balance(self, user_id):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            return c.fetchone()

    def update_balance(self, user_id, amount):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)', (user_id,))
            c.execute(
                'UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            conn.commit()

    def get_pp(self, user_id):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT pp FROM users WHERE user_id = ?', (user_id,))
            return c.fetchone()

    def update_pp(self, user_id, amount):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO users (user_id, pp) VALUES (?, 0)', (user_id,))
            c.execute('UPDATE users SET pp = pp + ? WHERE user_id = ?',
                      (amount, user_id))
            conn.commit()

    def get_participation_percentage(self, user_id):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'SELECT participation_percentage FROM users WHERE user_id = ?', (user_id,))
            return c.fetchone()

    def update_participation_percentage(self, user_id, amount):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO users (user_id, participation_percentage) VALUES (?, 0.0)', (user_id,))
            c.execute('UPDATE users SET participation_percentage = participation_percentage + ? WHERE user_id = ?',
                      (amount, user_id))
            conn.commit()

    def insert_user(self, user_id, username):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()

            if not result:
                # add user if not in database
                c.execute(
                    'INSERT INTO users (user_id, username, balance) VALUES (?, ?, 0)', (user_id, username))
                conn.commit()
                print(f'Added {username} to the database.')


# specify prefix
bot = discord.Bot(command_prefix='!', intents=intents)
db_handler = DatabaseHandler()

def calculate_income(pp: int):
    return (math.floor(pp * PP_MULTIPLIER)) + BASE_INCOME

def calculate_damage(vbucks, critical_chance, critical_damage_modifier):
    critical_chance = BASE_CRIT_CHANCE + critical_chance
    damage = vbucks
    ran = randrange(1, 100, 1)
    if ran < critical_chance * 100:
        # Ensure amount is an integer after multiplication
        damage = int(vbucks * critical_damage_modifier)
        isCrit = True
    else: isCrit = False
    return damage, isCrit

# Adds currency to all registered users
async def add_currency_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        users = db_handler.fetch_all_users()
        for user in users:
            user_id = user[0]
            pp = db_handler.get_pp(user_id)[0]
            amount = calculate_income(pp)
            db_handler.update_balance(user_id, amount)
    
        await asyncio.sleep(PAY_INTERVAL)


@bot.command(description="Check someone's balance. If no arguments supplied, check your own balance.")
async def balance(ctx, member: discord.Member = None):
    user = member or ctx.author
    user_id = user.id
    balance = db_handler.get_balance(user_id)[0]
    if member:
        await ctx.respond(f'Their balance is {balance} Vbucks.')
    else:
        await ctx.respond(f'Your balance is {balance} Vbucks.')

# Show all contribution to the current kill


@bot.command(description="Display participation percentages for all users on the current Ricardo.")
async def show_contributions(ctx):
    participants = db_handler.fetch_non_zero_participants()[0]
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
    pp = db_handler.get_pp(user_id)[0]
    income = calculate_income(pp)
    if member:
        await ctx.respond(f'They have is {pp} PP. This nets them {income - BASE_INCOME} extra Vbucks per minute for a total of {income} Vbucks per minute.')
    else:
        await ctx.respond(f'You have {pp} PP. This nets you {income - BASE_INCOME} extra Vbucks per minute for a total of {income} Vbucks per minute.')


@bot.command(description="This is top secret")
async def add(ctx, amount: int, member: discord.Member):
    if ctx.author.id == 165630744826347520:
        user_id = member.id
        db_handler.update_balance(user_id, amount)
        balance = db_handler.get_balance(user_id)[0]
        await ctx.respond(f'{amount} Vbucks have been added. Their new balance is {balance} Vbucks.')



@bot.command(description="Transfer Vbucks to another user.")
async def transfer(ctx, member: discord.Member, amount: int):
    if amount < 0:
        await ctx.respond("Fuck you Matt")
        return
    sender_id = ctx.author.id
    receiver_id = member.id
    sender_balance = db_handler.get_balance(sender_id)[0]

    if sender_balance < amount:
        await ctx.respond('You do not have enough Vbucks to complete this transfer.')
        return

    db_handler.update_balance(sender_id, -amount)
    db_handler.update_balance(receiver_id, amount)
    await ctx.respond(f'{amount} Vbucks have been transferred to {member.mention}.')


@bot.command(description="Shows Ricardo's death count")
async def deaths(ctx):
    death_count = db_handler.get_ricardo_deaths()[0]
    await ctx.respond(f'{BOSS_NAME} has been killed {death_count} times.')

# KILL RICARDO


@bot.command(description="KILL {BOSS_NAME}. Enter an integer value or 'all'")
async def kill(ctx, amount: str):
    og_user_id = ctx.author.id
    balance = db_handler.get_balance(og_user_id)[0]
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

    hp = db_handler.get_ricardo_current_hp()[0]
    death_count = db_handler.get_ricardo_deaths()[0]
    max_hp = db_handler.get_ricardo_max_hp()[0]

    # change this to reflect on player stats later
    calc = calculate_damage(amount, 0.0, 1.0)
    damage_dealt = calc[0]
    crit = calc[1]

    new_hp = hp - damage_dealt
    percentage_contributed = amount/max_hp
    if new_hp <= 0:
        if crit:
            # Convert back to original amount before crit multiplier
            amount = int(amount / BASE_CRIT_DAMAGE)
        amount = min(hp, amount)
        percentage_contributed = amount/max_hp  # Remove overkill amount from percent contribution

        db_handler.update_participation_percentage(og_user_id, percentage_contributed)

        death_count += 1
        new_max_hp = int(max_hp * 1.05)
        # Reset Ricardo's stats for new life
        db_handler.update_all_ricardo(new_max_hp, death_count, new_max_hp)
        num = randrange(0, len(CLIPS), 1)
        ricardo_mention = f'<@{BOSS_ID}>'
        participants = db_handler.fetch_non_zero_participants()

        message = f'KILL {ricardo_mention}! He has been killed {
            death_count} times. His new HP is {new_max_hp}. {CLIPS[num]}\n'
        for user_id, username, percentage in participants:  # Award PP to every user who contributed to the kill
            percentage *= 100
            pp_gain = round(percentage)
            message += f"{username} contributed {
                percentage:.2f}% and gained {pp_gain} PP!\n"
            db_handler.update_pp(user_id, pp_gain)
        await ctx.respond(f'{message}')
        db_handler.reset_percentages()

    else:
        db_handler.update_ricardo_current_hp(new_hp)
        db_handler.update_participation_percentage(og_user_id, percentage_contributed)
        await ctx.respond(f'You dealt {amount} damage to {BOSS_NAME}. His remaining HP is {new_hp}.')
        if crit:
            amount = int(amount / BASE_CRIT_CHANCE)

    db_handler.update_balance(og_user_id, -amount)


# Handle unknown commands
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.respond('''This isn't a real command <:Weirdge:1250870748944404490> Type !description''')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.respond('Check your args <:Weirdge:1250870748944404490>')
    else:
        await ctx.respond('Something went wrong with this command')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.author.bot:
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
        c.execute(
            'INSERT INTO users (user_id, username, balance) VALUES (?, ?, 0)', (user_id, username))
        conn.commit()
        print(f'Added {username} to the database.')

    conn.close()


@bot.command(description="Shows Ricardo's HP")
async def hp(ctx):
    hp, max_hp = db_handler.get_ricardo_current_hp()[0], db_handler.get_ricardo_max_hp()[0]
    await ctx.respond(f'{BOSS_NAME}: {hp}/{max_hp}')

# display top 10


@bot.command(description="Shows the top ten highest balances")
async def leaderboards(ctx):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()

    # display top 10 in descending order
    c.execute(
        'SELECT user_id, username, balance, pp FROM users ORDER BY pp DESC LIMIT 15')
    users = c.fetchall()

    conn.close()

    if not users:
        await ctx.respond('No users found in the database.')
        return

    # display table
    table_str = '```Username                     | Balance    | PP\n'
    table_str += '------------------------------------------------\n'
    for user in users:
        table_str += f'{user[1]:<28} | {user[2]:<10} | {user[3]}\n'
    table_str += '```'

    await ctx.respond(table_str)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    bot.loop.create_task(add_currency_task())

bot.run(TOKEN)
