import sys
import os

# Add the src directory to the Python path to allow imports from your package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from nexus_led_scoreboard.main import run_scoreboard


def test_run_scoreboard_placeholder(capsys):
    """
    Test that run_scoreboard prints the expected initial messages.
    """
    run_scoreboard()
    captured = capsys.readouterr()
    assert "Nexus LED Scoreboard is starting up..." in captured.out
    assert (
        "This is where the magic will happen for multi-sport display!" in captured.out
    )
