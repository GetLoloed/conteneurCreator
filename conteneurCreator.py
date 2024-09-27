import platform
import subprocess
import os
import time
from colorama import init, Fore, Style

# Initialiser colorama pour la coloration du texte
init(autoreset=True)

# Fonction pour afficher des messages avec pauses
def display_message(message, color=Fore.WHITE, pause=2):
    print(color + message)
    time.sleep(pause)

# 1. Détecter si on est sur Windows ou Linux
system = platform.system()
if system == "Linux":
    display_message("Vous êtes sur Linux.", Fore.GREEN)

    # Vérifier si l'utilisateur est root
    if os.geteuid() == 0:
        display_message("Vous êtes root.", Fore.GREEN)
    else:
        display_message("Vous n'êtes pas root.", Fore.RED)
        exit()

    # Détection de la famille Linux (Debian/RedHat)
    with open("/etc/os-release", "r") as f:
        os_info = f.read()
    if "debian" in os_info.lower() or "ubuntu" in os_info.lower():
        linux_family = "debian"
        display_message("Famille Linux: Debian/Ubuntu", Fore.BLUE)
    elif "rhel" in os_info.lower() or "fedora" in os_info.lower():
        linux_family = "redhat"
        display_message("Famille Linux: RedHat/Fedora", Fore.BLUE)
    else:
        display_message("Famille Linux inconnue.", Fore.RED)
        exit()

elif system == "Windows":
    display_message("Vous êtes sur Windows.", Fore.GREEN)

else:
    display_message("Système d'exploitation non supporté.", Fore.RED)
    exit()

# 2. Docker est-il installé ?
def is_docker_installed():
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

if is_docker_installed():
    display_message("Docker est installé.", Fore.GREEN)
else:
    display_message("Docker n'est pas installé.", Fore.RED)

    # Installer Docker sur Linux
    if system == "Linux":
        if linux_family == "debian":
            display_message("Installation de Docker via apt...", Fore.YELLOW)
            subprocess.run(["apt", "update"], check=True)
            subprocess.run(["apt", "install", "-y", "docker.io"], check=True)
        elif linux_family == "redhat":
            display_message("Installation de Docker via dnf...", Fore.YELLOW)
            subprocess.run(["dnf", "install", "-y", "docker"], check=True)

    # Installer Docker sur Windows via winget
    elif system == "Windows":
        try:
            display_message("Tentative d'installation de Docker via winget...", Fore.YELLOW)
            subprocess.run(["winget", "install", "Docker.DockerDesktop"], check=True)
            display_message("Docker installé avec succès via winget.", Fore.GREEN)
        except subprocess.CalledProcessError:
            display_message("Échec de l'installation de Docker via winget.", Fore.RED)
            exit()

# 3. Le service Docker est-il actif ?
def is_docker_active():
    try:
        subprocess.run(["systemctl", "is-active", "--quiet", "docker"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

if system == "Linux":
    if is_docker_active():
        display_message("Le service Docker est actif.", Fore.GREEN)
    else:
        display_message("Le service Docker est inactif. Démarrage...", Fore.YELLOW)
        subprocess.run(["systemctl", "start", "docker"], check=True)
        display_message("Service Docker démarré.", Fore.GREEN)

# 4. Créer un conteneur
container_count = 0

def create_container():
    global container_count
    container_count += 1
    # Choisir le type de conteneur
    display_message("Choisissez un type de conteneur:", Fore.CYAN)
    print("1. Ubuntu/Debian")
    print("2. RedHat/Fedora")
    print("3. Python")

    choice = input(Fore.YELLOW + "Votre choix: ")

    if choice == "1":
        image = "ubuntu"
    elif choice == "2":
        image = "fedora"
    elif choice == "3":
        image = "python"
    else:
        display_message("Choix invalide.", Fore.RED)
        return

    container_name = f"NOM-OS_A{container_count}"

    # Proposer d'ajouter un volume persistant
    attach_volume = input(Fore.YELLOW + "Souhaitez-vous attacher un volume persistant ? (y/n): ").lower()
    volume_option = ""
    if attach_volume == "y":
        volume_path = input(Fore.YELLOW + "Indiquez le chemin du volume: ")
        volume_option = f"-v {volume_path}:/data"

    # Créer le conteneur
    display_message(f"Création du conteneur {container_name} basé sur {image}...", Fore.YELLOW)
    subprocess.run(f"docker run -d --name {container_name} --network bridge {volume_option} {image} sleep infinity", shell=True)
    display_message(f"Conteneur {container_name} créé avec succès et joignable par pont.", Fore.GREEN)

   # Installer SSH dans le conteneur
    install_ssh(container_name, image)

# 5. Installer SSH et le configurer pour l'accès root
def install_ssh(container_name, image):
    display_message(f"Installation et configuration de SSH dans le conteneur {container_name}...", Fore.YELLOW)

    # Commandes pour installer SSH en fonction de l'image
    if "ubuntu" in image or "debian" in image:
        install_cmd = "apt update && apt install -y openssh-server"
        start_cmd = "service ssh start"
    elif "fedora" in image or "redhat" in image:
        install_cmd = "dnf install -y openssh-server"
        # Générer les clés SSH pour Fedora/RedHat
        keygen_cmd = "ssh-keygen -A"
        # Démarrer SSH manuellement (car systemctl/service peuvent ne pas fonctionner)
        start_cmd = "/usr/sbin/sshd"
    else:
        display_message("Le type de conteneur ne supporte pas l'installation de SSH.", Fore.RED)
        return  # Sortir si l'image ne supporte pas SSH

    # Exécuter les commandes d'installation SSH dans le conteneur
    subprocess.run(f"docker exec -it {container_name} bash -c '{install_cmd}'", shell=True)

    # Si Fedora/RedHat, générer les clés SSH après l'installation
    if "fedora" in image or "redhat" in image:
        subprocess.run(f"docker exec -it {container_name} bash -c '{keygen_cmd}'", shell=True)

    # Configurer SSH pour autoriser la connexion root
    subprocess.run(f"docker exec -it {container_name} bash -c \"echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config\"", shell=True)

    # Définir un mot de passe root
    subprocess.run(f"docker exec -it {container_name} bash -c \"echo 'root:rootpassword' | chpasswd\"", shell=True)

    # Démarrer le service SSH
    subprocess.run(f"docker exec -it {container_name} bash -c '{start_cmd}'", shell=True)

    display_message(f"SSH installé et configuré dans le conteneur {container_name}.", Fore.GREEN)


# Lancer le processus de création de conteneur
while True:
    create_container()
    another = input(Fore.YELLOW + "Voulez-vous créer un autre conteneur ? (y/n): ").lower()
    if another != "y":
        break