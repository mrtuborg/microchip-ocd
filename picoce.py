#!/usr/bin/env python3
import argparse
import atexit
import logging
import os
import signal
import sys
import platform
import subprocess
from logging.handlers import RotatingFileHandler
from picoce_lock import cleanup, signal_handler, acquire_lock

# Function Declarations
def setup_logging():
    logger = logging.getLogger('picoceLogger')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=1)
    logger.addHandler(handler)
    return logger

def parse_arguments():
    parser = argparse.ArgumentParser(description='Upload files and manage Docker containers for MPLAB tools.')
    parser.add_argument('tool', choices=['ipe', 'mdb', 'shell'], help='The tool to use')
    parser.add_argument('file', nargs='?', help='The binary file to upload')
    parser.add_argument('--lock_duration', type=int, default=0, help='Lock duration in seconds')
    parser.add_argument('--image-name', default='mplabx-container', help='Docker container name')
    parser.add_argument('--image-tag', default='v6.20.1', help='Docker image tag to use')
    return parser.parse_args()

def form_exec_command_arguments(args_tool, args, programmer_id, workspace):
    if args_tool == 'shell':
        exec_command = "/bin/bash"
        arguments_line = args.file  # Assuming args.file is directly passed for shell

    elif args_tool == 'ipe':
        hex_file = args.file
        exec_command = "/opt/microchip/mplabx/v6.20/mplab_platform/mplab_ipe/ipecmd.sh"
        arguments_line = f"-P32MK1024GPK064 -TP{programmer_id} -F{hex_file} -M -OL"

    elif args_tool == 'mdb':
        exec_command = "/opt/microchip/mplabx/v6.20/mplab_platform/bin/mdb.sh"
        if args.file == "empty":
            arguments_line = ""
        elif args.file == "help":
            print('mdb <scriptFile> <elf-file-to-debug>')
            exit()
        else:
            script, elf = args.file.split()[:2]  # Assuming args.file contains both script and elf separated by space
            script_tmp = f"{script}.tmp"
            with open(script_tmp, 'w') as tmp_file:
                with open(script, 'r') as original_script:
                    tmp_file.write(original_script.read())
                tmp_file.write(f'Program "{workspace}/{elf}"\n')
            print(f"exec: mdb {script} {elf}")
            with open(script_tmp, 'r') as tmp_file:
                print(tmp_file.read())
            arguments_line = script_tmp

    return exec_command, arguments_line

def check_docker_daemon(retry_count=3, retry_delay=5, logger=None):
    docker_command = {
        "Windows": ["docker", "info"],
        "Linux": ["systemctl", "is-active", "--quiet", "docker"],
        "Darwin": ["docker", "info"]  # macOS uses the same command as Windows
    }

    system_type = platform.system()
    if system_type not in docker_command:
        logger.error(f"Unsupported operating system: {system_type}")
        return False

    command = docker_command[system_type]

    for _ in range(retry_count):
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            time.sleep(retry_delay)

    logger.error("Docker daemon is not running after retries.")
    return False

def run_docker(image_name, exec_command, arguments, logger=None):
    check_docker_daemon(logger=logger)  # Ensure Docker daemon is running

    # Ensure arguments is a list
    if isinstance(arguments, str):
        arguments = [arguments]

    docker_command = ["docker", "run", "--privileged", "--device=/dev/bus/usb", "-v", f"{os.getcwd()}:/workspace", "-w", "/workspace", image_name, exec_command] + arguments
    try:
        subprocess.run(docker_command, check=True)
        logger.info("Docker command executed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run docker command: {e}")
        sys.exit(1)

# Global variables and paths
HOME_DIR = os.getenv("HOME")
LOCK_FILE = os.path.join(HOME_DIR, ".picoce.lock")
LOG_FILE = os.path.join(HOME_DIR, ".picoce.log")
PROGRAMMER_ID = "ICD4"
WORKSPACE_DIR = "/workspace"

# Main Entry Point
if __name__ == "__main__":
    args = parse_arguments()
    logger = setup_logging()

    # Adjust signal handler and atexit to use the new module's functions
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, LOCK_FILE, logger))
    signal.signal(signal.SIGTERM, lambda sig, frame: signal_handler(sig, frame, LOCK_FILE, logger))
    atexit.register(lambda: cleanup(LOCK_FILE, logger))

    if not acquire_lock(LOCK_FILE, args.lock_duration, logger):
        logger.error("Another instance is already running or the lock is still valid.")
        sys.exit(1)

    image_name = f"{args.image_name}:{args.image_tag}"
    exec_command, arguments_line = form_exec_command_arguments(args.tool, args, PROGRAMMER_ID, WORKSPACE_DIR)
    logger.info(f"exec: {exec_command} {arguments_line}")
    run_docker(image_name, exec_command, arguments_line, logger)