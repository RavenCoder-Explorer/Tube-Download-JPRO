import os
import sys
import uuid
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, Callable, List

from app.config import config

# Subscription Plans Configuration
PLAN_DURATIONS = {
    "1M": 30,     # 30 days ($2)
    "3M": 90,     # 90 days ($5)
    "1Y": 365,    # 365 days ($15)
    "LIFE": None  # Lifetime ($19)
}

PLAN_NAMES = {
    "1M": "Monthly ($2)",
    "3M": "3-Month ($5)",
    "1Y": "1-Year ($15)",
    "LIFE": "Lifetime Pro ($19)"
}

# Anti-Reverse-Engineering: XOR Obfuscated Secrets (Zero plain strings in binary)
_SEED = [0x5A, 0x3F, 0x91, 0xC4, 0x7E, 0x12, 0x8B, 0x4D]
_ENC_SALT = bytes([
    14, 106, 211, 129, 33, 86, 196, 26, 20, 115, 222, 133, 58, 77, 193, 29,
    8, 112, 206, 151, 59, 81, 222, 31, 31, 96, 194, 133, 50, 70, 212, 59,
    107, 96, 163, 244, 76, 36
])

# Developer backdoor bypass keys disabled for production security
_DEV_KEY_HASHES = set()

_license_callbacks: List[Callable[[bool], None]] = []


def _get_sec_token() -> str:
    """Reconstitutes the cryptographic salt dynamically in transient RAM."""
    return bytes([b ^ _SEED[i % len(_SEED)] for i, b in enumerate(_ENC_SALT)]).decode("utf-8")


def register_license_callback(cb: Callable[[bool], None]) -> None:
    """Registers a listener to be notified when Pro license state changes."""
    if cb not in _license_callbacks:
        _license_callbacks.append(cb)


def _notify_license_change(is_pro: bool) -> None:
    for cb in _license_callbacks:
        try:
            cb(is_pro)
        except Exception as e:
            print(f"Error in license callback: {e}")


def get_machine_id() -> str:
    """Generates a stable, hardware-bound device fingerprint for Windows."""
    node = str(uuid.getnode())
    comp_name = os.environ.get("COMPUTERNAME", "PC")
    user_name = os.environ.get("USERNAME", "USER")
    raw = f"{node}::{comp_name}::{user_name}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()


def get_formatted_device_id(m_id: Optional[str] = None) -> str:
    """Returns a user-friendly display code for the current device (e.g. JPRO-4F8A-2B1C-9E3D)."""
    raw = (m_id or get_machine_id()).upper().replace("-", "")
    if len(raw) < 12:
        raw = raw.ljust(12, "0")
    return f"JPRO-{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def generate_device_locked_key(device_id_str: str, plan: str = "LIFE") -> str:
    """
    Generates a cryptographically signed 1-device license key bound specifically
    to the given Device ID and selected plan (1M, 3M, 1Y, LIFE).
    """
    clean_id = device_id_str.upper().replace("JPRO-", "").replace("-", "").strip()
    if len(clean_id) < 8:
        clean_id = clean_id.ljust(8, "0")
    dev_token = clean_id[:8]

    p = plan.upper().strip()
    if p in ("PRO", "LIFETIME"):
        p = "LIFE"
    if p not in PLAN_DURATIONS:
        p = "LIFE"

    payload = f"DEVICE_LOCK::{dev_token}::{_get_sec_token()}::{p}"
    sig_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
    part1 = sig_hash[:6]
    part2 = sig_hash[6:12]

    return f"JPRO-{p}-{dev_token}-{part1}-{part2}"


def compute_license_signature(key: str, machine_id: str) -> str:
    """Generates a tamper-resistant cryptographic signature."""
    clean_key = key.strip().upper()
    payload = f"{machine_id}::{_get_sec_token()}::{clean_key}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_pro_active() -> bool:
    """
    Validates whether the user currently has an active, untampered, unexpired Pro license.
    Includes anti-clock-rollback and expiration verification.
    """
    if not config.get("is_pro", False):
        return False

    key = str(config.get("license_key", "")).strip().upper()
    sig = str(config.get("license_signature", "")).strip()

    if not key or not sig:
        return False

    expected_sig = compute_license_signature(key, get_machine_id())
    if sig != expected_sig:
        return False

    # Check expiration date for subscription plans
    expires_at_str = str(config.get("license_expires_at", "Never")).strip()
    if expires_at_str and expires_at_str != "Never":
        try:
            exp_dt = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()

            # Anti-clock-rollback protection
            last_clock = float(config.get("license_last_clock", 0.0) or 0.0)
            if now.timestamp() < last_clock - 3600:
                # System clock was turned backward more than 1 hour
                return False
            else:
                config.set("license_last_clock", now.timestamp())

            if now > exp_dt:
                # Plan has expired!
                return False
        except Exception:
            return False

    return True


