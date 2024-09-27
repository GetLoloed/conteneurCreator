import pytest
from unittest.mock import patch
import conteneurCreator
import platform
import subprocess

@pytest.fixture(autouse=True)
def mock_input(mocker):
    mocker.patch('builtins.input', return_value='3')

@pytest.fixture(autouse=True)
def mock_create_container(mocker):
    mocker.patch('conteneurCreator.create_container')

def test_system_detection():
    assert conteneurCreator.system in ["Windows", "Linux"]

@pytest.mark.parametrize("is_root, expected", [(0, True), (1000, False)])
def test_root_check(mocker, is_root, expected):
    mocker.patch('os.geteuid', return_value=is_root)
    assert conteneurCreator.os.geteuid() == (0 if expected else 1000)

@pytest.mark.parametrize("os_info, expected", [
    ("debian", "debian"),
    ("ubuntu", "debian"),
    ("rhel", "redhat"),
    ("fedora", "redhat"),
    ("unknown", None)
])
def test_linux_family_detection(mocker, os_info, expected):
    mock_open = mocker.mock_open(read_data=os_info)
    mocker.patch('builtins.open', mock_open)
    if expected:
        assert conteneurCreator.linux_family == expected
    else:
        with pytest.raises(SystemExit):
            conteneurCreator.linux_family

def test_is_docker_installed_true(mocker):
    mocker.patch('subprocess.run', return_value=mocker.Mock(returncode=0))
    assert conteneurCreator.is_docker_installed() == True

def test_is_docker_installed_false(mocker):
    mocker.patch('subprocess.run', side_effect=FileNotFoundError())
    assert conteneurCreator.is_docker_installed() == False

def test_is_docker_active_true(mocker):
    mocker.patch('subprocess.run', return_value=mocker.Mock(returncode=0))
    assert conteneurCreator.is_docker_active() == True

def test_is_docker_active_false(mocker):
    mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cmd'))
    assert conteneurCreator.is_docker_active() == False

def test_display_message(mocker):
    mock_print = mocker.patch('builtins.print')
    mock_sleep = mocker.patch('time.sleep')
    conteneurCreator.display_message("Test message", pause=0)
    mock_print.assert_called_once()
    mock_sleep.assert_called_once_with(0)

@pytest.mark.parametrize("choice, image", [("1", "ubuntu"), ("2", "fedora"), ("3", "python")])
def test_create_container(mocker, choice, image):
    mocker.patch('builtins.input', side_effect=[choice, "n"])
    mock_run = mocker.patch('subprocess.run')
    mock_display = mocker.patch('conteneurCreator.display_message')
    mocker.patch('conteneurCreator.install_ssh')
    
    conteneurCreator.create_container()
    
    expected_command = f"docker run -d --name NOM-OS_A1 --network bridge  {image} sleep infinity"
    mock_run.assert_called_with(expected_command, shell=True)
    mock_display.assert_any_call(f"Conteneur NOM-OS_A1 créé avec succès et joignable par pont.", mocker.ANY)

def test_create_container_with_volume(mocker):
    mocker.patch('builtins.input', side_effect=["1", "y", "/test/path"])
    mock_run = mocker.patch('subprocess.run')
    mocker.patch('conteneurCreator.display_message')
    mocker.patch('conteneurCreator.install_ssh')
    
    conteneurCreator.create_container()
    
    expected_command = "docker run -d --name NOM-OS_A1 --network bridge -v /test/path:/data ubuntu sleep infinity"
    mock_run.assert_called_with(expected_command, shell=True)

@pytest.mark.parametrize("image, install_cmd, start_cmd", [
    ("ubuntu", "apt update && apt install -y openssh-server", "service ssh start"),
    ("fedora", "dnf install -y openssh-server", "/usr/sbin/sshd")
])
def test_install_ssh(mocker, image, install_cmd, start_cmd):
    mock_run = mocker.patch('subprocess.run')
    mocker.patch('conteneurCreator.display_message')
    
    conteneurCreator.install_ssh("test_container", image)
    
    mock_run.assert_any_call(f"docker exec -it test_container bash -c '{install_cmd}'", shell=True)
    mock_run.assert_any_call(f"docker exec -it test_container bash -c '{start_cmd}'", shell=True)

def test_install_ssh_unsupported_image(mocker):
    mocker.patch('conteneurCreator.display_message')
    with pytest.raises(SystemExit):
        conteneurCreator.install_ssh("test_container", "unsupported_image")

# Test pour la boucle principale (si applicable)
def test_main_loop(mocker):
    mocker.patch('conteneurCreator.create_container')
    mock_input = mocker.patch('builtins.input', side_effect=["y", "n"])
    
    conteneurCreator.main()
    
    assert mock_input.call_count == 2
    conteneurCreator.create_container.assert_called_once()