#!/usr/bin/env python3
import os
from getpass import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException


INPUT_XLSX = "devices.xlsx"
OUTPUT_XLSX = "file_output.xlsx"
SHOW_CMD = "show line vty 0 4"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise les noms de colonnes pour accepter différents formats d'Excel.
    Attendus: ip / host, user / username, device_type
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # aliases possibles
    rename_map = {}
    if "host" in df.columns and "ip" not in df.columns:
        rename_map["host"] = "ip"
    if "username" in df.columns and "user" not in df.columns:
        rename_map["username"] = "user"
    if "device" in df.columns and "device_type" not in df.columns:
        rename_map["device"] = "device_type"
    if rename_map:
        df.rename(columns=rename_map, inplace=True)

    required = {"ip", "user", "device_type"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Colonnes manquantes dans {INPUT_XLSX}: {sorted(missing)}. "
            f"Colonnes trouvées: {list(df.columns)}"
        )

    # Nettoyage basique
    df["ip"] = df["ip"].astype(str).str.strip()
    df["user"] = df["user"].astype(str).str.strip()
    df["device_type"] = df["device_type"].astype(str).str.strip()

    # Optionnel: enlever lignes vides
    df = df[df["ip"].ne("") & df["user"].ne("") & df["device_type"].ne("")]
    return df


def check_vty_line_config(device: dict, password: str) -> dict:
    """
    Se connecte au device et récupère 'show line vty 0 4'.
    Retourne un dict prêt à être écrit en Excel.
    """
    ip = device.get("ip", "")
    user = device.get("user", "")
    device_type = device.get("device_type", "")

    conn_params = {
        "device_type": device_type,
        "host": ip,
        "username": user,
        "password": password,
        "timeout": 15,
        "conn_timeout": 15,
        "banner_timeout": 15,
        "auth_timeout": 15,
        "fast_cli": True,
    }

    try:
        connection = ConnectHandler(**conn_params)
        output = connection.send_command(SHOW_CMD, read_timeout=30)
        connection.disconnect()

        return {
            "ip": ip,
            "device_type": device_type,
            "user": user,
            "status": "OK",
            "command": SHOW_CMD,
            "output": output,
            "error": "",
        }

    except NetmikoAuthenticationException as e:
        return {
            "ip": ip,
            "device_type": device_type,
            "user": user,
            "status": "AUTH_FAIL",
            "command": SHOW_CMD,
            "output": "",
            "error": str(e),
        }

    except NetmikoTimeoutException as e:
        return {
            "ip": ip,
            "device_type": device_type,
            "user": user,
            "status": "TIMEOUT",
            "command": SHOW_CMD,
            "output": "",
            "error": str(e),
        }

    except Exception as e:
        return {
            "ip": ip,
            "device_type": device_type,
            "user": user,
            "status": "ERROR",
            "command": SHOW_CMD,
            "output": "",
            "error": str(e),
        }


def main():
    if not os.path.exists(INPUT_XLSX):
        raise FileNotFoundError(f"Fichier introuvable: {INPUT_XLSX}")

    password = getpass("SSH password: ")

    df = pd.read_excel(INPUT_XLSX)
    df = normalize_columns(df)
    devices = df.to_dict("records")

    # règle simple: évite de mettre 100 threads si t'as 20 devices
    max_workers = min(40, max(5, len(devices)))
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(check_vty_line_config, d, password) for d in devices]
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            # mini feedback console
            print(f"{res['ip']} -> {res['status']}")

    out_df = pd.DataFrame(results).sort_values(by=["status", "ip"])
    out_df.to_excel(OUTPUT_XLSX, index=False)
    print(f"\n✅ Saved: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
