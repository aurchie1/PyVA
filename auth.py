# -*- coding: utf-8 -*-
"""
auth.py
Password hashing utilities using bcrypt.

Install first:
    pip install bcrypt

Why bcrypt?
- It generates a random salt automatically for every call to hashpw().
- The salt is embedded directly inside the returned hash string, so you
  never need to store it in a separate column.
- It's deliberately slow (adjustable "cost factor"), which makes brute-force
  attacks much harder compared to fast hashes like plain SHA-256.
"""

import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password for storage in the database.

    Returns a string safe to store directly in the `password_hash` column.
    (bcrypt encodes the salt + cost factor + hash all in one string.)
    """
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()  # generates a new random salt each call
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")  # store as text in SQLite


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Check a plaintext password attempt against the stored hash.

    Returns True if it matches, False otherwise.
    """
    password_bytes = plain_password.encode("utf-8")
    hash_bytes = stored_hash.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)


# ---------------------------------------------------------
# Quick demo / manual test
# ---------------------------------------------------------
if __name__ == "__main__":
    pw = "correct horse battery staple"

    hashed = hash_password(pw)
    print("Stored hash:", hashed)

    print("Correct password check:", verify_password(pw, hashed))       # True
    print("Wrong password check:  ", verify_password("wrong", hashed))  # False

    # Notice: hashing the same password twice gives DIFFERENT hashes,
    # because bcrypt uses a different random salt each time.
    print("Second hash of same pw:", hash_password(pw))
