"""Exercise the actual Hermes loader without inference or active profiles."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

AUTOMATION = Path(__file__).resolve().parents[1]


class NativeTests(unittest.TestCase):
    def test_native_cli_and_all_shipping_skills_load_from_fresh_home(self):
        script = AUTOMATION / "verify_native.py"
        self.assertTrue(script.is_file(), "missing native Hermes loader check")
        try:
            available = importlib.util.find_spec("tools.skills_tool")
        except ModuleNotFoundError:
            available = None
        if available is None:
            self.skipTest("Hermes verification environment is not installed")
        # Keep the isolated home. This test never deletes Hermes profiles.
        root = Path(tempfile.mkdtemp(prefix="pstack-native-"))
        result = subprocess.run(
            [sys.executable, str(script), "--package", str(AUTOMATION.parent),
             "--home", str(root / "home")], capture_output=True, text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        report = json.loads(result.stdout)
        self.assertEqual(report["loaded_skills"], 55)
        self.assertGreaterEqual(report["loaded_support_files"], 62)
        self.assertTrue(report["cli_passed"])
        self.assertFalse(report["inference_performed"])


if __name__ == "__main__":
    unittest.main()
