import uuid
import string
import random

def generate_manual_code(length=6):
    """Generate a random 6-character alphanumeric code."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))