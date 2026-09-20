"""
SecureVOTE 3.0 — Canonical Cryptographic Test Vectors.

Fixed, deterministic test vectors for cross-platform verification,
independent audits, and regression detection.

Values are generated with fixed seeds / deterministic parameters so
independent implementations (e.g. TypeScript verifier in dashboard)
can assert byte-for-byte agreement.
"""

from app.crypto import PROTOCOL_VERSION
from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    ElGamalCiphertext,
    ElGamalPrivateKey,
    ElGamalPublicKey,
    G,
    point_add,
    scalar_mult,
)

# ---------------------------------------------------------------------------
# Fixed Keypair 1
# ---------------------------------------------------------------------------

# Known scalar: 0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
VECTOR_KEY_1_SCALAR = 0x0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF
_pub1_point = scalar_mult(VECTOR_KEY_1_SCALAR, G)

VECTOR_KEY_1_PUB_X = f"{_pub1_point.x:064x}"
VECTOR_KEY_1_PUB_Y = f"{_pub1_point.y:064x}"

# Public key object
VECTOR_PUBLIC_KEY_1 = ElGamalPublicKey(point=_pub1_point)
VECTOR_PRIVATE_KEY_1 = ElGamalPrivateKey(scalar=VECTOR_KEY_1_SCALAR, public_key=VECTOR_PUBLIC_KEY_1)

# ---------------------------------------------------------------------------
# Fixed Keypair 2 (for cross-key rejection tests)
# ---------------------------------------------------------------------------

VECTOR_KEY_2_SCALAR = 0xFEEDFACEDEADBEEFFEEDFACEDEADBEEFFEEDFACEDEADBEEFFEEDFACEDEADBEEF
_pub2_point = scalar_mult(VECTOR_KEY_2_SCALAR, G)
VECTOR_PUBLIC_KEY_2 = ElGamalPublicKey(point=_pub2_point)
VECTOR_PRIVATE_KEY_2 = ElGamalPrivateKey(scalar=VECTOR_KEY_2_SCALAR, public_key=VECTOR_PUBLIC_KEY_2)

# ---------------------------------------------------------------------------
# Deterministic Encryption Helper (Fixed Nonce)
# ---------------------------------------------------------------------------

def deterministic_encrypt(
    public_key: ElGamalPublicKey,
    message: int,
    nonce: int,
) -> ElGamalCiphertext:
    """Deterministic encryption with a fixed scalar nonce for test vector generation."""
    c1 = scalar_mult(nonce, G)
    r_y = scalar_mult(nonce, public_key.point)
    m_g = scalar_mult(message, G)
    c2 = point_add(r_y, m_g)
    return ElGamalCiphertext(c1=c1, c2=c2)


# ---------------------------------------------------------------------------
# Canonical Ballots with Fixed Nonces
# ---------------------------------------------------------------------------

ELECTION_CANONICAL_ID = "CANONICAL-TEST-ELECTION-2026"
CANDIDATE_IDS = ["CAND-ALPHA", "CAND-BETA", "CAND-GAMMA", "NOTA"]
CANDIDATE_COUNT = 4

# Known nonces for 3 ballots
BALLOT_1_NONCES = [
    0x1000000000000000000000000000000000000000000000000000000000000001,
    0x1000000000000000000000000000000000000000000000000000000000000002,
    0x1000000000000000000000000000000000000000000000000000000000000003,
    0x1000000000000000000000000000000000000000000000000000000000000004,
]

BALLOT_2_NONCES = [
    0x2000000000000000000000000000000000000000000000000000000000000001,
    0x2000000000000000000000000000000000000000000000000000000000000002,
    0x2000000000000000000000000000000000000000000000000000000000000003,
    0x2000000000000000000000000000000000000000000000000000000000000004,
]

BALLOT_3_NONCES = [
    0x3000000000000000000000000000000000000000000000000000000000000001,
    0x3000000000000000000000000000000000000000000000000000000000000002,
    0x3000000000000000000000000000000000000000000000000000000000000003,
    0x3000000000000000000000000000000000000000000000000000000000000004,
]
