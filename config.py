"""
Bridge module for root config delegating to backend.config.
"""
from backend.config import Config, TestConfig

__all__ = ["Config", "TestConfig"]
