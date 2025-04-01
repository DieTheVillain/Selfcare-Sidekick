#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Author: Matthew St. Jean
Consultant: Colin Dixon
Email: Matthew.StJean@gmail.com
Copyright (c) 2025 Matthew St. Jean
Description: A gamified Selfcare/Mental Health Assistant bot for Discord.
Install Link: https://discord.com/oauth2/authorize?client_id=1341457752891064350&permissions=292057869312&integration_type=0&scope=bot+applications.commands
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands

import sys
import asyncio
import json
import os
import pytz

import random
from datetime import datetime, time, timedelta

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Global dictionary to store pending buddy requests:
# Key: generated code, Value: dict with "inviter" (user id) and "expires" (datetime)
buddy_requests = {}

CONFIG_FILE = "config.json"
DATA_FILE = "users.json"

# Define a list of journaling prompts.
JOURNAL_PROMPTS = [
    "What is one challenging experience I've had recently?",
    "How did I cope with it?",
    "What could I have done differently?",
    "What can I learn from this experience?",
    "What are my healthy coping mechanisms?",
    "What unhealthy coping mechanisms do I sometimes use?",
    "How can I improve my healthy coping strategies?",
    "What am I grateful for today?",
    "What are three positive things that happened in the past week?",
    "What are my accomplishments, big or small?",
    "What are my mental health goals for the next week, month, or year?",
    "What specific steps can I take to achieve these goals?",
    "What support system do I need to reach these goals?",
    "What activities bring me joy and relaxation?",
    "How can I prioritize self-care in my daily routine?",
    "What boundaries do I need to set for my mental health?",
    "Write a letter to your younger self.",
    "Describe a time when you felt particularly vulnerable.",
    "What advice would you give to someone struggling with mental health issues?",
    "What are my hopes and dreams for the future?"
]

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"{CONFIG_FILE} not found. Please create one with your bot token.")

config = load_config()

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.decoder.JSONDecodeError:
            # File is empty or invalid JSON; return empty dict.
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# In-memory daily log for task completions: { user_id: { "completed": [task descriptions], "daily_points": int } }
daily_log = {}

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

