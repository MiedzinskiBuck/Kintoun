import os
import unittest
from unittest import mock

from functions import utils


class TestUtils(unittest.TestCase):
    def test_module_result_defaults(self):
        result = utils.module_result(data={"ok": True})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"], {"ok": True})
        self.assertEqual(result["errors"], [])

    def test_create_temp_zip_path_creates_file(self):
        temp_path = utils.create_temp_zip_path()
        try:
            self.assertTrue(os.path.exists(temp_path))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_poll_until_success(self):
        checks = {"count": 0}

        def check():
            checks["count"] += 1
            return checks["count"] >= 2

        with mock.patch("functions.utils.time.sleep"):
            result = utils.poll_until(check, interval_seconds=0, max_attempts=3)
        self.assertTrue(result)

    def test_poll_until_timeout(self):
        with mock.patch("functions.utils.time.sleep"):
            result = utils.poll_until(lambda: False, interval_seconds=0, max_attempts=2)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
