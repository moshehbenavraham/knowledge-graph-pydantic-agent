import sys
from pathlib import Path
from unittest.mock import patch

# Add src directory to path to import the module
sys.path.append(str(Path(__file__).parent.parent.resolve() / "src"))
import __main__


def test_main_function_prints_correct_message():
    with patch("builtins.print") as mock_print:
        __main__.main()
        mock_print.assert_any_call("Please run the agent using the Streamlit UI:")
        mock_print.assert_any_call("streamlit run src/ui/streamlit_app.py")
