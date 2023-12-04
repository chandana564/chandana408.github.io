import pyotp
from app.models import User
from app import db


def generate_otp(user):
    otp_secret = pyotp.random_base32()
    user.otp_secret = otp_secret
    db.session.commit()
    return otp_secret


def verify_otp(user, otp):
    totp = pyotp.TOTP(user.otp_secret)
    return totp.verify(otp)
