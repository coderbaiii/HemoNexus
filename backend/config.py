"""
Bridge module for backend.config delegating to root config.py.
"""
from config import Config, TestConfig

__all__ = ["Config", "TestConfig"]
