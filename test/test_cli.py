import tempfile
import unittest
from pathlib import Path

from main import main


class CommandLineTests(unittest.TestCase):
    def test_compiles_source_to_requested_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "program.nc"
            output = root / "game.sb3"
            source.write_text(
                "sprite Main { fn main() -> int { Move(10, 20); return 0; } }",
                encoding="utf-8",
            )
            self.assertEqual(main([str(source), "-o", str(output)]), 0)
            self.assertTrue(output.is_file())

    def test_check_does_not_write_an_output_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.nc"
            source.write_text("sprite Main { fn main() -> int { return 0; } }", encoding="utf-8")
            self.assertEqual(main([str(source), "--check"]), 0)
            self.assertFalse(source.with_suffix(".sb3").exists())
