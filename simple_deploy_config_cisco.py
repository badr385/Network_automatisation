from netmiko import ConnectHandler
from getpass import getpass

# Prompt for username and password
username = input("Enter your SSH username: ")
password = getpass("Enter your SSH password: ")

# Load device list from a file (one hostname/IP per line)
with open("devices.txt") as f:
    devices = [line.strip() for line in f if line.strip()]

# Configuration commands to push
commands = [
    "ip scp server enable",
    "ip tcp window-size 65535",
    "ip ssh window-size 65535"
]

for host in devices:
    print(f"\n=== Connecting to {host} ===")
    try:
        device = {
            "device_type": "cisco_ios",
            "host": host,
            "username": username,
            "password": password,
        }

        connection = ConnectHandler(**device)

        # Enter config mode and send commands
        output = connection.send_config_set(commands)
        print(output)

        # Save config
        save_out = connection.save_config()
        print(save_out)

        connection.disconnect()
    except Exception as e:
        print(f"Failed to connect {host}: {e}")
