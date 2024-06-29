#!/usr/bin/env python3
import time
import argparse
import logging
import os
import signal
import sys
import platform
import subprocess

from logging.handlers import RotatingFileHandler
from picoce_lock import signal_handler, acquire_lock
from hwtools_scan import hwscan

# Function Declarations
def setup_logging(verbose):
    logger = logging.getLogger('picoceLogger')
    if not logger.handlers:  # Check if handlers are already added
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=1)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(formatter)
        logger.addHandler(consoleHandler)
    return logger

def parse_arguments():
    parser = argparse.ArgumentParser(description='Upload files and manage Docker containers for MPLAB tools.')
    parser.add_argument('tool', choices=['ipe', 'mdb', 'shell', 'scan'], help='The tool to use')
    parser.add_argument('file', nargs='?', help='The binary file to upload')
    parser.add_argument('--lock_duration', type=int, default=0, help='Lock duration in seconds')
    parser.add_argument('--hwtool_type', type=str, help='Programmer ID, i.e. ICD4')
    parser.add_argument('--hwtool_sn', type=str, help='Programmer serial number, i.e. BUR202672399')
    parser.add_argument('--target', type=str, default='PIC32MK1024GPK064', help='Target device, i.e. PIC32MK1024GPK064')
    parser.add_argument('--image-name', default='registry.gitlab.com/biosort-as/eels/infrastructure/docker/mplabx-container', help='Docker container name')
    parser.add_argument('--image-tag', default='v6.20.2', help='Docker image tag to use')
    parser.add_argument('-v', '--verbose', action='store_true', help='Increase output verbosity')
    return parser.parse_args()

def form_exec_command_arguments(args_tool, args, workspace):
    if args_tool == 'shell':
        exec_command = "/bin/bash"
        arguments_line = ""

    elif args_tool == 'ipe':
        hex_file = args.file
        exec_command = "/opt/microchip/mplabx/v6.20/mplab_platform/mplab_ipe/ipecmd.sh"
        # -TP{args.hwtool_type} - have own naming, that differs from mdb.sh output, so will use only serial number
        arguments_line = f"-P32MK1024GPK064 -TS{args.hwtool_sn} -F{hex_file} -M -OL"

    elif args_tool == 'mdb':
        exec_command = "/opt/microchip/mplabx/v6.20/mplab_platform/bin/mdb.sh"
        if args.file == "empty":
            arguments_line = ""
        elif args.file == "help":
            print('mdb <scriptFile> <elf-file-to-debug>')
            exit()
        else:
            script_tmp = f"mdb_conf.tmp"
            with open(script_tmp, 'w') as tmp_file:
                tmp_file.write(f'Device {args.target}\n')
                tmp_file.write(f'Hwtool {args.hwtool_type} <sn>{args.hwtool_sn}\n')
                tmp_file.write(f'Program "{workspace}/{args.file}"\n')
            logger.debug(f"exec: mdb {script_tmp} {args.file}")
            with open(script_tmp, 'r') as tmp_file:
                logger.debug(tmp_file.read())
            arguments_line = script_tmp

    elif args_tool == 'scan':
        exec_command = "/opt/microchip/mplabx/v6.20/mplab_platform/bin/mdb.sh"
        arguments_line = "/workspace/mdb_scan.conf"

    logger.debug('tool:' + args_tool)
    logger.debug('exec_command:' + exec_command)
    logger.debug('arguments_line:' + arguments_line)
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

def run_docker(image_name, tool, exec_command, arguments, logger=None):
    check_docker_daemon(logger=logger)  # Ensure Docker daemon is running

    logger.debug(f"exec: {exec_command} {arguments_line}")

    # Ensure arguments is a list
    #if isinstance(arguments, str):
    #    arguments = [arguments]
    if args.tool == 'shell':
        interactive_args = "-it"
    else:
        interactive_args = ""

    logger.debug('interactive_args:' + interactive_args)
    docker_command = ["docker", "run", "--privileged", "--device=/dev/bus/usb", "-v", f"{os.getcwd()}:/workspace", "-w", "/workspace", image_name, exec_command, arguments, "2>/dev/null"]
    try:
        if tool == 'scan':
            result = subprocess.run(docker_command, check=True, capture_output=True, text=True)
            hwscan(result.stdout)
        else:
            subprocess.run(docker_command, check=True)

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run docker command: {e}")
        sys.exit(1)

# Global variables and paths
WORKSPACE_DIR = "/workspace"

# Main Entry Point
if __name__ == "__main__":
    args = parse_arguments()

    # Construct LOCK_FILE here using args.hwtool_sn
    LOCK_FILE = os.path.join("/var/lock/", f"picoce_{args.hwtool_sn}.lock")
    LOG_FILE = os.path.join("./", f"picoce.log")
    logger = setup_logging(args.verbose)

    # Adjust signal handler and atexit to use the new module's functions
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, LOCK_FILE, logger))
    signal.signal(signal.SIGTERM, lambda sig, frame: signal_handler(sig, frame, LOCK_FILE, logger))
    ## atexit.register(lambda: cleanup(LOCK_FILE, logger))

    # Lock should contain following information: lock_duration, hwtool_type, hwtool_sn. Lock_duration is optional.
    if not acquire_lock(LOCK_FILE, args.lock_duration, logger):
        logger.error("Another instance is already running or the lock is still valid.")
        sys.exit(1)

    image_name = f"{args.image_name}:{args.image_tag}"
    exec_command, arguments_line = form_exec_command_arguments(args.tool, args, WORKSPACE_DIR)
    logger.debug(f"exec: {exec_command} {arguments_line}")
    run_docker(image_name, args.tool, exec_command, arguments_line, logger)



