"""HermitAgent channel interfaces — CLI / Telegram / HTTP."""
from .base import ChannelInterface
from .cli import CLIChannel
from .http import HTTPChannel
from .telegram import TelegramChannel

__all__ = ["ChannelInterface", "CLIChannel", "HTTPChannel", "TelegramChannel"]