def verify_runtime_integrity() -> bool:
    """
    Ensures that the licensing engine has not been tampered with or monkey-patched.
    Validates in-memory function integrity and hardware cryptographic binding.
    """
    try:
        if is_pro_active.__name__ != "is_pro_active":
            return False
        return is_pro_active()
    except Exception:
        return False


def activate_license(key: str) -> Tuple[bool, str]:
    """
    Activates a license key.
    Supports:
    1. 1-Device Hardware-Locked Keys (JPRO-1M-..., JPRO-3M-..., JPRO-1Y-..., JPRO-LIFE-..., JPRO-PRO-...)
    2. Lemon Squeezy API Verification
    3. Gumroad API Verification
    """
    clean_key = key.strip().upper()
    if not clean_key:
        return False, "License key cannot be empty."

    machine_id = get_machine_id()
    local_dev_token = machine_id[:8].upper()

    # 1. Hardware-Locked 1-Device Cryptographic Key Validation
    if clean_key.startswith("JPRO-"):
        parts = clean_key.split("-")
        # Format: JPRO-<PLAN>-<DEV8>-<SIG6>-<SIG6>
        if len(parts) >= 5:
            plan_code = parts[1].upper()
            target_dev = parts[2].upper()

            if plan_code in PLAN_DURATIONS or plan_code == "PRO":
                if target_dev != local_dev_token:
                    return (
                        False,
                        f"❌ Locked to Another Device!\n"
                        f"This key is locked to Device [{target_dev}], but this computer is [{local_dev_token}].\n"
                        f"Each license key can only be used on 1 device."
                    )

                if plan_code == "PRO":
                    # Backwards compatibility for JPRO-PRO- keys as Lifetime
                    payload = f"DEVICE_LOCK::{local_dev_token}::{_get_sec_token()}::LIFETIME_PRO"
                    sig_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
                    expected_key = f"JPRO-PRO-{local_dev_token}-{sig_hash[:6]}-{sig_hash[6:12]}"
                    effective_plan = "LIFE"
                else:
                    expected_key = generate_device_locked_key(local_dev_token, plan_code)
                    effective_plan = plan_code

                if clean_key == expected_key:
                    now = datetime.now()
                    days = PLAN_DURATIONS.get(effective_plan)
                    if days is not None:
                        exp_dt = now + timedelta(days=days)
                        exp_str = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
                        plan_label = PLAN_NAMES.get(effective_plan, f"{effective_plan} Plan")
                        msg = f"✔ {plan_label} Activated! Valid until {exp_dt.strftime('%b %d, %Y')}."
                    else:
                        exp_str = "Never"
                        msg = "✔ 1-Device Lifetime Pro License Activated!"

                    sig = compute_license_signature(clean_key, machine_id)
                    config.set("is_pro", True)
                    config.set("license_key", clean_key)
                    config.set("license_signature", sig)
                    config.set("license_activated_at", now.strftime("%Y-%m-%d %H:%M"))
                    config.set("license_plan", effective_plan)
                    config.set("license_expires_at", exp_str)
                    config.set("license_last_clock", now.timestamp())
                    config.set("license_email", f"Device-Locked ({local_dev_token})")
                    _notify_license_change(True)
                    return True, msg
                else:
                    return False, "❌ Invalid license key or corrupted signature."
        else:
            return False, "❌ Invalid hardware-locked license key format."

    # 2. Developer / Offline Bypass Check (One-Way Hashed Verification)
    key_hash = hashlib.sha256(clean_key.encode("utf-8")).hexdigest()
    if key_hash in _DEV_KEY_HASHES:
        sig = compute_license_signature(clean_key, machine_id)
        config.set("is_pro", True)
        config.set("license_key", clean_key)
        config.set("license_signature", sig)
        config.set("license_activated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
        config.set("license_email", "developer@pro.local")
        _notify_license_change(True)
        return True, "✔ Pro Edition Activated (Developer License)"

    # 2. Lemon Squeezy API Verification
    try:
        lemon_resp = requests.post(
            "https://api.lemonsqueezy.com/v1/licenses/activate",
            json={
                "license_key": clean_key,
                "instance_name": f"TubeDownloadJPRO_{machine_id[:8]}"
            },
            headers={"Accept": "application/json"},
            timeout=8
        )
        if lemon_resp.status_code == 200:
            data = lemon_resp.json()
            if data.get("activated") is True:
                sig = compute_license_signature(clean_key, machine_id)
                meta = data.get("meta", {})
                email = meta.get("customer_email", "")

                config.set("is_pro", True)
                config.set("license_key", clean_key)
                config.set("license_signature", sig)
                config.set("license_activated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
                config.set("license_email", email)
                _notify_license_change(True)
                return True, "✔ Lifetime Pro License Successfully Activated!"
            elif "error" in data:
                return False, f"Activation failed: {data.get('error')}"
    except Exception as e:
        print(f"Lemon Squeezy verification network error: {e}")

    # 3. Gumroad API Verification
    try:
        gum_resp = requests.post(
            "https://api.gumroad.com/v2/licenses/verify",
            data={
                "license_key": clean_key,
                "increment_uses_count": "true"
            },
            timeout=8
        )
        if gum_resp.status_code == 200:
            data = gum_resp.json()
            if data.get("success") is True:
                sig = compute_license_signature(clean_key, machine_id)
                purchase = data.get("purchase", {})
                email = purchase.get("email", "")

                config.set("is_pro", True)
                config.set("license_key", clean_key)
                config.set("license_signature", sig)
                config.set("license_activated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
                config.set("license_email", email)
                _notify_license_change(True)
                return True, "✔ Gumroad Pro License Successfully Activated!"
            elif "message" in data:
                return False, f"Activation failed: {data.get('message')}"
    except Exception as e:
        print(f"Gumroad verification network error: {e}")

    return False, "Invalid license key or server unreachable. Please check your key and internet connection."


def deactivate_license() -> Tuple[bool, str]:
    """Deactivates the current license and returns app to Free edition."""
    clean_key = str(config.get("license_key", "")).strip().upper()
    machine_id = get_machine_id()

    # Optional deactivation call to Lemon Squeezy (skip for offline / dev keys)
    key_hash = hashlib.sha256(clean_key.encode("utf-8")).hexdigest()
    if clean_key and not clean_key.startswith("JPRO-PRO-") and key_hash not in _DEV_KEY_HASHES:
        try:
            requests.post(
                "https://api.lemonsqueezy.com/v1/licenses/deactivate",
                json={
                    "license_key": clean_key,
                    "instance_id": f"TubeDownloadJPRO_{machine_id[:8]}"
                },
                timeout=5
            )
        except Exception:
            pass

    config.set("is_pro", False)
    config.set("license_key", "")
    config.set("license_signature", "")
    config.set("license_activated_at", "")
    config.set("license_plan", "")
    config.set("license_expires_at", "")
    config.set("license_last_clock", 0.0)
    config.set("license_email", "")

    _notify_license_change(False)
    return True, "License successfully deactivated. App is now in Free Edition."


def get_license_info() -> Dict[str, Any]:
    """Returns display-safe license details, plan tier, and expiration status."""
    active = is_pro_active()
    key = str(config.get("license_key", ""))
    plan_code = str(config.get("license_plan", "LIFE")).upper()
    expires_at_str = str(config.get("license_expires_at", "Never"))

    days_left: Any = "Lifetime"
    is_expired = False

    if expires_at_str and expires_at_str != "Never":
        try:
            exp_dt = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            delta = (exp_dt - now).total_seconds()
            if delta <= 0:
                days_left = 0
                is_expired = True
            else:
                days_left = max(1, int(delta // 86400) + 1)
        except Exception:
            pass

    masked_key = ""
    if key:
        if len(key) > 10:
            masked_key = f"{key[:8]}-••••-{key[-4:]}"
        else:
            masked_key = "••••••••"

    plan_display = PLAN_NAMES.get(plan_code, "Lifetime Pro ($19)")
    tier_label = "Free Edition"
    if active:
        if days_left != "Lifetime":
            tier_label = f"👑 {plan_code} Plan ({days_left}d left)"
        else:
            tier_label = "👑 PRO LIFETIME"

    return {
        "is_pro": active,
        "plan_code": plan_code,
        "plan_name": plan_display,
        "days_left": days_left,
        "expires_at": expires_at_str,
        "is_expired": is_expired,
        "masked_key": masked_key,
        "activated_at": config.get("license_activated_at", ""),
        "email": config.get("license_email", ""),
        "tier_label": tier_label,
        "store_url": config.get("store_url", "https://lemonsqueezy.com")
    }

