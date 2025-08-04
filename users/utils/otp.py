import pyotp
import time

class OTPManager:
    def __init__(self, secret=None):
        """
        Initialize with an optional secret key.
        If no secret is provided, generate a new base32 secret.
        """
        if secret:
            self.secret = secret
        else:
            self.secret = pyotp.random_base32()
        self.totp = pyotp.TOTP(self.secret, interval=600, digits=5)

    def get_secret(self):
        """
        Return the base32 secret key.
        Save this to verify OTP later.
        """
        return self.secret

    def generate_otp(self):
        """
        Generate a current OTP code.
        """
        return self.totp.now()

    def verify_otp(self, otp_code, valid_window=1):
        """
        Verify the OTP code.
        valid_window: number of 30-sec windows to check before and after current time (default 1)
        Returns True if valid, False otherwise.
        """
        return self.totp.verify(otp_code, valid_window=valid_window)
