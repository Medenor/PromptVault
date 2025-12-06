# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# #!/usr/bin/env python3
"""Promote a user to admin role for testing."""
import sys
sys.path.insert(0, '/Users/raphael/Programmation/PromptVault')

from src.db.session import SessionLocal
from src.db.models.user import User

def promote_user_to_admin(username: str) -> bool:
    """Promote a user to admin role."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' not found")
            return False
        
        user.role = 'admin'
        db.commit()
        print(f"✓ User '{username}' promoted to admin")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python promote_to_admin.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    if promote_user_to_admin(username):
        sys.exit(0)
    else:
        sys.exit(1)
