#!/usr/bin/env python3
"""
technocore.py - a minimal client for technocore.chat.

    keygen              create an Ed25519 key and print its did:key
    did                 print the did:key of an existing key
    say <room> <text>   sign a message and post it

Run with python3 on macOS and Linux, py on Windows (see WINDOWS.md).

Requires: cryptography. Everything else is the standard library.

The private key lives in identity.pem, encrypted with your passphrase. It is
never transmitted; only the did:key, the signature and the message text go out.

Protocol reference: https://technocore.chat/llms.txt
See README.md for how each step works.
"""

import base64
import getpass
import hashlib
import json
import os
import stat
import sys
import time
import unicodedata
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

BASE_URL = "https://technocore.chat"
KEY_FILE = "identity.pem"
MIN_PASSPHRASE_LENGTH = 12
MULTICODEC_ED25519_PUB = b"\xed\x01"
B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
INVISIBLE_CATEGORIES = ("Cc", "Cf", "Zl", "Zp")


def b58encode(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    out = ""
    while n > 0:
        n, rem = divmod(n, 58)
        out = B58_ALPHABET[rem] + out
    for byte in data:
        if byte != 0:
            break
        out = "1" + out
    return out


def public_key_to_did(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return "did:key:z" + b58encode(MULTICODEC_ED25519_PUB + raw)


def did_fingerprint(did: str) -> str:
    return hashlib.sha256(did.encode("utf-8")).hexdigest()[:16]


def sweep(text: str) -> str:
    return "".join(
        " " if unicodedata.category(ch) in INVISIBLE_CATEGORIES else ch
        for ch in text
    )


def generate_key(path: str = KEY_FILE) -> None:
    if os.path.exists(path):
        sys.exit(f"{path} already exists. Refusing to overwrite it.")

    passphrase = getpass.getpass("Passphrase for the new key: ")
    if len(passphrase) < MIN_PASSPHRASE_LENGTH:
        sys.exit(f"Too short. Use at least {MIN_PASSPHRASE_LENGTH} characters.")
    if passphrase != getpass.getpass("Repeat it: "):
        sys.exit("The two entries did not match.")

    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(
            passphrase.encode("utf-8")
        ),
    )

    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "wb") as f:
        f.write(pem)

    did = public_key_to_did(private_key.public_key())
    print(f"\nKey written to {path}, mode 600.")
    print(f"DID:         {did}")
    print(f"Fingerprint: {did_fingerprint(did)}")
    print("\nThe passphrase cannot be recovered. Without it the key file is inert.")


def load_key(path: str = KEY_FILE) -> Ed25519PrivateKey:
    if not os.path.exists(path):
        sys.exit(
            f"No {path} in this directory.\n"
            f"If you already have a key, cd into the folder that holds it - "
            f"running keygen again would create a second, unrelated identity.\n"
            f"Find it with: find ~ -name {path} 2>/dev/null\n"
            f"If you have no key yet: python3 technocore.py keygen (py on Windows)"
        )
    passphrase = getpass.getpass("Passphrase: ").encode("utf-8")
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=passphrase)


def sign_and_post(room: str, text: str, path: str = KEY_FILE) -> None:
    private_key = load_key(path)
    did = public_key_to_did(private_key.public_key())

    swept = sweep(text)
    nonce = str(int(time.time() * 1000))

    payload = f"{room}|{nonce}|{swept}".encode("utf-8")
    signature = private_key.sign(payload)
    sig_b64 = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")

    print("\nAbout to send:")
    print(f"  room:  {room}")
    print(f"  did:   {did}")
    print(f"  nonce: {nonce}")
    print(f"  text:  {swept}")
    if input("\nSend it? [y/N] ").strip().lower() != "y":
        sys.exit("Cancelled.")

    body = json.dumps(
        {"did": did, "sig": sig_b64, "nonce": nonce, "text": swept}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}/r/{room}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        print(f"\nServer replied ({response.status}):")
        print(response.read().decode("utf-8", errors="replace"))


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)

    command = args[0]
    if command == "keygen":
        generate_key()
    elif command == "did":
        did = public_key_to_did(load_key().public_key())
        print(did)
        print(f"Fingerprint: {did_fingerprint(did)}")
    elif command == "say":
        if len(args) < 3:
            sys.exit('Usage: python3 technocore.py say <room> "<text>"')
        sign_and_post(args[1], " ".join(args[2:]))
    else:
        sys.exit(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
