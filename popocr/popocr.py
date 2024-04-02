"""
Convert image and PDF files into text and/or structured text
"""
import subprocess
from subprocess import TimeoutExpired, CalledProcessError
from typing import IO, List, Dict, Optional, Any


class ConversionOptions:
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        if options is None:
            options = {}

        valid_keys = {"first_page", "last_page"}

        for key in options.keys():
            if key not in valid_keys:
                raise ValueError(f"Invalid option: {key}")

        self.first_page = options.get("first_page", 1)
        self.last_page = options.get("last_page", 1)


class SystemCallError(Exception):
    pass


def convert_file(fp: IO[bytes], options: Optional[ConversionOptions] = None) -> List[IO[bytes]]:
    """
    Calls poppler and returns list of output file objects

    Inputs:
    - fp: input file object
    - options: Dict of conversion options with keys:
        "first_page": int
        "last_page": int
    """
    return []


def run_command_with_timeout(command, timeout):
    """
    Runs a system command with a specified timeout. Raises SystemCallError if the command fails or returns a non-zero exit status.

    Parameters:
    - command (list): The command to execute and its arguments as a list.
    - timeout (int): The timeout in seconds.

    Returns:
    - The output of the command if successful.

    Raises:
    - SystemCallError: If the command fails, times out, or returns a non-zero exit status.
    """
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=timeout)
        return result.stdout
    except TimeoutExpired as e:
        raise SystemCallError(f"Command '{' '.join(command)}' timed out after {timeout} seconds") from e
    except CalledProcessError as e:
        error_message = e.stderr.strip() if e.stderr else e.stdout.strip()
        raise SystemCallError(f"Command '{' '.join(command)}' failed with exit status {e.returncode}: {error_message}") from e
    except Exception as e:
        raise SystemCallError(f"An error occurred while executing command '{' '.join(command)}': {str(e)}") from e
