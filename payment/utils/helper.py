import random, time, string


def generate_tx_ref(prefix="TX"):
    timestamp = int(time.time())  # seconds since epoch
    rand_str = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{timestamp}-{rand_str}"

