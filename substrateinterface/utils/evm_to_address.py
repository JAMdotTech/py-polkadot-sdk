import hashlib
import base58

def blake2b_256(data):
    """
    Compute the Blake2b-256 hash of the given data.
    """
    return hashlib.blake2b(data, digest_size=32).digest()

def u8a_concat(*args):
    """
    Concatenate multiple byte arrays into one.
    """
    return b"".join(args)

def hasher(hash_type, data):
    """
    Hash the data using the specified hash type.
    Args:
        hash_type (str): The hash algorithm to use ('blake2' or 'keccak').
        data (bytes): The data to hash.
    Returns:
        bytes: The hashed data.
    """
    if hash_type == "keccak":
        return hashlib.new("keccak256", data).digest()
    elif hash_type == "blake2":
        return blake2b_256(data)
    else:
        raise ValueError(f"Unsupported hash type: {hash_type}")

def encode_address(public_key, ss58_format):
    """
    Encode a public key into SS58 format.
    Args:
        public_key (bytes): The public key or hashed address.
        ss58_format (int): The SS58 prefix (e.g., 42 for testnet).
    Returns:
        str: The SS58 address.
    """
    # SS58 prefix
    ss58_prefix = b"SS58PRE"
    # Concatenate the format byte with the public key
    payload = bytes([ss58_format]) + public_key
    # Compute the checksum
    checksum = hashlib.blake2b(ss58_prefix + payload, digest_size=64).digest()[:2]
    # Concatenate the payload and checksum
    full_payload = payload + checksum
    # Encode the result into Base58
    return base58.b58encode(full_payload).decode("utf-8")

def evm_to_address(evm_address, ss58_format=42, hash_type="blake2"):
    """
    Converts an EVM address to its corresponding SS58 address.
    Args:
        evm_address (str | bytes): The EVM address (20 bytes).
        ss58_format (int): The SS58 prefix (default is 42 for testnet).
        hash_type (str): The hash algorithm to use ('blake2' or 'keccak').
    Returns:
        str: The SS58 address.
    """
    if isinstance(evm_address, str):
        # Remove the '0x' prefix if present and convert to bytes
        if evm_address.startswith("0x"):
            evm_address = bytes.fromhex(evm_address[2:])
        else:
            evm_address = bytes.fromhex(evm_address)

    # Ensure the length of the address is 20 bytes
    if len(evm_address) != 20:
        raise ValueError(f"Invalid EVM address length: {len(evm_address)}")

    # Concatenate "evm:" with the address
    message = u8a_concat(b"evm:", evm_address)

    # Hash the concatenated message
    hashed_message = hasher(hash_type, message)

    # Encode the hashed message as an SS58 address
    return encode_address(hashed_message, ss58_format)