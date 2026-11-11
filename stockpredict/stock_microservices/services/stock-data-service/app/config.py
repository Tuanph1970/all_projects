"""
Stock Data Service Configuration
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Service configuration from environment variables"""

    # Service Identity
    SERVICE_NAME: str = "stock-data-service"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "stock_helper"

    # Backlog #87 — how much history an ingest pulls.
    #
    # This was hardcoded at 5 years, inherited from the monolith's
    # DEFAULT_YEARS_HISTORY, and the vendor is not the constraint: VCI returns
    # FPT from 2009-03-27 (4,380 bars) and VNINDEX from 2008-02-18 (4,641).
    #
    # The depth matters beyond tidiness. EM-4's test of E&M's claim that
    # "all major stock market Bottoms have corresponded with extremely low MEI
    # readings" came back n=2 at the 60-session horizon, because 5.3 years of
    # VN data contains exactly ONE bear market where E&M spoke of 20 years.
    # The claim was untestable for want of history, not refuted.
    HISTORY_YEARS: int = 5

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Database
    DATABASE_HOST: str = "mysql"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = "Mysql_2025"
    DATABASE_NAME: str = "stockdata_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "stockuser"
    RABBITMQ_PASSWORD: str = "stockpass"
    RABBITMQ_VHOST: str = "/stock"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL: int = 300  # 5 minutes default cache

    # JWT — shared secret with auth-service for validating bearer tokens.
    # Currently only used to gate admin endpoints (/companies/sync,
    # /priceboards/refresh). SECURITY_AUDIT.md HIGH #4.
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # VNStock Configuration
    VNSTOCK_DATA_SOURCE: str = "VCI"
    # vnstock 4.x (via its `vnai` dependency) enforces a client-side quota:
    # Guest = 20 req/min, free Community key = 60 req/min. vnai reads the key
    # from the VNSTOCK_API_KEY env var itself; we only use it to pick a default
    # spacing between calls. Get a key at https://vnstocks.com/login
    VNSTOCK_API_KEY: Optional[str] = None
    # Calls per minute the tier allows. 20 guest / 60 with a Community key.
    VNSTOCK_GUEST_RATE_PER_MIN: int = 20
    VNSTOCK_KEYED_RATE_PER_MIN: int = 60

    # Fraction of that budget we actually aim at (Backlog #134).
    #
    # THE OLD DEFAULT TARGETED 95% OF A HARD CAP AND HAD NO MARGIN. With a key
    # the interval was 1.05s = 57.1 calls/min against a 60/min limit, and a
    # 61-symbol backfill lost 6 requests to it. 95% leaves nothing for the three
    # things that always happen: jitter between the sleep and the call, a second
    # caller inside this process (a user request landing mid-sync), and — the one
    # a per-process interval CANNOT control — another machine using the SAME
    # key, because with a key present vnai enforces the quota SERVER-SIDE per
    # key (`vnai/beam/quota.py::verify` -> `qm.check_quota(api_key)`), not per
    # process. A local interval can only lower our share of a shared budget; it
    # can never guarantee it.
    VNSTOCK_QUOTA_SAFETY: float = 0.7

    # Minimum seconds between two vnstock calls. None = derive from the tier
    # and the safety fraction above.
    VNSTOCK_MIN_INTERVAL_SECONDS: Optional[float] = None
    # On RateLimitExceeded, sleep for vnai's retry_after and try again.
    VNSTOCK_RATE_LIMIT_RETRY: bool = True
    VNSTOCK_RATE_LIMIT_MAX_WAIT_SECONDS: float = 90.0
    # Attempts after the first. One was not enough: vnai has already retried
    # twice internally before it raises, so by the time we see RateLimitExceeded
    # the budget has been exhausted for seconds, and when the key is shared it
    # can stay exhausted for the rest of the minute.
    VNSTOCK_RATE_LIMIT_MAX_RETRIES: int = 3

    # Adaptive pacing (Backlog #134, second pass).
    #
    # A FIXED SAFETY FRACTION CANNOT SOLVE A SHARED BUDGET, which is what this
    # key has. Measured 2026-11-10: pacing at 42 calls/min — 70% of the 60/min
    # tier — a 38-request burst still came back "Đã sử dụng: 60/60". Only this
    # container holds the key on this machine and only it imports vnstock, so
    # the other ~20 calls/min came from somewhere we do not control (the key is
    # also in use on the production host). Any fraction we pick here is a guess
    # at a stranger's share, and it will be wrong again the moment that share
    # moves.
    #
    # So the interval reacts instead of predicting: multiply it on a rate limit,
    # decay it back on success. Classic multiplicative-decrease / additive-
    # recovery, which converges on whatever share is actually available without
    # anyone having to know what it is.
    VNSTOCK_ADAPTIVE_PACING: bool = True
    VNSTOCK_BACKOFF_FACTOR: float = 2.0
    VNSTOCK_MAX_INTERVAL_MULTIPLIER: float = 8.0
    #: Per successful call. 0.98 ** 35 ~ 0.5, so a doubled interval halves back
    #: over roughly 35 clean calls — fast enough to recover within a nightly
    #: sync, slow enough not to re-provoke the limit immediately.
    VNSTOCK_RECOVERY_FACTOR: float = 0.98

    # ── TCBS OpenAPI (Backlog #142, option (a)) ───────────────────────────
    #
    # Staged ahead of the adapter so the auth questions can be answered against
    # a real key. NOTHING READS THIS YET beyond the probe — setting it changes
    # no behaviour, which is deliberate: the vnstock path keeps running until
    # the adapter replaces it endpoint by endpoint.
    #
    # Named TCBS_, not TCB_: `tcb_*` in news-service means the Techcombank
    # research EMAIL (tcb_news, tcb_routes), which is a different source with a
    # different shape. Keeping the broker API distinguishable from the mail
    # feed matters once both are live.
    TCBS_API_KEY: str = ""
    TCBS_BASE_URL: str = "https://openapi.tcbs.com.vn"

    #: The JWT from /gaia/v1/oauth2/openapi/token is valid for AT MOST 8 HOURS
    #: ("Token có hiệu lực tối đa 8 giờ", developers.tcbs.com.vn). Refreshing
    #: needs a Smart OTP from the TCInvest app, so whether an unattended nightly
    #: job is possible at all turns on whether that OTP can be avoided on
    #: refresh — unresolved, and the first thing to settle before endpoint work.
    TCBS_TOKEN_TTL_SECONDS: float = 8 * 3600

    # ── StockComponents reuse (Backlog #144) ──────────────────────────────
    #: How long a cached `StockComponents` stays usable, in seconds.
    #:
    #: NOT just a cache-size knob — it bounds STALENESS, and there is something
    #: real to go stale. Building one runs `Finance._handshake()`, which GETs
    #: trading.vietcap.com.vn/priceboard and copies the session COOKIES into the
    #: instance headers. Cookies expire, so an entry kept indefinitely would
    #: eventually carry dead ones and fail every financial read for that symbol
    #: until the process restarted. The handshake also swallows its own
    #: exception, so a failed one yields a component with no cookies at all —
    #: this TTL is what stops either state from being permanent.
    #:
    #: 15 minutes keeps the win that matters (one handshake per symbol per
    #: quarter-hour instead of one per call site invocation) while capping how
    #: long a bad entry can sit there. 0 disables reuse entirely.
    VNSTOCK_COMPONENTS_TTL_SECONDS: float = 900.0

    @field_validator("VNSTOCK_API_KEY", "VNSTOCK_MIN_INTERVAL_SECONDS", mode="before")
    @classmethod
    def _blank_env_is_unset(cls, v):
        """docker-compose passes `${VAR:-}` through as "" — treat as None."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @property
    def vnstock_rate_per_min(self) -> int:
        """The tier's per-minute budget, named rather than implied."""
        return (self.VNSTOCK_KEYED_RATE_PER_MIN if self.VNSTOCK_API_KEY
                else self.VNSTOCK_GUEST_RATE_PER_MIN)

    @property
    def vnstock_min_interval(self) -> float:
        """Seconds between calls = 60 / (budget x safety).

        An explicit VNSTOCK_MIN_INTERVAL_SECONDS still wins, so an operator who
        knows the key is theirs alone can turn the margin back down.
        """
        if self.VNSTOCK_MIN_INTERVAL_SECONDS is not None:
            return self.VNSTOCK_MIN_INTERVAL_SECONDS
        safety = min(max(self.VNSTOCK_QUOTA_SAFETY, 0.05), 1.0)
        return 60.0 / max(1.0, self.vnstock_rate_per_min * safety)

    # Company data sync
    COMPANY_SYNC_STALE_DAYS: int = 7

    # Backlog #114 follow-up — the nightly all-symbols price top-up.
    # On by default because it REPLACES work rather than adding it: without it
    # the first reader of each stale symbol pays the vendor call during the
    # trading day, which is exactly when quota is most contended. Measured
    # 2026-11-02: 30 of 32 stored symbols were three sessions behind.
    ENABLE_DAILY_PRICE_REFRESH: bool = True
    # A ceiling on vendor calls per nightly run, so a universe that grows to
    # thousands cannot turn a top-up into an all-night job. Symbols are taken
    # stalest-first, and whatever is left over is picked up the next night (or
    # on read, which still works).
    PRICE_REFRESH_MAX_SYMBOLS: int = 200
    # Spacing between symbols, on top of vnstock_call's own quota pacing.
    PRICE_REFRESH_PAUSE_SECONDS: float = 2.0

    # Backlog #119 — nightly sweep for price seams (overnight moves no VN board
    # permits, left behind when the provider restates history and our
    # incremental top-up only appends).
    #
    # SCANNING IS FREE. Detection reads stored closes and costs no vendor call,
    # so sweeping the whole universe every night spends nothing in the normal
    # case — which is every night, since only four seams existed across five
    # years. Only an actual repair costs a call, and only for the one symbol.
    ENABLE_NIGHTLY_SEAM_SCAN: bool = True
    # A hard cap on repairs per run. A repair re-pulls a symbol's ENTIRE
    # history (~1,400 bars), so without this a bad night across many symbols
    # could eat the daily quota that the price refresh needs.
    SEAM_SCAN_MAX_REPAIRS: int = 3
    # Only seams whose date falls within this window are auto-repaired.
    #
    # THIS IS THE LOOP GUARD, and it is the whole reason the sweep is safe to
    # run unattended. A seam appears when the provider restates history at a
    # corporate action, and re-pulling fixes it. But if a seam is GENUINE —
    # the provider itself never adjusted — a re-pull changes nothing, and a
    # scan with no memory would re-pull that symbol every single night for
    # ever. Bounding by the seam's own date makes the sweep self-limiting with
    # no state to persist: a fresh seam gets one repair attempt, and one that
    # has survived long enough to fall outside the window is left alone.
    # Known limitation: on a brand-new deployment an OLD seam is therefore
    # never auto-repaired. That is deliberate — POST
    # /stocks/{symbol}/repair-history covers it, and #118's narrator keeps
    # warning about it meanwhile.
    SEAM_SCAN_RECENT_DAYS: int = 30

    # Backlog #48 — during trading hours a price board row older than this is
    # refetched on read (one Vietcap POST; not vnstock, so no quota cost).
    PRICE_BOARD_MAX_AGE_SECONDS: int = 60

    # Tracing
    TRACING_ENABLED: bool = True
    TRACING_JAEGER_HOST: str = "jaeger"
    TRACING_JAEGER_PORT: int = 6831
    TRACING_SAMPLE_RATE: float = 1.0

    @property
    def database_url(self) -> str:
        """Async database URL"""
        return (
            f"mysql+asyncmy://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync database URL"""
        return (
            f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def rabbitmq_url(self) -> str:
        """RabbitMQ connection URL"""
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
        )

    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra environment variables


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance, validated against placeholder secrets."""
    from stock_common.secrets_validation import assert_no_placeholder_secrets
    s = Settings()
    assert_no_placeholder_secrets(s, service_name="stock-data-service")
    return s
