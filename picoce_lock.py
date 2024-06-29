import json
import logging
import os
import time
import fcntl
import sys

# Assuming logger is set up in this module or passed as an argument to functions that need it
global_logger = logging.getLogger('picoce_lock')

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

def get_logger(logger=None):
    return logger if logger else global_logger

def cleanup(lock_file, logger=None):
    logger = get_logger(logger)
    try:
        with open(lock_file, 'r+') as f:
            os.remove(lock_file)
            logger.debug("Lock file removed successfully.")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def signal_handler(sig, lock_file, logger=None):
    logger = get_logger(logger)
    logger.debug(f"Signal {sig} received, cleaning up...")
    cleanup(lock_file)
    sys.exit(0)

def acquire_lock(lock_file, duration_s=0, logger=None):
    logger = get_logger(logger)
    logger.debug(f"Acquiring lock file: {lock_file}")
    # Check if the lock file exists, create if not
    if not os.path.exists(lock_file):
        try:
            with open(lock_file, 'w') as f:
                json.dump({}, f)  # Create an empty lock file
            logger.debug("Lock file created.")
            unlocked = True
        except IOError as e:
            logger.error(f"Failed to create lock file: {e}")
            return False
    else:
        unlocked = check_lock(lock_file, logger=logger)

    # Proceed with the existing logic
    if unlocked:
        try:
            # Calculate expiration timestamp by adding duration to the current time
            expiration_timestamp = int(time.time()) + int(duration_s)
            with open(lock_file, 'w') as f:
                json.dump({"expiration": expiration_timestamp}, f)
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            logger.debug("New lock acquired successfully.")
            return True
        except IOError as e:
            logger.error(f"Failed to acquire new lock: {e}")
            return False
    else:
        logger.debug("Existing lock is still valid; new lock not acquired.")
        return False

def check_lock(lock_file, logger=None):
    logger = get_logger(logger)
    logger.debug(f"Checking lock file: {lock_file}")
    try:
        with open(lock_file, 'r+') as f:
            try:
                # Attempt to acquire an exclusive non-blocking lock
                fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    lock_content = json.load(f)
                    logger.debug(f"Lock file content: {lock_content}")
                    # Check if the current time is beyond the lock's expiration timestamp
                    current_time = time.time()
                    one_hour_later = current_time + 3600  # 3600 seconds = 1 hour
                    expiration_timestamp = lock_content.get("expiration", 0)
                    logger.debug(f"Current time: {current_time}, Expiration time: {expiration_timestamp}")

                    if current_time > expiration_timestamp or expiration_timestamp > one_hour_later:
                        logger.debug("Lock is free")
                        lock_is_free = True
                    else:
                        logger.debug("Lock is acquired")
                        lock_is_free = False
                except json.JSONDecodeError:
                    logger.error("Lock file contains invalid JSON.")
                    return True  # Return True if JSON is invalid, indicating lock is free
                # If we reach this point, the lock was successfully acquired and is valid
                return lock_is_free
            except IOError: # fcntl.lockf raises IOError if the lock is held by another process
                # The lock is held by another process
                logger.error("Lock is currently held by another process.")
                return False
    except FileNotFoundError:
        logger.error("Lock file does not exist.")
        return False
    except Exception as e:
        logger.error(f"Error during lock check: {e}")
        return False
