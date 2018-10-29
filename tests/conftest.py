import pytest
import sys
from shutil import copy
if sys.version_info >= (3, 0):
    from pathlib import Path
else:
    from pathlib2 import Path


@pytest.fixture
def exc_directory(tmp_path):
    test_file = Path(__file__)
    test_dir = test_file.parents[0]
    copy(str(test_dir / "sample.exc"), str(tmp_path))
    copy(str(test_dir / "sample.fir"), str(tmp_path))
    return tmp_path
