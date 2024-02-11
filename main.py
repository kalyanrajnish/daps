import json
import sys
import os
from util.config import Config
from util.scheduler import check_schedule
from util.logger import setup_logger
from util.utility import *
from prettytable import PrettyTable
import importlib
import multiprocessing
import time
import datetime

# Set the script name
script_name = "main"
# Set the current time
current_time = datetime.datetime.now().strftime("%H:%M")

already_run = {}

list_of_python_scripts = [
    "border_replacerr",
    "health_checkarr",
    "labelarr",
    "nohl",
    "poster_cleanarr",
    "poster_renamerr",
    "queinatorr",
    "renameinatorr",
    "sync_gdrive",
    "upgradinatorr",
    "unmatched_assets",
]

list_of_bash_scripts = [
    "backup_folder",
    "backup_appdata",
    "backup_plex",
    "jduparr",
    "nohl_bash",
]

branch = get_current_git_branch()

def run_module(script_name, logger):
    if script_name in list_of_python_scripts:
        try:
            module = importlib.import_module(f"modules.{script_name}")
            process = multiprocessing.Process(target=module.main)
            if process:
                process.start()
            return process
        except ModuleNotFoundError:
            logger.error(f"Script: {script_name} does not exist")
            return
    elif script_name and any(script in script_name for script in list_of_bash_scripts):
        module = "bash_scripts"
        try:
            module = importlib.import_module(f"modules.{module}")
            process = multiprocessing.Process(target=module.main, args=(script_name,))
            if process:
                process.start()
            return process
        except ModuleNotFoundError:
            logger.error(f"Script: {script_name} does not exist!")
            return
    else:
        logger.error(f"Script: {script_name} does not exist")
        return

def load_config(logger):
    """
    Load the config file

    Args:
        logger (obj): The logger object

    Returns:
        config (obj): The config object
        schedule (dict): The schedule dictionary
        logger (obj): The logger object
    """

    # Load the config file
    config = Config(script_name)

    # Get log level from config
    log_level = config.log_level

    # Setup the logger
    logger = setup_logger(log_level, script_name)

    # Get the schedule from the config
    schedule = config.scheduler

    return config, schedule, logger


def main():
    """
    Main function
    """
    logger = None
    try:
        config, scripts_schedules, logger = load_config(logger)
        if len(sys.argv) > 1:
            initial_run = None
            for input_name in sys.argv[1:]:
                if input_name and any(script in input_name for script in list_of_bash_scripts):
                    run_module(input_name, logger)
                elif input_name in list_of_python_scripts:
                    run_module(input_name, logger)
                elif input_name not in list_of_python_scripts or (input_name and not any(script in input_name for script in list_of_bash_scripts)):
                    logger.error(f"Script: {input_name} does not exist")
        else:
            # If config file is not found
            last_check = None
            initial_run = True
            old_schedule = None
            running_scripts = {}
            waiting_message_shown = False
            while True:
                config, scripts_schedules, logger = load_config(logger)
                
                # Check for new version
                if last_check is None or last_check.date() < datetime.datetime.now().date():
                    logger.debug("Checking for new version...")
                    from util.version import version_check
                    version_check(logger, branch)
                    last_check = datetime.datetime.now()
                    next_check = (last_check + datetime.timedelta(days=1)).strftime("%A %I:%M %p")
                    logger.info(f"Next version check: {next_check}")
                # Print the start message on the first run
                if initial_run or old_schedule != scripts_schedules:
                    if initial_run:
                        logger.info(create_bar("START"))

                    # Print the schedule
                    logger.info(create_bar("SCHEDULE"))
                    table = PrettyTable(["Script", "Schedule"])
                    table.align = "l"
                    table.padding_width = 1
                    for script_name, schedule_time in scripts_schedules.items():
                        if isinstance(schedule_time, dict):
                            for instance, schedule_time in schedule_time.items():
                                table.add_row([instance, schedule_time])
                        else:
                            table.add_row([script_name, schedule_time])
                    logger.info(f"{table}")
                    logger.info(create_bar("SCHEDULE"))
                    initial_run = False
                    waiting_message_shown = False

                if not waiting_message_shown:
                    logger.info("Waiting for scheduled scripts...")
                    waiting_message_shown = True

                
                # Check for scheduled scripts
                for script_name, schedule_time in scripts_schedules.items():
                    if isinstance(schedule_time, dict):
                        for instance, instance_schedule_time in schedule_time.items():
                            script_name = instance
                            schedule_time = instance_schedule_time
                            
                            if script_name in running_scripts or not schedule_time:
                                continue

                            if (script_name in list_of_python_scripts or any(script in script_name for script in list_of_bash_scripts)) and check_schedule(schedule_time):
                                process = run_module(script_name, logger)
                                running_scripts[script_name] = process
                    else:
                        if script_name in running_scripts or not schedule_time:
                            continue

                        if (script_name in list_of_python_scripts or any(script in script_name for script in list_of_bash_scripts)) and check_schedule(schedule_time):
                            process = run_module(script_name, logger)
                            running_scripts[script_name] = process

                # Remove the from running_scripts if the process is done
                processes_to_remove = []
                for script_name, process in running_scripts.items():
                    if not process.is_alive():
                        processes_to_remove.append(script_name)

                for script_name in processes_to_remove:
                    if script_name in processes_to_remove:
                        logger.info(f"Script: {script_name.capitalize()} has finished")
                        del running_scripts[script_name]
                        waiting_message_shown = False

                old_schedule = scripts_schedules
                time.sleep(15)
        
    # If the script is interrupted
    except KeyboardInterrupt:
        print("Keyboard Interrupt detected. Exiting...")
        sys.exit()
    
    # If an error occurs
    except Exception:
        logger.error(f"\n\nAn error occurred:\n", exc_info=True)
        logger.error(f"\n\n")

    # If the script is stopped
    finally:
        if initial_run is not None:
            logger.info(create_bar("END"))


if __name__ == '__main__':
    """
    Main function
    """
    main()
