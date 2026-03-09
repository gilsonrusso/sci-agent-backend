import os
import logging
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from app.core.config import settings

# Set environment variables for Langfuse SDK to pick up automatically
# (This is needed because CallbackHandler is often initialized at module import time)
if settings.LANGFUSE_PUBLIC_KEY:
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
if settings.LANGFUSE_SECRET_KEY:
    os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
if settings.LANGFUSE_HOST:
    os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST

# Initialize Langfuse client instance (singleton) at module level
# to ensure it's available for decorators and CallbackHandlers initialized at import time
try:
    Langfuse(
        secret_key=settings.LANGFUSE_SECRET_KEY,
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        host=settings.LANGFUSE_HOST,
    )
except Exception as e:
    # We'll log this in setup_langfuse or just let it be
    pass

logger = logging.getLogger(__name__)


def setup_langfuse() -> None:
    """Initialize Langfuse client. Expected to be called during app startup."""
    logger.info("Langfuse observability client initialization check.")


def get_langfuse_handler() -> CallbackHandler | None:
    """Return a configured Langfuse Callback Handler from the singleton if available."""
    try:
        return CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
        )
    except Exception as e:
        logger.warning(f"Failed to fetch Langfuse handler: {e}")
        return None


def teardown_langfuse() -> None:
    """Clean up Langfuse client if needed."""
    pass
