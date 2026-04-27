"""Cross-broker adapter helpers.

Modules under this package are used by more than one broker adapter. Per
[ADR-034](../../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004)
the rate limiter and credentials loader live here so every broker family
(`blive.adapters.{paper,ig,ib,...}`) can compose them without duplicating.
"""

from blive.adapters.shared.credentials import (
    CredentialField,
    CredentialSchema,
    CredentialsMissing,
    default_secrets_dir,
    load_credentials,
    redaction_keys,
)
from blive.adapters.shared.rate_limiter import (
    BucketMetrics,
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
    UnknownBucket,
)

__all__ = [
    # Rate limiter (ADR-031 + ADR-038)
    "BucketMetrics",
    "RateLimitBucket",
    "RateLimitConfig",
    "TokenBucketRateLimiter",
    "UnknownBucket",
    # Credentials (ADR-035)
    "CredentialField",
    "CredentialSchema",
    "CredentialsMissing",
    "default_secrets_dir",
    "load_credentials",
    "redaction_keys",
]
