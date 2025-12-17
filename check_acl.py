import pandas as pd
from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor
import re

# Define the expected ACL entries
expected_acl_entries = [
        "permit ip_wanna_check, wildcard bits 0.0.0.31",
        "permit 10.0.0.0, wildcard bits 0.0.0.31",
        "deny   any log"
]

# Function to connect to a device and check for ACL
def check_acl(device_details):
    try:
        # Netmiko connection handler
        connection = ConnectHandler(
            device_type=device_details['device_type'],
            host=device_details['ip'],
            username=device_details['user'],
            password=getpass("SSH password: ")
        )

        # Command to get the ACL
        output = connection.send_command('show ip access-list name_acl')
        print(output)
        connection.disconnect()

        # Check each expected entry against the output
        missing_entries = [entry for entry in expected_acl_entries if entry not in output]

        # If there are missing entries, return them in the result
        if missing_entries:
            return {
                'ip': device_details['ip'],
                'missing_acl_entries': missing_entries
            }
        else:
            return None  # If all entries match, return None

    except Exception as e:
        return {
            'ip': device_details['ip'],
            'error': str(e)
        }

# Read device details from an Excel file using pandas
df = pd.read_excel('file.xlsx')
devices = df.to_dict('records')

# Use ThreadPoolExecutor to check ACLs concurrently and gather results
acl_check_results = []
with ThreadPoolExecutor(max_workers=20) as executor:
    results = executor.map(check_acl, devices)
    for result in results:
        if result:  # Include only devices with missing entries
            acl_check_results.append(result)

# Convert the results to a DataFrame
acl_check_df = pd.DataFrame(acl_check_results)

# Save the DataFrame to an Excel file
acl_check_df.to_excel('acl_check_results_snmp_telefonika.xlsx', index=False)
