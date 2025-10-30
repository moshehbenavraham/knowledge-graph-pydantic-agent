import sys
from pathlib import Path
from unittest.mock import patch

# Add src directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import __main__ as src_main


def test_main_function_prints_correct_message():
    with patch("builtins.print") as mock_print:
        src_main.main()
        mock_print.assert_any_call("Please run the agent using the Streamlit UI:")
        mock_print.assert_any_call("streamlit run src/ui/streamlit_app.py")
