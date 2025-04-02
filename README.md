# Selfcare-Sidekick
Selfcare Sidekick is a gamified self-care and mental health assistant bot for Discord. It helps you build and maintain healthy daily routines through personalized task lists, journaling prompts, accountability buddy pairing, crisis support, and more—all while awarding points for completing tasks!

## Features

* Registration & Personalization:
    Register using /register to set your preferred name, select your local time zone via a dropdown, and choose 10 default self-care tasks from a list of suggestions. Your data (including your selected tasks and time zone) is stored for personalized reminders.

* Task Management:

  * /list: View your daily tasks, with completed tasks struck through and points awarded displayed.

  * /complete: Mark one or more tasks as completed (accepts a comma-separated list of task numbers) and earn points based on each task’s difficulty (shown as "points").

  * /add: Add custom tasks (daily or weekly) with an optional points value.

  * /remove: Remove custom tasks (soft delete).

* Journaling:
Use /journal to receive a random journaling prompt (or write about your own topic) and earn 5 points for a daily entry. Your entries remain private and are not stored.

* Accountability Buddy:
Use `/buddy` to generate a unique code to invite an accountability buddy. If another user sends the code and accepts the request, they become your buddy. If you don’t complete tasks in 7 days, your buddy receives a reminder to check in on you.

* Crisis Support:
In moments of need, use `/crisis` to access emergency mental health and suicide prevention resources.

* Points Tracking:
Earn points for completing tasks (default tasks typically award 1 point; custom tasks award 2 points by default, though you can set these). Check your total and weekly points with `/points`.

* Reminders & Summaries:
Scheduled tasks send you:

  * A morning reminder at 8:00 AM (local time) with your daily tasks.

  * A nightly summary at 11:00 PM (local time) reviewing completed and pending tasks and points earned.

  * A weekly summary on Friday at 5:00 PM (local time) with your weekly points, then resets weekly points.

  * Automatic resets for task completions at midnight (daily and weekly).

* Pause/Unpause Reminders:
Use `/pause` and `/unpause` to temporarily stop and resume receiving reminders.

## Installation
### Prerequisites

    Python 3.9+ (Python 3.10 or later is recommended)

    A Discord bot token. Create one on the Discord Developer Portal.

### Dependencies

Install the required Python libraries using pip:

`pip install discord.py pytz aiodns' 

Note: This project uses discord.py v2.0+ for slash commands and UI components.

### Setup

1. Clone the Repository:
```
git clone https://github.com/yourusername/selfcare-sidekick.git
cd selfcare-sidekick
```
2. Create a Configuration File:

Create a `config.json` file in the project root with the following content:
```
{
  "TOKEN": "YOUR_DISCORD_BOT_TOKEN"
}
```
3. User Data File:

The bot stores user data in `users.json`. This file will be created automatically when users register.

4. Run the Bot:

Start the bot with:

    python "Selfcare Sidekick.py"

## Commands
### Slash Commands

    /register
    Registers a new user. You’ll be prompted (via DM) to provide your name, select your local time zone from a dropdown, and choose your initial self-care tasks.

    /settimezone
    (Optional) Change your time zone later if needed.

    /list
    View your daily task list. Completed tasks are displayed with a strikethrough and the points earned.

    /complete
    Mark one or more tasks as completed by providing a comma-separated list of task numbers. Points are awarded based on each task’s set value.

    /add
    Add a custom task (daily or weekly). You can optionally specify a points value (defaults are 1 for daily and 2 for weekly).

    /remove
    Remove (soft-delete) a custom task via a numbered list.

    /buddy
    Generate a unique code to request an accountability buddy. Another user can DM the code to accept (or decline) the request.

    /journal
    Write a daily journal entry prompted by a random question, or write on your own. Earn 5 points for journaling once per day.

    /deregister
    Permanently remove your data from the bot.

    /crisis
    Receive crisis support resources and hotline information if you're in need.

    /points
    Check your total and weekly points.

    /pause and /unpause
    Temporarily pause or resume your reminders.

### Scheduled Tasks

    Morning Reminder:
    Sent at 8:00 AM local time to remind you of your daily tasks.

    Nightly Summary:
    Sent at 11:00 PM local time to summarize your task completion and points for the day.

    Weekly Summary:
    Sent on Friday at 5:00 PM local time to report weekly points and reset the weekly counter.

    Task Resets:
    Automated resets for daily and weekly task completions occur at midnight.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

    Author: Matthew St. Jean
    Consultant: Colin Dixon – contributed ideas and solutions for design and problem-solving.
