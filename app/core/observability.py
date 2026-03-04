import os
import logging
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

logger = logging.getLogger(__name__)


def setup_langfuse() -> None:
    """Initialize Langfuse client. Expected to be called during app startup."""
    try:
        # Initialize Langfuse client instance (singleton)
        Langfuse(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3001"),
        )
        logger.info("Langfuse observability client initialized.")
    except Exception as e:
        logger.warning(f"Langfuse observability client failed to initialize: {e}")


def get_langfuse_handler() -> CallbackHandler | None:
    """Return a configured Langfuse Callback Handler from the singleton if available."""
    try:
        return CallbackHandler()
    except Exception as e:
        logger.warning(f"Failed to fetch Langfuse handler: {e}")
        return None
