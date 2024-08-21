import secrets

# Generate a 32-byte random secret key
SECRET = secrets.token_urlsafe(32)

print("Secret key:",SECRET)
