import argparse
import getpass

from app.users import ROLES, create_user


def main():
    parser = argparse.ArgumentParser(description="Create a user account")
    parser.add_argument("username")
    parser.add_argument("--role", choices=ROLES, default="employee")
    parser.add_argument("--department", default="General")
    args = parser.parse_args()

    # getpass hides what you type and keeps the password out of your shell history.
    password = getpass.getpass("Password (min 8 characters): ")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match")
    try:
        create_user(args.username, password, args.role, args.department)
    except ValueError as e:
        raise SystemExit(f"Error: {e}")
    print(f"Created {args.username} ({args.role}, {args.department})")


if __name__ == "__main__":
    main()
