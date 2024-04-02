import pytest
from popocr.popocr import run_command_with_timeout, SystemCallError

def test_successful_command():
    """Test that a successful command returns the correct output."""
    command = ['echo', 'hello']
    expected_output = 'hello\n'
    output = run_command_with_timeout(command, 5)
    assert output == expected_output

def test_timeout():
    """Test that the function raises an error when the command times out."""
    command = ['sleep', '2']  # Adjust sleep time if necessary to ensure timeout
    with pytest.raises(SystemCallError) as excinfo:
        run_command_with_timeout(command, 1)  # Set a timeout less than the sleep time
    assert 'timed out' in str(excinfo.value)

def test_non_zero_exit():
    """Test that the function raises an error when the command fails."""
    command = ['ls', 'non_existent_file']
    with pytest.raises(SystemCallError) as excinfo:
        run_command_with_timeout(command, 5)
    assert 'failed with exit status' in str(excinfo.value)

def test_unexpected_error():
    """Test the function's response to an unexpected error."""
    # Use a command that's likely not present on the system
    command = ['some_nonexistent_command']
    with pytest.raises(SystemCallError) as excinfo:
        run_command_with_timeout(command, 5)
    assert 'An error occurred while executing command' in str(excinfo.value)