###############################################################################
# --- UI Components for Time Zone Selection ---
###############################################################################
class TimezoneSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Eastern Time (US)", value="America/New_York"),
            discord.SelectOption(label="Central Time (US)", value="America/Chicago"),
            discord.SelectOption(label="Mountain Time (US)", value="America/Denver"),
            discord.SelectOption(label="Pacific Time (US)", value="America/Los_Angeles"),
            discord.SelectOption(label="Greenwich Mean Time", value="Etc/Greenwich"),
            discord.SelectOption(label="London", value="Europe/London"),
            discord.SelectOption(label="Paris", value="Europe/Paris"),
            discord.SelectOption(label="Tokyo", value="Asia/Tokyo")
        ]
        super().__init__(placeholder="Choose your time zone...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Store the selected time zone in the view for retrieval.
        self.view.value = self.values[0]
        self.view.stop()

class TimezoneView(discord.ui.View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.add_item(TimezoneSelect())
        self.value = None

###############################################################################
# /register Command: Registers a new user and sends initial DM instructions.
###############################################################################
@bot.tree.command(name="register", description="Register with Selfcare Sidekick.")
async def register(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id in data:
        await interaction.response.send_message("You are already registered. Please check your DMs for details.", ephemeral=True)
        return

    await interaction.response.send_message("Check your DMs to complete registration!", ephemeral=True)
    try:
        dm_channel = await interaction.user.create_dm()
        # Ask for the user's preferred name.
        await dm_channel.send("Welcome to Selfcare Sidekick! What would you like to be called? Please reply with your preferred name.")
        def check(m): 
            return m.author == interaction.user and m.channel == dm_channel
        name_msg = await bot.wait_for('message', check=check, timeout=120)
        preferred_name = name_msg.content.strip()
        registration_date = datetime.utcnow().isoformat()

        # Ask for time zone using a dropdown.
        view = TimezoneView(timeout=60)
        await dm_channel.send("Please select your time zone from the dropdown below:", view=view)
        await view.wait()
        timezone = view.value
        if not timezone:
            await dm_channel.send("No time zone selected. You can set your time zone later with /settimezone.")
            timezone = None

        # Define default tasks with a points value.
        original_defaults = [
            {"description": "Rise and shine - enjoy a refreshing glass of water!", "difficulty": 1},
            {"description": "Splash your face and greet the day with a smile.", "difficulty": 1},
            {"description": "Brush your teefs until they sparkle.", "difficulty": 1},
            {"description": "Hop in the shower if you're feeling a bit groggy.", "difficulty": 1},
            {"description": "Quickly brush your hair for a neat look.", "difficulty": 1},
            {"description": "Change into fresh undies and a comfy tee.", "difficulty": 1},
            {"description": "Fuel up with a healthy meal or snack.", "difficulty": 1},
            {"description": "Take a light walk or stretch to get moving.", "difficulty": 1},
            {"description": "Do something fun that makes your heart sing.", "difficulty": 1},
            {"description": "Check in with your mood and give yourself a high-five.", "difficulty": 1}
        ]
        additional_tasks = [
            {"description": "Meditate for 5 magical minutes.", "difficulty": 2},
            {"description": "Write one thing you're grateful for.", "difficulty": 2},
            {"description": "Drink another glass of water - hydrate like a hero!", "difficulty": 1},
            {"description": "Take 5 deep, mindful breaths.", "difficulty": 1},
            {"description": "Step outside and soak up some sunshine.", "difficulty": 1},
            {"description": "Play your favorite tune and dance a bit.", "difficulty": 2},
            {"description": "Read a few pages of a good book.", "difficulty": 2},
            {"description": "Do a quick, gentle stretch.", "difficulty": 1},
            {"description": "Tidy up a small corner for a clear mind.", "difficulty": 2},
            {"description": "Smile at yourself in the mirror.", "difficulty": 1},
            {"description": "Whip up a tasty healthy snack.", "difficulty": 2},
            {"description": "Take a short break from screens.", "difficulty": 1},
            {"description": "Enjoy a warm cup of tea or coffee.", "difficulty": 1},
            {"description": "Send a quick thank-you to someone.", "difficulty": 1},
            {"description": "Jot down one positive thought.", "difficulty": 1},
            {"description": "Do a 2-minute breathing exercise.", "difficulty": 1},
            {"description": "Celebrate one small win today.", "difficulty": 2},
            {"description": "Try a brief mindfulness exercise.", "difficulty": 2},
            {"description": "Doodle something fun.", "difficulty": 2},
            {"description": "Reach out with a kind word to a friend.", "difficulty": 1}
        ]
        available_tasks = original_defaults + additional_tasks

        # Build the numbered list string, showing the points value.
        tasks_list_str = "\n".join(
            [f"{i+1}. {task['description']} (points: {task['difficulty']})" for i, task in enumerate(available_tasks)]
        )
        prompt_text = (
            "Please select your first 10 tasks from the list by entering the numbers separated by commas (e.g., '1,3,5,...').\n"
            "Or simply reply with 'Default' to use the default set.\n\n" +
            tasks_list_str
        )
        await dm_channel.send(prompt_text)
        selection_msg = await bot.wait_for('message', check=check, timeout=120)
        selection = selection_msg.content.strip()
        if selection.lower() == "default":
            personal_defaults = original_defaults
        else:
            try:
                numbers = [int(n.strip()) for n in selection.split(",")]
                if len(set(numbers)) != 10 or any(n < 1 or n > len(available_tasks) for n in numbers):
                    await dm_channel.send("Invalid selection. Please select exactly 10 unique numbers from the list. Try /register again.")
                    return
                personal_defaults = [available_tasks[n-1] for n in numbers]
            except ValueError:
                await dm_channel.send("Invalid input format. Use comma-separated numbers or 'Default'.")
                return

        # Initialize user data, including personal defaults and daily tracker.
        data[user_id] = {
            "name": preferred_name,
            "registered": registration_date,
            "points": 10,
            "weekly_points": 10,
            "tasks": [],  # Custom tasks added later.
            "personal_defaults": personal_defaults,
            "daily_defaults": {"date": datetime.utcnow().date().isoformat(), "completed": []},
            "last_journal": "",
            "timezone": timezone
        }
        save_data(data)
        tasks_chosen = "\n".join(
            [f"- {task['description']} (points: {task['difficulty']})" for task in personal_defaults]
        )
        instructions = (
            f"Thanks {preferred_name}, you are now registered with Selfcare Sidekick and have been gifted **10 points**!\n\n"
            "Your personal default tasks for daily self-care:\n" +
            tasks_chosen +
            "\n\nUse `/complete` to mark tasks as done, `/add` to add custom tasks, `/remove` to remove tasks, and `/points` to check your points.\n"
            "Try `/journal` for a daily journal prompt. Have a great day!"
        )
        await dm_channel.send(instructions)
    except asyncio.TimeoutError:
        await dm_channel.send("Registration timed out. Please try again with /register.")

###############################################################################
# /list Command: View Your Tasks (with strike-through for completed tasks)
###############################################################################
@bot.tree.command(name="list", description="View your list of tasks for today.")
async def list_tasks(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message("You are not registered. Use /register to get started.", ephemeral=True)
        return

    today_str = datetime.utcnow().date().isoformat()
    
    # Format personal default tasks.
    personal_defaults = data[user_id].get("personal_defaults", [])
    formatted_defaults = []
    base_defaults = []
    default_points = []
    for task in personal_defaults:
        if isinstance(task, dict):
            base = task["description"]
            formatted = f"{base} (points: {task['difficulty']})"
            formatted_defaults.append(formatted)
            base_defaults.append(base)
            default_points.append(task["difficulty"])
        else:
            # If stored as plain strings.
            formatted_defaults.append(task)
            base_defaults.append(task)
            default_points.append(1)
    
    # Retrieve completed default tasks stored in JSON (raw descriptions).
    completed_defaults = []
    if "daily_defaults" in data[user_id] and data[user_id]["daily_defaults"].get("date") == today_str:
        completed_defaults = data[user_id]["daily_defaults"].get("completed", [])
    
    # Format custom tasks.
    custom_tasks_raw = [t for t in data[user_id].get("tasks", []) if t["deleted"] is None]
    formatted_custom = []
    base_custom = []
    for t in custom_tasks_raw:
        diff = t.get("difficulty", 2)
        base = t["description"]
        formatted = f"{base} ({t['type'].capitalize()}, points: {diff})"
        formatted_custom.append(formatted)
        base_custom.append(base)
    
    # For custom tasks, build completed list (formatted) for tasks marked complete.
    completed_custom = []
    for t in custom_tasks_raw:
        if t.get("is_completed"):
            diff = t.get("difficulty", 2)
            base = t["description"]
            completed_custom.append(f"{base} ({t['type'].capitalize()}, points: {diff})")
    
    # Combine default and custom tasks for full checklist.
    checklist = formatted_defaults + formatted_custom
    # Combine raw base descriptions for defaults and custom tasks.
    base_checklist = base_defaults + base_custom
    
    # Build the list of completed tasks.
    # For defaults, match by base description.
    completed = []
    for base in completed_defaults:
        # Look up the formatted string corresponding to the base in defaults.
        for i, base_val in enumerate(base_defaults):
            if base_val == base:
                completed.append(formatted_defaults[i])
                break
    # Add completed custom tasks.
    completed.extend(completed_custom)
    
    # Determine tasks that are not completed.
    not_completed = [task for task in checklist if task not in completed]
    
    # Build response lines.
    response_lines = ["Here are your tasks for today:"]
    for idx, task in enumerate(checklist, start=1):
        # Determine points value: for defaults, use stored value; for custom tasks, assume default is 2 if not provided.
        if idx <= len(formatted_defaults):
            points = default_points[idx - 1]
        else:
            points = 2
        if task in completed:
            line = f"{idx}. ~~{task}~~ (+{points})"
        else:
            line = f"{idx}. {task}"
        response_lines.append(line)
    
    message = "\n".join(response_lines)
    await interaction.response.send_message(message, ephemeral=True)

###############################################################################
# /add Command: Add a Custom Task (with is_completed field)
###############################################################################
@bot.tree.command(name="add", description="Add a custom task.")
@app_commands.describe(
    task_type="Specify 'daily' or 'weekly'",
    description="Description of the task",
    difficulty="Optional points value as an integer (default: 1 for daily, 2 for weekly)"
)
async def add(interaction: discord.Interaction, task_type: str, description: str, difficulty: int = None):
    task_type = task_type.lower()
    if task_type not in ["daily", "weekly"]:
        await interaction.response.send_message("Invalid task type. Specify 'daily' or 'weekly'.", ephemeral=True)
        return
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message("Not registered. Use /register first.", ephemeral=True)
        return

    # Set default difficulty if not provided.
    if difficulty is None:
        difficulty = 1 if task_type == "daily" else 2

    added_date = datetime.utcnow().isoformat()
    task_entry = {
        "description": description,
        "type": task_type,
        "added": added_date,
        "deleted": None,
        "is_completed": False,
        "difficulty": difficulty
    }
    existing_tasks = [t for t in data[user_id]["tasks"] if t["deleted"] is None]
    data[user_id]["tasks"].append(task_entry)
    gift_text = ""
    if len(existing_tasks) == 0:
        data[user_id]["points"] += 5
        data[user_id]["weekly_points"] += 5
        gift_text = " Bonus: 5 extra points for adding your first custom task!"
    save_data(data)
    await interaction.response.send_message(f"Task added: '{description}' as a {task_type} task with points: {difficulty}.{gift_text}", ephemeral=True)

###############################################################################
# /remove Command: Remove a Custom Task (Soft Delete)
###############################################################################
@bot.tree.command(name="remove", description="Remove a custom task.")
async def remove(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message("You are not registered. Use /register to register first.", ephemeral=True)
        return
    tasks_list = [t for t in data[user_id]["tasks"] if t["deleted"] is None]
    if not tasks_list:
        await interaction.response.send_message("You have no custom tasks to remove.", ephemeral=True)
        return

    # Immediately respond to the interaction so it doesn't expire.
    await interaction.response.send_message("Check your DMs for task removal instructions.", ephemeral=True)

    msg = "Your custom tasks:\n"
    for idx, task in enumerate(tasks_list, start=1):
        msg += f"{idx}. {task['description']} (Type: {task['type']})\n"
    msg += "Reply with the number of the task you want to remove."

    try:
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send(msg)

        def check(m):
            return m.author == interaction.user and m.channel == dm_channel

        response = await bot.wait_for('message', check=check, timeout=60)
        try:
            num = int(response.content.strip())
            if num < 1 or num > len(tasks_list):
                await dm_channel.send("Invalid number. Operation cancelled.")
                return
        except ValueError:
            await dm_channel.send("Invalid input. Operation cancelled.")
            return

        task_to_remove = tasks_list[num - 1]
        task_to_remove["deleted"] = datetime.utcnow().isoformat()
        save_data(data)
        await dm_channel.send(f"Task '{task_to_remove['description']}' removed.")
        await interaction.followup.send("Task removal processed. Check your DMs for confirmation.", ephemeral=True)
    except asyncio.TimeoutError:
        try:
            await interaction.followup.send("Task removal timed out.", ephemeral=True)
        except Exception as e:
            print(f"Error sending timeout message: {e}")


###############################################################################
# /complete Command: Mark a Task as Completed for Today
###############################################################################
@bot.tree.command(name="complete", description="Mark one or more tasks as completed for today.")
@app_commands.describe(task_numbers="Comma-separated list of task numbers from your checklist (e.g., '6,7,8')")
async def complete(interaction: discord.Interaction, task_numbers: str):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message("Not registered. Use /register first.", ephemeral=True)
        return

    today_str = datetime.utcnow().date().isoformat()
    personal_defaults = data[user_id].get("personal_defaults")
    if not personal_defaults:
        personal_defaults = [
            {"description": "Rise and shine - enjoy a refreshing glass of water!", "difficulty": 1},
            {"description": "Splash your face and greet the day with a smile.", "difficulty": 1},
            {"description": "Brush your teefs until they sparkle.", "difficulty": 1},
            {"description": "Hop in the shower if you're feeling a bit groggy.", "difficulty": 1},
            {"description": "Quickly brush your hair for a neat look.", "difficulty": 1},
            {"description": "Change into fresh undies and a comfy tee.", "difficulty": 1},
            {"description": "Fuel up with a healthy meal or snack.", "difficulty": 1},
            {"description": "Take a light walk or stretch to get moving.", "difficulty": 1},
            {"description": "Do something fun that makes your heart sing.", "difficulty": 1},
            {"description": "Check in with your mood and give yourself a high-five.", "difficulty": 1}
        ]
    default_tasks = [{"description": task["description"], "difficulty": task["difficulty"], "source": "default"} for task in personal_defaults]
    custom_tasks_raw = [t for t in data[user_id].get("tasks", []) if t["deleted"] is None]
    custom_tasks = [{"description": f"{t['description']} ({t['type'].capitalize()}, points: {t.get('difficulty', 2)})", "source": "custom", "ref": t} for t in custom_tasks_raw]
    checklist = default_tasks + custom_tasks

    if "daily_defaults" not in data[user_id] or data[user_id]["daily_defaults"].get("date") != today_str:
        data[user_id]["daily_defaults"] = {"date": today_str, "completed": []}

    try:
        numbers = [int(n.strip()) for n in task_numbers.split(",")]
    except ValueError:
        await interaction.response.send_message("Invalid format. Use a comma-separated list of numbers.", ephemeral=True)
        return

    total_points_awarded = 0
    messages = []
    for num in numbers:
        if num < 1 or num > len(checklist):
            messages.append(f"Task number {num} is invalid.")
            continue
        task = checklist[num - 1]
        if task.get("source") == "default":
            if task["description"] in data[user_id]["daily_defaults"]["completed"]:
                messages.append(f"Default task '{task['description']}' already completed.")
            else:
                data[user_id]["daily_defaults"]["completed"].append(task["description"])
                points_awarded = task["difficulty"]
                data[user_id]["points"] += points_awarded
                data[user_id]["weekly_points"] += points_awarded
                total_points_awarded += points_awarded
                messages.append(f"Marked default task '{task['description']}' as completed (+{points_awarded}).")
        else:
            ref = task.get("ref")
            if ref.get("is_completed"):
                messages.append(f"Custom task '{ref['description']}' already completed.")
            else:
                ref["is_completed"] = True
                points_awarded = ref.get("difficulty", 2)
                data[user_id]["points"] += points_awarded
                data[user_id]["weekly_points"] += points_awarded
                total_points_awarded += points_awarded
                messages.append(f"Marked custom task '{ref['description']}' as completed (+{points_awarded}).")
    save_data(data)
    messages.append(f"Total points awarded: {total_points_awarded}.")
    final_message = "\n".join(messages)
    await interaction.response.send_message(final_message, ephemeral=True)




###############################################################################
# /Buddy Command: Allows a user to register an accountability buddy
###############################################################################
@bot.tree.command(name="buddy", description="Request an accountability buddy with a unique code.")
async def buddy(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message("You are not registered. Use /register first.", ephemeral=True)
        return

    # Generate a unique 9-digit code in the format XXX-XXX-XXX.
    code_digits = [str(random.randint(0, 9)) for _ in range(9)]
    code = f"{''.join(code_digits[:3])}-{''.join(code_digits[3:6])}-{''.join(code_digits[6:9])}"
    
    # Store the pending buddy request with a 5-minute expiry.
    expiry_time = datetime.utcnow() + timedelta(minutes=5)
    buddy_requests[code] = {"inviter": user_id, "expires": expiry_time}
    
    # Inform the inviter (user 1) of the generated code.
    await interaction.response.send_message(
        f"Your buddy request code is **{code}**. Share this code with someone you trust. They have 5 minutes to DM me this code to become your accountability buddy.",
        ephemeral=True
    )
    
    # Define a check for incoming DM messages with the code.
    def code_check(message):
        return (
            message.content.strip() == code and
            str(message.author.id) != user_id and
            isinstance(message.channel, discord.DMChannel)
        )
    
    try:
        # Wait up to 5 minutes for another user (user 2) to DM the code.
        message = await bot.wait_for('message', check=code_check, timeout=300)
        buddy_user_id = str(message.author.id)
        
        # Attempt to fetch user 2.
        buddy_user = bot.get_user(int(buddy_user_id))
        if buddy_user is None:
            buddy_user = await bot.fetch_user(int(buddy_user_id))
        if buddy_user is None:
            raise Exception("Unable to fetch buddy user.")
            
        # DM user 2 with an explanation and request confirmation.
        buddy_dm = await buddy_user.create_dm()
        prompt_msg = (
            "You've received a buddy request code. By replying 'yes', you agree to be the accountability buddy for the requesting user. "
            "As an accountability buddy, if they don't complete any tasks in 7 days, you'll receive a reminder to check in on them. "
            "Reply 'yes' to accept or 'no' to decline."
        )
        await buddy_dm.send(prompt_msg)
        
        # Wait for user 2's confirmation.
        def confirm_check(m):
            return (
                m.author.id == int(buddy_user_id) and
                m.channel == buddy_dm and
                m.content.strip().lower() in ["yes", "no"]
            )
        confirmation = await bot.wait_for('message', check=confirm_check, timeout=120)
        response = confirmation.content.strip().lower()
        
        # Use interaction.user directly for the inviter.
        inviter_dm = await interaction.user.create_dm()
        
        if response == "yes":
            data[user_id]["accountability_buddy"] = buddy_user_id
            save_data(data)
            await buddy_dm.send("Thank you! You are now registered as an accountability buddy.")
            await inviter_dm.send(f"{buddy_user.name} has accepted your accountability buddy request!")
        else:
            await buddy_dm.send("You have declined the buddy request.")
            await inviter_dm.send(f"Unfortunately, {buddy_user.name} has declined to be your accountability buddy.")
        
        # Remove the pending request.
        if code in buddy_requests:
            del buddy_requests[code]
    except asyncio.TimeoutError:
        if code in buddy_requests:
            del buddy_requests[code]
        inviter_dm = await interaction.user.create_dm()
        await inviter_dm.send("Buddy request expired. No one responded in time.")
        await interaction.followup.send("Buddy request expired. No one joined as your accountability buddy.", ephemeral=True)




###############################################################################
# /Journal Command: Allows a user to complete a daily journal entry.
###############################################################################
@bot.tree.command(name="journal", description="Write a short journal entry on a given prompt or your own topic.")
async def journal(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    
    if user_id not in data:
        await interaction.response.send_message("You are not registered. Please use /register to get started.", ephemeral=True)
        return

    # Check if user has journaled today. We'll store the date as ISO date (YYYY-MM-DD).
    today_str = datetime.utcnow().date().isoformat()
    last_journal = data[user_id].get("last_journal", "")
    if last_journal == today_str:
        await interaction.response.send_message("You've already journaled today. Try again tomorrow!", ephemeral=True)
        return

    # Choose a random prompt and offer a "Your own" option.
    prompt = random.choice(JOURNAL_PROMPTS + ["Your own prompt"])
    
    # Inform the user that their entry is private and not stored.
    instructions = (
        f"**Journaling Prompt:** {prompt}\n\n"
        "If you'd like to respond to the prompt above, please check your DMs.\n"
        "Alternatively, if you choose 'Your own prompt', just write about a topic of your choice.\n\n"
        "Note: Your journal entry is private between you and the bot and is not stored anywhere."
    )
    await interaction.response.send_message(instructions, ephemeral=True)
    
    try:
        # Open DM channel and prompt for the journal entry.
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send(
            "Please write your journal entry. Remember, this is private and not stored anywhere.\n"
            "When you're done, just send your entry as a message here."
        )
        def check(m):
            return m.author == interaction.user and m.channel == dm_channel
        msg = await bot.wait_for('message', check=check, timeout=900)  # 15 minute timeout
        
        # Award 5 points for journaling.
        points_awarded = 5
        data[user_id]["points"] += points_awarded
        data[user_id]["weekly_points"] = data[user_id].get("weekly_points", 0) + points_awarded
        data[user_id]["last_journal"] = today_str
        save_data(data)
        
        await dm_channel.send(f"Thank you for journaling! You've been awarded {points_awarded} points for today.")
    except asyncio.TimeoutError:
        await dm_channel.send("Journal entry timed out. Please try again later when you have a moment.")


###############################################################################
# /deregister Command: Remove a User's Data Completely
###############################################################################
@bot.tree.command(name="deregister", description="Remove all your data from Selfcare Sidekick. This cannot be undone!")
async def deregister(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message("You are not registered.", ephemeral=True)
        return

    await interaction.response.send_message(
        "WARNING: This will permanently remove all your data. If you register again, you will start over with 0 points.\n"
        "Please confirm by replying with 'yes' in DM.", ephemeral=True
    )
    try:
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send("Please confirm that you want to deregister by replying with 'yes'.")
        def check(m):
            return m.author == interaction.user and m.channel == dm_channel
        response = await bot.wait_for('message', check=check, timeout=60)
        if response.content.strip().lower() == "yes":
            del data[user_id]
            save_data(data)
            await dm_channel.send("Your data has been permanently removed. We're sorry to see you go!")
            await interaction.followup.send("You have been deregistered.", ephemeral=True)
        else:
            await dm_channel.send("Deregistration cancelled.")
            await interaction.followup.send("Deregistration cancelled.", ephemeral=True)
    except asyncio.TimeoutError:
        await interaction.response.send_message("Deregistration timed out.", ephemeral=True)
        
###############################################################################
# Crisis Function: Provides user with mental health and suicide prevention resources
###############################################################################
@bot.tree.command(name="crisis", description="Get crisis support resources if you're feeling unsafe or overwhelmed.")
async def crisis(interaction: discord.Interaction):
    message = (
        "**If you're in crisis or feeling suicidal, please know that help is available.**\n\n"
        "Please consider reaching out to someone you trust or a mental health professional immediately. "
        "If you're in immediate danger, call your local emergency services (for example, 911 in the US).\n\n"
        "**Crisis Resources:**\n"
        "- **United States:** National Suicide Prevention Lifeline: 988 or 1-800-273-8255\n"
        "- **Crisis Text Line (US & Canada):** Text HOME to 741741\n"
        "- **United Kingdom:** Samaritans: 116 123\n"
        "- **Australia:** Lifeline Australia: 13 11 14\n"
        "- **International:** Visit [Find a Helpline](https://findahelpline.com/) to locate resources in your country.\n\n"
        "Remember: You deserve support, and there are people ready to help you through this. Please consider talking to someone right away."
    )
    await interaction.response.send_message(message, ephemeral=True)


###############################################################################
# Points Report: Allows users to check total and weekly points.
###############################################################################
@bot.tree.command(name="points", description="Check your total and weekly points.")
async def points(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message("You are not registered. Please use /register to get started.", ephemeral=True)
        return

    total = data[user_id].get("points", 0)
    weekly = data[user_id].get("weekly_points", 0)
    message = (
        "Your points:\n"
        f"- Total Points: **{total}**\n"
        f"- Weekly Points: **{weekly}**"
    )
    await interaction.response.send_message(message, ephemeral=True)
    
###############################################################################
# Pause/Unpause Functions: Allows users to take a break from the reminders.
###############################################################################
@bot.tree.command(name="pause", description="Pause daily reminders.")
async def pause(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message("You are not registered. Use /register first.", ephemeral=True)
        return
    data[user_id]["paused"] = True
    save_data(data)
    await interaction.response.send_message("Your reminders have been paused.", ephemeral=True)

@bot.tree.command(name="unpause", description="Resume daily reminders.")
async def unpause(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data:
        await interaction.response.send_message("You are not registered. Use /register first.", ephemeral=True)
        return
    data[user_id]["paused"] = False
    save_data(data)
    await interaction.response.send_message("Your reminders have been resumed.", ephemeral=True)

###############################################################################
# Settimezone - allows users to set timezone to get reminders in their local time.
###############################################################################
@bot.tree.command(name="settimezone", description="Set your local time zone.")
@app_commands.describe(timezone="Select your local time zone from the list.")
@app_commands.choices(timezone=[
    app_commands.Choice(name="Eastern Time (US)", value="America/New_York"),
    app_commands.Choice(name="Central Time (US)", value="America/Chicago"),
    app_commands.Choice(name="Mountain Time (US)", value="America/Denver"),
    app_commands.Choice(name="Pacific Time (US)", value="America/Los_Angeles"),
    app_commands.Choice(name="Greenwich Mean Time", value="Etc/Greenwich"),
    app_commands.Choice(name="London", value="Europe/London"),
    app_commands.Choice(name="Paris", value="Europe/Paris"),
    app_commands.Choice(name="Tokyo", value="Asia/Tokyo")
])
async def settimezone(interaction: discord.Interaction, timezone: app_commands.Choice[str]):
    data = load_data()
    user_id = str(interaction.user.id)
    if user_id not in data:
        await interaction.response.send_message("You are not registered. Use /register first.", ephemeral=True)
        return
    data[user_id]["timezone"] = timezone.value
    save_data(data)
    await interaction.response.send_message(f"Your time zone has been set to {timezone.name} ({timezone.value}).", ephemeral=True)


###############################################################################
# Nightly Summary: DM Each Registered User Their Daily Task Summary at Night
###############################################################################
@tasks.loop(seconds=60)
async def nightly_summary():
    await bot.wait_until_ready()
    data = load_data()
    now_utc = datetime.utcnow()
    for user_id, user_info in data.items():
        if user_info.get("paused"):
            print(f"User {user_id} is paused; skipping nightly summary DM.")
            continue
        tz_str = user_info.get("timezone")
        if not tz_str:
            # User hasn't set a timezone; skip sending localized messages.
            continue
        try:
            tz = pytz.timezone(tz_str)
        except Exception as e:
            print(f"Invalid timezone for user {user_id}: {tz_str}")
            continue
        now_local = datetime.now(tz)
        # If it is exactly 23:00 (11 PM) local time, send the summary.
        if now_local.hour == 23 and now_local.minute == 0:
            try:
                user = bot.get_user(int(user_id))
                if user is None:
                    user = await bot.fetch_user(int(user_id))
                dm_channel = await user.create_dm()
            except Exception as e:
                print(f"Error fetching DM channel for user {user_id}: {e}")
                continue

            # (Use your existing formatting code for the summary message)
            today_str = datetime.utcnow().date().isoformat()
            # Format personal defaults.
            personal_defaults = user_info.get("personal_defaults", [])
            if personal_defaults and isinstance(personal_defaults[0], dict):
                formatted_defaults = [f"{task['description']} (points: {task['difficulty']})" for task in personal_defaults]
            else:
                formatted_defaults = personal_defaults

            # Retrieve completed default tasks.
            completed_defaults = []
            if "daily_defaults" in user_info and user_info["daily_defaults"].get("date") == today_str:
                completed_defaults = user_info["daily_defaults"].get("completed", [])

            # Format custom tasks.
            custom_tasks_raw = [t for t in user_info.get("tasks", []) if t["deleted"] is None]
            custom_tasks = [f"{t['description']} ({t['type'].capitalize()}, points: {t.get('difficulty', 2)})" for t in custom_tasks_raw]
            # Completed custom tasks.
            completed_custom = [f"{t['description']} ({t['type'].capitalize()}, points: {t.get('difficulty', 2)})" for t in custom_tasks_raw if t.get("is_completed")]

            # Combine tasks.
            all_tasks = formatted_defaults + custom_tasks
            completed = completed_defaults + completed_custom

            # For strike-through, we compare base descriptions.
            def extract_description(task_str):
                return task_str.split(" (")[0].strip()

            completed_descriptions = {extract_description(task) for task in completed}
            not_completed = [task for task in all_tasks if extract_description(task) not in completed_descriptions]

            # Calculate today's points.
            daily_points = 0
            if personal_defaults and isinstance(personal_defaults[0], dict):
                for task in personal_defaults:
                    if task["description"] in completed_defaults:
                        daily_points += task.get("difficulty", 1)
            else:
                daily_points += len(completed_defaults)
            for t in custom_tasks_raw:
                if t.get("is_completed"):
                    daily_points += t.get("difficulty", 2)

            summary = "Here is your nightly summary:\n\n"
            summary += "**Completed Tasks:**\n"
            summary += "\n".join(f"- {task}" for task in completed) if completed else "None\n"
            summary += "\n\n**Uncompleted Tasks:**\n"
            summary += "\n".join(f"- {task}" for task in not_completed) if not_completed else "None\n"
            summary += f"\n\nTotal Points for Today: {daily_points}\n"

            print(f"Attempting to send nightly DM to {user_info['name']} (ID: {user_id})")
            try:
                await dm_channel.send(summary)
                print(f"Nightly summary DM sent to {user_info['name']}")
            except Exception as e:
                print(f"Error sending DM to user {user_id}: {e}")


###############################################################################
# Morning Reminder: DM Each Registered User at 8am with Today's Tasks
###############################################################################
@tasks.loop(seconds=60)
async def morning_reminder():
    await bot.wait_until_ready()
    data = load_data()
    now_utc = datetime.utcnow()
    for user_id, user_info in data.items():
        # Skip if user is paused or no timezone is set.
        if user_info.get("paused"):
            print(f"User {user_id} is paused; skipping DM.")
            continue
        tz_str = user_info.get("timezone")
        if not tz_str:
            # If the user hasn't set a time zone, skip them.
            continue
        try:
            tz = pytz.timezone(tz_str)
        except Exception as e:
            print(f"Invalid timezone for user {user_id}: {tz_str}")
            continue

        # Get the current local time for the user.
        now_local = datetime.now(tz)
        # For testing, you might check for a specific minute; here, we send at 8:00 AM local time.
        if now_local.hour == 8 and now_local.minute == 0:
            try:
                user = bot.get_user(int(user_id))
                if user is None:
                    user = await bot.fetch_user(int(user_id))
                dm_channel = await user.create_dm()
            except Exception as e:
                print(f"Error fetching DM channel for user {user_id}: {e}")
                continue

            # Format the message as before.
            personal_defaults = user_info.get("personal_defaults", [])
            if personal_defaults and isinstance(personal_defaults[0], dict):
                formatted_defaults = [f"{task['description']} (points: {task['difficulty']})" for task in personal_defaults]
            else:
                formatted_defaults = personal_defaults

            daily_custom = [
                f"{t['description']} (points: {t.get('difficulty', 2)})"
                for t in user_info.get("tasks", [])
                if t["deleted"] is None and t["type"] == "daily"
            ]
            weekly_custom = [
                f"{t['description']} (points: {t.get('difficulty', 2)})"
                for t in user_info.get("tasks", [])
                if t["deleted"] is None and t["type"] == "weekly"
            ]
            message = f"Good morning {user_info['name']}!\n\nHere are your tasks for today:\n\n**Daily Tasks:**\n"
            for idx, task in enumerate(formatted_defaults, start=1):
                message += f"{idx}. {task}\n"
            if daily_custom:
                message += "\n**Your Custom Daily Tasks:**\n"
                for idx, task in enumerate(daily_custom, start=1):
                    message += f"{idx}. {task}\n"
            if weekly_custom:
                message += "\n**Your Weekly Tasks:**\n"
                for idx, task in enumerate(weekly_custom, start=1):
                    message += f"{idx}. {task}\n"
            print(f"Attempting to send DM to {user_info['name']} (ID: {user_id})")
            try:
                await dm_channel.send(message)
                print(f"DM sent to {user_info['name']}")
            except Exception as e:
                print(f"Error sending DM to user {user_id}: {e}")

###############################################################################
# Weekly Summary: DM Each Registered User on Friday at 5pm with Their Weekly Points
###############################################################################
@tasks.loop(seconds=60)
async def weekly_summary():
    await bot.wait_until_ready()
    data = load_data()
    for user_id, user_info in data.items():
        if user_info.get("paused"):
            print(f"User {user_id} is paused; skipping weekly summary DM.")
            continue
        tz_str = user_info.get("timezone")
        if not tz_str:
            continue
        try:
            tz = pytz.timezone(tz_str)
        except Exception as e:
            print(f"Invalid timezone for user {user_id}: {tz_str}")
            continue
        now_local = datetime.now(tz)
        # Check if it is Friday at 17:00 (5 PM) local time.
        if now_local.weekday() == 4 and now_local.hour == 17 and now_local.minute == 0:
            try:
                user = bot.get_user(int(user_id))
                if user is None:
                    user = await bot.fetch_user(int(user_id))
                dm_channel = await user.create_dm()
            except Exception as e:
                print(f"Error fetching DM channel for user {user_id}: {e}")
                continue

            personal_defaults = user_info.get("personal_defaults", [])
            if personal_defaults and isinstance(personal_defaults[0], dict):
                formatted_defaults = [f"{task['description']} (points: {task['difficulty']})" for task in personal_defaults]
            else:
                formatted_defaults = personal_defaults

            custom_tasks_raw = [t for t in user_info.get("tasks", []) if t["deleted"] is None]
            formatted_custom = [
                f"{t['description']} ({t['type'].capitalize()}, points: {t.get('difficulty', 2)})"
                for t in custom_tasks_raw
            ]
            tasks_list = formatted_defaults + formatted_custom
            total_points = user_info.get("points", 0)
            weekly_points = user_info.get("weekly_points", 0)

            message = (
                f"Happy Friday, {user_info['name']}!\n\n"
                f"This week, you've earned **{weekly_points}** points.\n"
                f"Your total points so far are **{total_points}**.\n\n"
                "Here are your current tasks:\n"
            )
            if tasks_list:
                for idx, task in enumerate(tasks_list, start=1):
                    message += f"{idx}. {task}\n"
            else:
                message += "No tasks found.\n"
            message += "\nKeep up the great work!"

            try:
                await dm_channel.send(message)
                print(f"Weekly summary DM sent to {user_info['name']} (ID: {user_id})")
            except Exception as e:
                print(f"Failed to send weekly summary DM to {user_id}: {e}")
            
            # Reset weekly points.
            user_info["weekly_points"] = 0
    save_data(data)
    
###############################################################################
# Reset Custom Task Completion for Daily Tasks (runs at midnight)
###############################################################################
@tasks.loop(time=time(hour=0, minute=0))
async def reset_daily_custom_tasks():
    await bot.wait_until_ready()
    data = load_data()
    changed = False
    # Reset custom daily tasks
    for user_id, user_info in data.items():
        for task in user_info.get("tasks", []):
            if task["deleted"] is None and task["type"] == "daily" and task.get("is_completed"):
                task["is_completed"] = False
                changed = True
        # Reset default task completions stored in "daily_defaults"
        if "daily_defaults" in user_info:
            # Always update the date and empty the list for the new day.
            user_info["daily_defaults"] = {"date": datetime.utcnow().date().isoformat(), "completed": []}
            changed = True
    if changed:
        save_data(data)


###############################################################################
# Reset Custom Task Completion for Weekly Tasks (runs on Friday at midnight)
###############################################################################
@tasks.loop(time=time(hour=0, minute=0))
async def reset_weekly_custom_tasks():
    await bot.wait_until_ready()
    # Check if today is Friday (weekday() returns 4 for Friday)
    if datetime.utcnow().weekday() == 4:
        data = load_data()
        changed = False
        for user_id, user_info in data.items():
            for task in user_info["tasks"]:
                if task["deleted"] is None and task["type"] == "weekly" and task.get("is_completed"):
                    task["is_completed"] = False
                    changed = True
        if changed:
            save_data(data)

###############################################################################
# Bot Ready and Command Sync
###############################################################################
# (Remember to start these loops in your on_ready handler.)
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(e)
    if not nightly_summary.is_running() :
        nightly_summary.start()
    if not morning_reminder.is_running():
        morning_reminder.start()
    if not weekly_summary.is_running() :
        weekly_summary.start()
    if not reset_daily_custom_tasks.is_running():
        reset_daily_custom_tasks.start()
    if not reset_weekly_custom_tasks.is_running() :
        reset_weekly_custom_tasks.start()


###############################################################################
# Run the Bot
###############################################################################
bot.run(config["TOKEN"])
