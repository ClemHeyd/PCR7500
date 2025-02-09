#!/usr/bin/env python3
"""
Attestation daemon that:
 - Listens on a Unix domain socket at /tmp/qemu-socket.
 - Receives files and metadata using a simple custom protocol.
 - Stores received files and creates a timestamped directory.
 - Signs the file data using Ed25519, saves a base64-encoded signature.

Requires the 'cryptography' library.
"""
import socket
import struct
import os
import time
import hashlib
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidKey
from asn1crypto.core import Sequence, OctetString, UTF8String

# Path for the UNIX domain socket (should match the QEMU command line)
SOCKET_PATH = "/tmp/org.causality.attestation"

# Base directory where received files will be stored.
# Files and their signatures will be placed in a folder named after the current Unix timestamp.
OUTPUT_BASE_DIR = "/var/lib/attestation_results"

# File to store/load Ed25519 private key
SIGNING_KEY_PATH = "/var/lib/pcr_attestation_keys/signing_key.pem"

###############################################################################
# ERROR HANDLING
###############################################################################

class AttestationDaemonError(Exception):
    """Custom exception to clarify daemon-specific errors."""
    pass


###############################################################################
# KEY MANAGEMENT
###############################################################################

def save_private_key(private_key: ed25519.Ed25519PrivateKey, key_path: str) -> None:
    """
    Save an Ed25519 private key to disk in PEM format.
    
    :param private_key: The Ed25519 private key to save
    :param key_path: Path where the private key will be stored
    """
    with open(key_path, "wb") as key_file:
        key_file.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

def save_public_key(public_key: ed25519.Ed25519PublicKey, output_dir: str) -> None:
    """
    Save an Ed25519 public key to the attestation results directory in PEM format.
    
    :param public_key: The Ed25519 public key to save
    :param output_dir: Directory where the public key will be stored
    """
    os.makedirs(output_dir, exist_ok=True)
    public_key_path = os.path.join(output_dir, "signing_key.pub.pem")
    
    with open(public_key_path, "wb") as pub_key_file:
        pub_key_file.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

def get_signing_key(key_path: str = SIGNING_KEY_PATH) -> ed25519.Ed25519PrivateKey:
    """
    Retrieve or generate an Ed25519 private key.
    If a new key pair is generated, the public key is saved to the attestation results directory.

    :param key_path: Path where the private key is stored or will be generated.
    :return: An Ed25519PrivateKey instance.
    """
    if os.path.exists(key_path):
        try:
            with open(key_path, "rb") as key_file:
                key = serialization.load_pem_private_key(key_file.read(), password=None)
                if not isinstance(key, ed25519.Ed25519PrivateKey):
                    raise AttestationDaemonError("Loaded key is not an Ed25519 private key.")
                return key
        except (ValueError, InvalidKey) as exc:
            raise AttestationDaemonError(f"Failed to load existing private key: {exc}") from exc
    else:
        # Generate new key pair if none exists
        private_key = ed25519.Ed25519PrivateKey.generate()
        
        # Save both private and public keys
        save_private_key(private_key, key_path)
        save_public_key(private_key.public_key(), OUTPUT_BASE_DIR)
        
        return private_key


###############################################################################
# SOCKET HANDLING
###############################################################################

def recvall(sock: socket.socket, count: int) -> bytes:
    """
    Receive exactly 'count' bytes from the socket.

    :param sock: The socket to receive from.
    :param count: The exact number of bytes to read.
    :returns: The bytes read.
    :raises RuntimeError: If the socket closes prematurely.
    """
    buf = b""
    while len(buf) < count:
        chunk = sock.recv(count - len(buf))
        if not chunk:
            raise RuntimeError("Socket connection closed prematurely.")
        buf += chunk
    return buf


###############################################################################
# FILE CONTAINER
###############################################################################

class FileContainer(Sequence):
    _fields = [
        ('filename', UTF8String),
        ('data', OctetString)
    ]

# Encoding
def create_file_container(filename: str, data: bytes) -> bytes:
    container = FileContainer({
        'filename': filename,
        'data': data
    })
    return container.dump()

# Decoding
def parse_file_container(der_bytes: bytes) -> tuple[str, bytes]:
    container = FileContainer.load(der_bytes)
    return (
        container['filename'].native,
        container['data'].native
    )


###############################################################################
# FILE HANDLING
###############################################################################

def handle_file_data(
    conn: socket.socket,
    output_base_dir: str,
    signing_key: ed25519.Ed25519PrivateKey
) -> None:
    """
    Receive DER-encoded file data, save it to a timestamped directory,
    compute its hash, and sign it using the provided Ed25519 private key.
    """
    # First read the total length (4 bytes)
    length_bytes = recvall(conn, 4)
    total_length = struct.unpack("!I", length_bytes)[0]
    
    # Read the DER-encoded data
    der_data = recvall(conn, total_length)
    
    # Parse the DER container
    filename, file_data = parse_file_container(der_data)

    timestamp = str(int(time.time()))
    output_dir = os.path.join(output_base_dir, timestamp)
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_dir, filename)
    with open(file_path, "wb") as f:
        f.write(file_data)

    print(f"Received file: {filename} ({len(file_data)} bytes) -> {file_path}")

    # Compute SHA-256 hash (for logging/debugging)
    file_hash = hashlib.sha256(file_data).hexdigest()
    print("SHA256:", file_hash)

    # Sign the file
    signature = signing_key.sign(file_data)
    signature_b64 = base64.b64encode(signature)

    signature_path = file_path + ".sig"
    with open(signature_path, "wb") as sig_file:
        sig_file.write(signature_b64)

    print("Signature written to:", signature_path)


def handle_connection(
    conn: socket.socket,
    output_base_dir: str,
    signing_key: ed25519.Ed25519PrivateKey
) -> None:
    """
    Handle each client connection: parse header, receive file, sign.

    :param conn: Connected socket from accept().
    :param output_base_dir: Base directory for output.
    :param signing_key: Ed25519 private key used to sign the file data.
    """
    try:
        handle_file_data(conn, output_base_dir, signing_key)
    except AttestationDaemonError as exc:
        print(f"[Error] Protocol error: {exc}")
    except Exception as exc:
        print(f"[Error] Unexpected error while handling connection: {exc}")
    finally:
        conn.close()


def run_server(
    socket_path: str = SOCKET_PATH,
    output_base_dir: str = OUTPUT_BASE_DIR
) -> None:
    """
    Main loop: create a server socket, accept connections,
    and process them using handle_connection.

    :param socket_path: Path for the Unix domain socket.
    :param output_base_dir: Base directory to store files and signatures.
    """
    # Remove any stale socket
    if os.path.exists(socket_path):
        os.remove(socket_path)

    signing_key = get_signing_key()

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socket_path)
    server.listen(5)
    print(f"Listening on {socket_path}")

    try:
        while True:
            conn, _ = server.accept()
            print("Accepted connection.")
            handle_connection(conn, output_base_dir, signing_key)
    except KeyboardInterrupt:
        print("Shutting down server.")
    finally:
        server.close()
        if os.path.exists(socket_path):
            os.remove(socket_path)


def main() -> None:
    """
    Entry point. Runs the server loop.
    """
    run_server()


if __name__ == "__main__":
    main()
