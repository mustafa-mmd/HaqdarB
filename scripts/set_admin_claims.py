# scripts/set_admin_claims.py
"""
HaqDar AI — Set Firebase Custom Claims for Admins
Usage: python scripts/set_admin_claims.py <uid_or_email>
"""
import sys
import os
import firebase_admin
from firebase_admin import credentials, auth

# Load service account key
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "haqdar-key.json")

if not os.path.exists(SERVICE_ACCOUNT_PATH):
    print(f"❌ Error: Service account key not found at '{SERVICE_ACCOUNT_PATH}'")
    sys.exit(1)

try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"❌ Error initializing Firebase Admin: {e}")
    sys.exit(1)

def set_claims(uid_or_email):
    # Try finding by email first, otherwise assume it is a UID
    user = None
    if "@" in uid_or_email:
        try:
            user = auth.get_user_by_email(uid_or_email)
            print(f"Found user by email: {user.email} (UID: {user.uid})")
        except auth.UserNotFoundError:
            print(f"❌ Error: No user found with email '{uid_or_email}'")
            return
        except Exception as e:
            print(f"❌ Error searching user by email: {e}")
            return
    else:
        try:
            user = auth.get_user(uid_or_email)
            print(f"Found user by UID: {user.uid} (Email: {user.email})")
        except auth.UserNotFoundError:
            print(f"❌ Error: No user found with UID '{uid_or_email}'")
            return
        except Exception as e:
            print(f"❌ Error searching user by UID: {e}")
            return

    try:
        # Set claims
        auth.set_custom_user_claims(user.uid, {"admin": True})
        
        # Verify it was set
        updated_user = auth.get_user(user.uid)
        print(f"Custom claims after update: {updated_user.custom_claims}")
        
        if updated_user.custom_claims and updated_user.custom_claims.get("admin") is True:
            print(f"✅ Success! Admin privilege granted to {user.email or user.uid}")
        else:
            print(f"❌ Error: Claims were updated but verification failed.")
    except Exception as e:
        print(f"❌ Error setting claims: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/set_admin_claims.py <uid_or_email>")
        print("Example: python scripts/set_admin_claims.py admin@haqdar.com")
        sys.exit(1)
        
    set_claims(sys.argv[1])
