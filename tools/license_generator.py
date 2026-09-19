#!/usr/bin/env python3
"""
Tube Download JPRO - 1-Device License Key Generator
Generates cryptographically signed license keys bound to a single computer hardware ID.
Supports: Monthly ($2), 3-Month ($5), 1-Year ($15), and Lifetime ($19) plans.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.license_manager import (
    generate_device_locked_key,
    get_formatted_device_id,
    get_machine_id,
    PLAN_DURATIONS,
    PLAN_NAMES
)


def record_license_sale(dev_id_str: str, selected_plan: str, key: str, customer_note: str = "Direct Sale"):
    """Records the transaction in both a human-readable text file and an Excel-compatible CSV."""
    clean_dev = dev_id_str.upper().replace("JPRO-", "").replace("-", "").strip()[:8]
    plan_prices = {
        "1M": 2.00,
        "3M": 5.00,
        "1Y": 15.00,
        "LIFE": 19.00
    }
    price_val = plan_prices.get(selected_plan, 19.00)
    plan_label = PLAN_NAMES.get(selected_plan, f"{selected_plan} Plan")
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 1. Text log
    log_file = PROJECT_ROOT / "licenses_issued.txt"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] Plan: {selected_plan} (${price_val:.2f}) | Key: {key} | Device: {clean_dev} | Note: {customer_note}\n")
    except Exception as e:
        print(f"Warning: Could not write to licenses_issued.txt: {e}")

    # 2. Excel-compatible CSV spreadsheet
    csv_file = PROJECT_ROOT / "licenses_issued.csv"
    try:
        write_header = not csv_file.exists() or csv_file.stat().st_size == 0
        with open(csv_file, "a", encoding="utf-8") as f:
            if write_header:
                f.write("Date_Time,Customer_Note,Plan,Price_USD,License_Key,Device_ID\n")
            safe_note = customer_note.replace('"', '""')
            f.write(f'"{now_str}","{safe_note}","{plan_label}",{price_val:.2f},"{key}","{clean_dev}"\n')
    except Exception as e:
        print(f"Warning: Could not write to licenses_issued.csv: {e}")

    return log_file, csv_file, price_val, plan_label


def generate_interactive():
    print("=" * 64)
    print("      👑 TUBE DOWNLOAD JPRO - 1-DEVICE LICENSE GENERATOR")
    print("=" * 64)
    print("This tool generates cryptographically signed subscription &")
    print("lifetime keys mathematically locked to 1 customer computer.")
    print("=" * 64)
    print()

    # Local computer shortcut
    local_dev_id = get_formatted_device_id()
    print(f"Tip: Your local computer's Device ID is: {local_dev_id}")
    print()

    # 1. Device ID input
    while True:
        try:
            raw_input_id = input("Enter Customer's Device ID (e.g. JPRO-4F8A-2B1C-9E3D) or 'local': ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return

        if not raw_input_id:
            print("Device ID cannot be empty. Please try again.\n")
            continue

        if raw_input_id.lower() == "local":
            raw_input_id = local_dev_id

        break

    # 2. Plan selection
    print("\nSelect License Plan:")
    print("  [1] Monthly  ($2)   - 30 Days")
    print("  [2] 3-Month  ($5)   - 90 Days ($1.66/mo)")
    print("  [3] 1-Year   ($15)  - 365 Days ($1.25/mo)")
    print("  [4] Lifetime ($19)  - Never Expires (Default)")

    plan_choice = input("Enter choice (1-4) [default: 4]: ").strip()
    plan_map = {
        "1": "1M",
        "2": "3M",
        "3": "1Y",
        "4": "LIFE"
    }
    selected_plan = plan_map.get(plan_choice, "LIFE")

    # 3. Customer note
    try:
        customer_note = input("\nEnter Customer Name or Order # (Optional): ").strip()
    except (KeyboardInterrupt, EOFError):
        customer_note = "Direct Sale"

    if not customer_note:
        customer_note = "Direct Sale"

    # Generate key
    key = generate_device_locked_key(raw_input_id, selected_plan)
    clean_dev = raw_input_id.upper().replace("JPRO-", "").replace("-", "").strip()[:8]

    log_file, csv_file, price_val, plan_label = record_license_sale(raw_input_id, selected_plan, key, customer_note)

    print("\n" + "=" * 64)
    print("✔ LICENSE KEY GENERATED SUCCESSFULLY!")
    print("=" * 64)
    print(f"🔑 LICENSE KEY:  {key}")
    print(f"📦 PLAN TIER:    {plan_label}")
    print(f"💻 LOCKED TO:    Device [{clean_dev}] ({customer_note})")
    print("🔒 RESTRICTION:  Mathematically locked to 1 device only.")
    print("=" * 64)
    print()
    print("📋 READY-TO-SEND CUSTOMER MESSAGE:")
    print("-" * 64)
    print(f"Thank you for purchasing Tube Download JPRO {plan_label}!")
    print(f"Your 1-Device License Key:")
    print(f"{key}")
    print()
    print("To activate:")
    print("1. Open Tube Download JPRO.")
    print("2. Click [ ⭐ Upgrade ] on the left sidebar (or in Settings).")
    print("3. Paste the key above and click [ 🔑 Activate ].")
    print("-" * 64)
    print(f"Transaction logged to: {log_file}")
    print(f"Spreadsheet ledger:    {csv_file}")
    print()

    input("Press Enter to exit...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        dev_arg = sys.argv[1]
        plan_arg = sys.argv[2] if len(sys.argv) > 2 else "LIFE"
        note_arg = sys.argv[3] if len(sys.argv) > 3 else "Direct Sale"
        key = generate_device_locked_key(dev_arg, plan_arg)
        record_license_sale(dev_arg, plan_arg, key, note_arg)
        print(key)
    else:
        generate_interactive()
