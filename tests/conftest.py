import os
import pytest

@pytest.fixture(scope='session', autouse=True)
def change_test_dir(request):
    os.chdir(request.config.rootdir / 'src')
    yield
