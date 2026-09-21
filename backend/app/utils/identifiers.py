import uuid
from datetime import datetime, timezone


def generate_election_id(year: int | None = None, sequence: int = 1) -> str:
    """
    Generate a deterministic election ID in format EV-YYYY-NNN.

    Args:
        year: Election year. Defaults to current year.
        sequence: Sequence number within the year.

    Returns:
        Election ID string, e.g., 'EV-2026-001'
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    return f"EV-{year:04d}-{sequence:03d}"


def generate_candidate_id(index: int) -> str:
    """
    Generate a deterministic candidate ID in format CNNN.

    Args:
        index: 1-based candidate index.

    Returns:
        Candidate ID string, e.g., 'C001'
    """
    return f"C{index:03d}"


def generate_device_id(index: int) -> str:
    """
    Generate a deterministic device ID in format EVM-NNN.

    Args:
        index: 1-based device index.

    Returns:
        Device ID string, e.g., 'EVM-001'
    """
    return f"EVM-{index:03d}"


def generate_session_token() -> str:
    """
    Generate a unique session token.

    This is a simulated session credential — not a real voter
    authentication mechanism. In a production system, session tokens
    would be bound to verified voter credentials.
    """
    return uuid.uuid4().hex


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())
