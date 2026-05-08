import re


# Validation regex patterns
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
# Password: at least 6 chars, 1 uppercase, 1 lowercase, 1 digit
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{6,}$")


class ValidationError(Exception):
    """Custom exception for validation errors"""

    def __init__(self, field, message):
        self.field = field
        self.message = message
        super().__init__(self.message)


def validate_username(username):
    """
    Validate username format and length

    Rules:
    - 3-20 characters
    - Only alphanumeric, underscore, and hyphen
    - No spaces or special characters

    Args:
        username (str): Username to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    # Minimal validation for signup/signin: only require a non-empty username.
    # (We intentionally do NOT enforce regex/length constraints here.)
    if username is None:
        return False, "Username is required"

    username = str(username).strip()
    if not username:
        return False, "Username is required"

    return True, None


def validate_email(email):
    """
    Validate email format

    Rules:
    - Must follow standard email format
    - Valid domain with at least 2 chars TLD

    Args:
        email (str): Email to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"

    email = email.strip().lower()

    if len(email) > 254:  # RFC 5321
        return False, "Email is too long"

    if not EMAIL_PATTERN.match(email):
        return False, "Invalid email format"

    return True, None


def validate_password(password):
    """
    Validate password strength

    Rules:
    - At least 6 characters
    - Contains at least 1 uppercase letter
    - Contains at least 1 lowercase letter
    - Contains at least 1 digit

    Args:
        password (str): Password to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 6:
        return False, "Password must be at least 6 characters"

    if len(password) > 128:
        return False, "Password is too long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least 1 uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least 1 lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least 1 number"

    return True, None


def validate_full_name(full_name):
    """
    Validate full name format

    Rules:
    - Optional field
    - 2-100 characters if provided
    - Only letters, spaces, hyphens, and apostrophes

    Args:
        full_name (str): Full name to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not full_name:
        return True, None  # Optional field

    full_name = full_name.strip()

    if len(full_name) < 2:
        return False, "Full name must be at least 2 characters"

    if len(full_name) > 100:
        return False, "Full name must not exceed 100 characters"

    # Allow letters, spaces, hyphens, apostrophes, and common international characters
    if not re.match(
        r"^[a-zA-Z\s\-'àáâãäåèéêëìíîïòóôõöùúûüýÿ]+$", full_name, re.IGNORECASE
    ):
        return False, "Full name contains invalid characters"

    return True, None


def validate_signup_data(username, password):
    """Validate signup data.

    Per requirement, signup should not require email and should not enforce
    strict username/password strength constraints.

    Returns:
        tuple: (is_valid, dict of errors)
    """
    errors = {}

    # Validate username
    is_valid, error = validate_username(username)
    if not is_valid:
        errors["username"] = error

    # Password: only require non-empty (no strength rules).
    if password is None or password == "":
        errors["password"] = "Password is required"

    return len(errors) == 0, errors


def validate_signin_data(username, password):
    """
    Validate signin data

    Args:
        username_or_email (str): Username or email
        password (str): Password

    Returns:
        tuple: (is_valid, dict of errors)
    """
    errors = {}

    # Validate username
    is_valid, error = validate_username(username)
    if not is_valid:
        errors["username"] = error

    # Password: only require non-empty (no strength rules).
    if password is None or password == "":
        errors["password"] = "Password is required"

    return len(errors) == 0, errors


def validate_password_confirmation(password, confirm_password):
    """
    Validate that password and confirm password match

    Args:
        password (str): Password
        confirm_password (str): Confirm password

    Returns:
        tuple: (is_valid, error_message)
    """
    if password != confirm_password:
        return False, "Passwords do not match"
    return True, None


def validate_change_password_data(old_password, new_password, confirm_password):
    errors = {}

    if not old_password:
        errors["old_password"] = "Old password is required"

    is_valid, error = validate_password(new_password)
    if not is_valid:
        errors["new_password"] = error

    is_valid, error = validate_password_confirmation(new_password, confirm_password)
    if not is_valid:
        errors["confirm_password"] = error

    return len(errors) == 0, errors
