#!/usr/bin/env python3
import threading
import unittest
import os
import json
import time
import sys
import logging
from picoce_lock import acquire_lock

MAX_UNIX_TIMESTAMP = 2147483647

# Assuming logger is set up in this module or passed as an argument to functions that need it
logger = logging.getLogger('picoce_unittest')

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)


class TestLockingMechanism(unittest.TestCase):
    lock_file_path = ".lockfile_test"

    def setUp(self):
        logger.info("Ensure no lock file exists before each test to maintain test isolation.")
        if os.path.exists(self.lock_file_path):
            os.remove(self.lock_file_path)

    def test_1_single_instance_lock_acquisition(self):
        logger.info("Test #1: Single instance can successfully acquire a lock.")
        logger.info("Test #1: This also checks if the lock file is created upon lock acquisition.")
        self.assertTrue(acquire_lock(self.lock_file_path), "Failed to acquire lock for a single instance.")
        self.assertTrue(os.path.exists(self.lock_file_path), "Lock file was not created after acquiring lock.")
        logger.info("Test #1: SUCCESSFULLY COMPLETED\n")

    def tearDown(self):
        # ---
        # Clean up by removing the lock file after each test, ensuring no state leakage between tests.
        # ---
        #if os.path.exists(self.lock_file_path):
        #    os.remove(self.lock_file_path)
        pass

    def test_2_concurrent_instance_lock_prevention(self):
        logger.info("Test #2: a second instance cannot acquire a lock if it's already held by a first instance.")
        logger.info("Test #2: This ensures that concurrent access is properly prevented.")

        # Acquire the lock in the first instance for 5 seconds
        first_instance_lock_acquired = acquire_lock(self.lock_file_path, 5)
        if (first_instance_lock_acquired == True):
            logger.info("First instance acquired the lock successfully.")
        else:
            logger.error("First instance failed to acquire the lock.")
            self.fail("First instance failed to acquire the lock.")

        # Attempt to acquire the lock in the second instance while it's held by the first instance
        # 5 seconds is not yet elapsed, so the lock should not be possible to acquire
        second_instance_lock_acquired = acquire_lock(self.lock_file_path)
        if (second_instance_lock_acquired == True):
            logger.error("Second instance acquired the lock while it was held by another instance.")
            self.fail("Second instance acquired the lock while it was held by another instance.")
        else:
            logger.info("Second instance failed to acquire the lock while it was held by another instance.")

        self.assertFalse(second_instance_lock_acquired, "Second instance incorrectly acquired a lock while it was held by another instance.")
        logger.info("Test #2: SUCCESSFULLY COMPLETED\n")


    def test_4_stale_lock_handling(self):
        logger.info("Test #4: The handling of stale locks by attempting to acquire a lock with a stale lock file present.")
        logger.info("Test #4: This simulates a scenario where a lock file is left behind due to abnormal termination and checks if it can be overridden.")
        # Assuming self.lock_file_path is defined elsewhere
        with open(self.lock_file_path, "w") as f:
            json.dump({"expiration": MAX_UNIX_TIMESTAMP}, f)
        self.assertTrue(acquire_lock(self.lock_file_path), "Failed to acquire lock with a stale lock file present.")
        self.assertTrue(os.path.exists(self.lock_file_path), "Lock file does not exist after handling a stale lock.")
        logger.info("Test #4: SUCCESSFULLY COMPLETED\n")

    def test_5_cleanup_on_abnormal_termination(self):
        logger.info("Test #5: The cleanup of lock files upon abnormal termination")
        logger.info("Test #5: This test is simplified to check if the lock file exists after acquisition, without simulating actual abnormal termination")
        acquire_lock(self.lock_file_path)
        self.assertTrue(os.path.exists(self.lock_file_path), "Lock file does not exist after simulating abnormal termination.")
        logger.info("Test #5: SUCCESSFULLY COMPLETED\n")

    def test_6_lock_expiration(self):
        logger.info("Test #6: Lock automatically releases after expiration.")
        # Acquire the lock with a short expiration time (e.g., 2 seconds)
        acquire_lock(self.lock_file_path, duration_s = 2)
        # Wait for longer than the expiration time
        time.sleep(3)
        # Attempt to acquire the lock again, which should succeed if the lock has expired
        self.assertTrue(acquire_lock(self.lock_file_path), "Failed to acquire lock after expiration.")
        logger.info("Test #6: SUCCESSFULLY COMPLETED\n")

    def concurrent_lock_attempt(self, results, index):
        """
        Attempt to acquire the lock and record the result.
        """
        result = acquire_lock(self.lock_file_path, duration_s = 60)
        #if result:
        # If lock is acquired, release it immediately for other threads to attempt
        # release_lock(self.lock_file_path)
        results[index] = result

    def test_7_concurrent_lock_acquisition_stress_test(self):
        logger.info("Test #7: Concurrent Lock Acquisition Stress Test")
        thread_count = 10
        threads = []
        results = [False] * thread_count  # Initialize results list to track each thread's lock acquisition result

        # Start multiple threads to attempt lock acquisition simultaneously
        for i in range(thread_count):
            thread = threading.Thread(target=self.concurrent_lock_attempt, args=(results, i))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results - only one thread should have successfully acquired the lock
        successful_locks = sum(results)
        self.assertEqual(successful_locks, 1, f"More than one instance acquired the lock simultaneously: {successful_locks} instances.")
        logger.info("Test #8: SUCCESSFULLY COMPLETED\n")

if __name__ == '__main__':
    unittest.main()