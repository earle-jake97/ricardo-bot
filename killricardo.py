import math
import random
import discord
from discord.ext import commands, tasks
import sqlite3
import asyncio
import json
from discord.ui import Button, View

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
CURRENCY_NAME = config.get('CURRENCY_NAME', "currency")
BOSS_HP_SCALING = config.get('BOSS_HP_SCALING', 1.05)



class DatabaseHandler:
    def __init__(self, db_path='currency.db'):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_boss_current_hp(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT hp FROM ricardo_hp WHERE id = 1')
            return c.fetchone()

    def update_boss_current_hp(self, new_hp):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE ricardo_hp SET hp = ? WHERE id = 1', (new_hp,))
            conn.commit()

    def get_boss_deaths(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT death_count FROM ricardo_hp WHERE id = 1')
            return c.fetchone()

    def update_boss_deaths(self, death_count):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE ricardo_hp SET death_count = ? WHERE id = 1', (death_count,))
            conn.commit()

    def get_boss_max_hp(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT initial_hp FROM ricardo_hp WHERE id = 1')
            return c.fetchone()

    def update_boss_max_hp(self, new_max_hp):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE ricardo_hp SET initial_hp = ? WHERE id = 1', (new_max_hp,))
            conn.commit()

    def update_all_boss(self, new_hp, new_death_count, new_max_hp):
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

    # This will fetch everyone who has dealt damage to boss on his current life
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
    
    def fetch_all_by_contribution(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT username, total_contribution FROM users ORDER BY total_contribution DESC')
            return c.fetchall()

    def get_total_contribution(self, user_id):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'SELECT total_contribution FROM users WHERE user_id = ?', (user_id,))
            return c.fetchone()

    def update_total_contribution(self, user_id, total_contribution):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO users (user_id, total_contribution) VALUES (?, ?)', (user_id, total_contribution))
            c.execute('UPDATE users SET total_contribution = total_contribution + ? WHERE user_id = ?',
                      (total_contribution, user_id))
            conn.commit()
    
    def get_bonus_crit_rate(self, user_id):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'SELECT bonus_crit_rate FROM users WHERE user_id = ?', (user_id,))
            return c.fetchone()

    def update_bonus_crit_rate(self, user_id, bonus_crit_rate):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO users (user_id, bonus_crit_rate) VALUES (?, 0.0)', (user_id, bonus_crit_rate))
            c.execute('UPDATE users SET bonus_crit_rate = bonus_crit_rate + ? WHERE user_id = ?',
                      (bonus_crit_rate, user_id))
            conn.commit()
    
    def get_crit_damage_modifier(self, user_id):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'SELECT crit_damage_modifier FROM users WHERE user_id = ?', (user_id,))
            return c.fetchone()

    def update_crit_damage_modifier(self, user_id, crit_damage_modifier):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO users (user_id, crit_damage_modifier) VALUES (?, 0.0)', (user_id, crit_damage_modifier))
            c.execute('UPDATE users SET crit_damage_modifier = crit_damage_modifier + ? WHERE user_id = ?',
                      (crit_damage_modifier, user_id))
            conn.commit()
        


# specify prefix
bot = discord.Bot(command_prefix='!', intents=intents)
db_handler = DatabaseHandler()

def create_leaderboard_embed(page=0, per_page=10):
    leaderboard = db_handler.fetch_all_by_contribution()
    max_pages = (len(leaderboard) // per_page) + (1 if len(leaderboard) % per_page > 0 else 0)

    start_index = page * per_page
    end_index = start_index + per_page
    leaderboard_page = leaderboard[start_index:end_index]

    embed = discord.Embed(title="Leaderboard", description=f"Page {page + 1}/{max_pages}", color=discord.Color.blurple())

    # Add fields for each user with a profile button
    for idx, (username, total_contribution) in enumerate(leaderboard_page, start=start_index + 1):
        # Add user information to the embed with the profile button
        formatted_total_contribution = "{:,}".format(total_contribution)
        embed.add_field(
            name=f"{idx}. {username}",
            value=f"Total damage dealt: {formatted_total_contribution}",
            inline=False
        )

    return embed, max_pages

class LeaderboardView(View):
    def __init__(self, author, page, max_pages):
        super().__init__(timeout=60)
        self.author = author
        self.current_page = page
        self.max_pages = max_pages
        self.previous_button = Button(label="Previous", style=discord.ButtonStyle.primary)
        self.next_button = Button(label="Next", style=discord.ButtonStyle.primary)
        self.update_buttons()
        self.previous_button.callback = self.previous
        self.next_button.callback = self.next

    def update_buttons(self):
        self.clear_items()
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.max_pages - 1
        self.add_item(self.previous_button)
        self.add_item(self.next_button)

    async def interaction_check(self, interaction):
        return interaction.user == self.author

    async def previous(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            embed, max_pages = create_leaderboard_embed(self.current_page)
            self.max_pages = max_pages
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)

    async def next(self, interaction: discord.Interaction):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            embed, max_pages = create_leaderboard_embed(self.current_page)
            self.max_pages = max_pages
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)


def calculate_income(pp: int):
    return (math.floor(pp * PP_MULTIPLIER)) + BASE_INCOME

# Uses player stats to calculate damage dealt
def calculate_damage(currency, player_id, boss_health):
    # Step 1: Calculate the base damage
    base_damage = currency
    crit = ""
    # Get the critical chance and damage modifier
    critical_chance = BASE_CRIT_CHANCE + db_handler.get_bonus_crit_rate(player_id)[0]
    critical_damage_modifier = BASE_CRIT_DAMAGE + db_handler.get_crit_damage_modifier(player_id)[0]

    # If the base damage would have killed, refund the excess currency spent
    if base_damage > boss_health:
        excess_base = base_damage - boss_health
        return base_damage, excess_base
    
    ran = random.uniform(1, 1.1) # Damage can deal up to 10% more
    damage_range = base_damage * ran
    ran = random.randrange(1, 100, 1)
    if ran < critical_chance * 100:
        actual_damage = round(damage_range * critical_damage_modifier)
        crit = " critically💥"
    else:
        actual_damage = round(damage_range)

    return actual_damage, 0, crit


def respawn_boss(boss_deaths, boss_max_hp):
    boss_deaths += 1
    boss_new_max_hp = int(BOSS_HP_SCALING * boss_max_hp)
    db_handler.update_all_boss(boss_new_max_hp, boss_deaths, boss_new_max_hp)

# Hurts the boss and adds the damage dealt to the player's contribution
def hurt_boss(attacker_id, damage_dealt, boss_max_hp, boss_current_hp):
    percentage_contributed = damage_dealt/boss_max_hp

    db_handler.update_boss_current_hp(boss_current_hp - damage_dealt)
    db_handler.update_participation_percentage(attacker_id, percentage_contributed)

# Rewards PP and returns a message showing all player awards
def award_on_kill():
    participants = db_handler.fetch_non_zero_participants()
    message = ""
    prev_boss_max_hp = int(db_handler.get_boss_max_hp()[0] / BOSS_HP_SCALING)
    for user_id, username, percentage in participants:
        damage_dealt = int(prev_boss_max_hp * percentage)
        percentage *= 100
        pp_gain = round(percentage)
        message += f"{username} dealt {damage_dealt} ({percentage: .2f}%) total damage and gained {pp_gain} PP!\n"
        db_handler.update_pp(user_id, pp_gain)
    db_handler.reset_percentages()
    return message

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


@bot.command(description="Show the leaderboard")
async def leaderboard(ctx):
    embed, max_pages = create_leaderboard_embed()
    view = LeaderboardView(ctx.author, 0, max_pages)
    await ctx.respond(embed=embed, view=view, ephemeral=True)

@bot.command(description="Check someone's balance. If no arguments supplied, check your own balance.")
async def balance(ctx, member: discord.Member = None):
    user = member or ctx.author
    user_id = user.id
    balance = db_handler.get_balance(user_id)[0]
    if member:
        await ctx.respond(f'Their balance is {balance} {CURRENCY_NAME}.')
    else:
        await ctx.respond(f'Your balance is {balance} {CURRENCY_NAME}.')

# Show all contribution to the current kill


@bot.command(description="Display participation percentages for all users on the current boss.")
async def show_contributions(ctx):
    participants = db_handler.fetch_non_zero_participants()
    if not participants:
        await ctx.respond("No contributions to display.")
        return

    message = "All contributors:\nUsername        | Contribution\n-------------------------------\n"
    for user_id, username, percentage in participants:
        percentage_display = percentage * 100
        message += f"{username:<15} | {percentage_display:.2f}%\n"

    await ctx.respond(f"```\n{message}\n```")

    # check user's pp


@bot.command(description="Check someone's Participation Points. If no arguments supplied, check your own PP.")
async def pp(ctx, member: discord.Member = None):
    user = member or ctx.author
    user_id = user.id
    pp = db_handler.get_pp(user_id)[0]
    income = calculate_income(pp)
    if member:
        await ctx.respond(f'They have is {pp} PP. This nets them {income - BASE_INCOME} extra {CURRENCY_NAME} per minute for a total of {income} {CURRENCY_NAME} per minute.')
    else:
        await ctx.respond(f'You have {pp} PP. This nets you {income - BASE_INCOME} extra {CURRENCY_NAME} per minute for a total of {income} {CURRENCY_NAME} per minute.')


@bot.command(description="This is top secret")
async def add(ctx, amount: int, member: discord.Member):
    if ctx.author.id == 165630744826347520:
        user_id = member.id
        db_handler.update_balance(user_id, amount)
        balance = db_handler.get_balance(user_id)[0]
        await ctx.respond(f'{amount} {CURRENCY_NAME} have been added. Their new balance is {balance} {CURRENCY_NAME}.')



@bot.command(description=f"Transfer {CURRENCY_NAME} to another user.")
async def transfer(ctx, member: discord.Member, amount: int):
    if amount < 0:
        await ctx.respond("Invalid transaction. You may only transfer 1 or more {CURRENCY_NAME}")
        return
    sender_id = ctx.author.id
    receiver_id = member.id
    sender_balance = db_handler.get_balance(sender_id)[0]

    if sender_balance < amount:
        await ctx.respond('You do not have enough {CURRENCY_NAME} to complete this transfer.')
        return

    db_handler.update_balance(sender_id, -amount)
    db_handler.update_balance(receiver_id, amount)
    await ctx.respond(f'{amount} {CURRENCY_NAME} have been transferred to {member.mention}.')


@bot.command(description="Shows boss's death count")
async def deaths(ctx):
    death_count = db_handler.get_boss_deaths()[0]
    await ctx.respond(f'{BOSS_NAME} has been killed {death_count} times.')


@bot.command(description=f"Let's kill {BOSS_NAME}! Enter an integer value or 'all'")
async def attack(ctx, amount_spent: str):
    attacker_id = ctx.author.id
    balance = db_handler.get_balance(attacker_id)[0]

    if amount_spent.lower() == "all": # Check if user wants to spend all of their currency
        amount_spent = balance
    else:
        try:
            amount_spent = int(amount_spent)
        except ValueError:
            await ctx.respond(f'Invalid input: {amount_spent}. Please enter a valid number or "all".')
            return
    
    boss_current_hp = db_handler.get_boss_current_hp()[0]
    boss_max_hp = db_handler.get_boss_max_hp()[0]
    boss_death_count = db_handler.get_boss_deaths()[0]
    
    damage_dealt, refund_amount, crit = calculate_damage(amount_spent, attacker_id, boss_current_hp)
    hurt_boss(attacker_id, damage_dealt, boss_max_hp, boss_current_hp)

    boss_current_hp = db_handler.get_boss_current_hp()[0]
    
    if boss_current_hp <= 0:
        damage_dealt -= boss_current_hp # ensures that players won't be granted extra total contribution
        respawn_boss(boss_death_count, boss_max_hp)
        amount_spent -= refund_amount
        new_boss_max_hp = db_handler.get_boss_max_hp()[0]

        message = f'{BOSS_NAME} IS DEAD! {BOSS_NAME} has now died {boss_death_count} times. {BOSS_NAME} has respawned with {new_boss_max_hp}/{new_boss_max_hp}.\n'
        message += award_on_kill()

        await ctx.respond(f'{message}')
    else:
        await ctx.respond(f"{ctx.author.name} spent {amount_spent} {CURRENCY_NAME} to{crit} deal {damage_dealt} damage to {BOSS_NAME}.\n{BOSS_NAME}'s new HP: {boss_current_hp}/{boss_max_hp}")
    
    db_handler.update_balance(attacker_id, -amount_spent)
    db_handler.update_total_contribution(attacker_id, damage_dealt)
    
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


@bot.command(description="Shows boss's HP")
async def hp(ctx):
    hp, max_hp = db_handler.get_boss_current_hp()[0], db_handler.get_boss_max_hp()[0]
    await ctx.respond(f'{BOSS_NAME}: {hp}/{max_hp}')

@bot.command(description="View a user's profile or your own")
async def profile(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    user_id = member.id

    total_contribution = "{:,}".format(db_handler.get_total_contribution(user_id)[0])
    pp = db_handler.get_pp(user_id)[0]
    crit_rate = db_handler.get_bonus_crit_rate(user_id)[0] + BASE_CRIT_CHANCE * 100
    crit_damage = db_handler.get_crit_damage_modifier(user_id)[0] + BASE_CRIT_DAMAGE * 100
    current_balance = "{:,}".format(db_handler.get_balance(user_id)[0])

    # Accessing display_avatar for Pycord
    avatar_url = member.display_avatar.url

    # Create an embed to display the profile information
    embed = discord.Embed(title=f"Profile - {member.name}", color=discord.Color.blurple())
    embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="Current Balance", value=f"{current_balance} {CURRENCY_NAME}", inline=False)
    embed.add_field(name="Total Contribution", value=f"{total_contribution} damage dealt", inline=False)
    embed.add_field(name="PP", value=f"{pp}", inline=False)
    embed.add_field(name="Critical Rate", value=f"{crit_rate}%", inline=False)
    embed.add_field(name="Critical Damage", value=f"{crit_damage}%", inline=False)

    await ctx.respond(embed=embed)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    bot.loop.create_task(add_currency_task())

bot.run(TOKEN)
