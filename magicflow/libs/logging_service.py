import logging
import sys
from typing import Dict
from magicflow.config.config import settings

class LoggingService:
    _instance = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggingService, cls).__new__(cls)
            cls._instance._setup_logging()
        return cls._instance
    
    def _setup_logging(self):
        """Initialize logging configuration once"""
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        # Set base log level from settings or environment
        self.base_log_level = getattr(settings, 'log_level', 'INFO').upper()
        
        # Create root logger
        root_logger = logging.getLogger('app')
        root_logger.setLevel(self.base_log_level)
        root_logger.addHandler(console_handler)
        
        self._loggers['root'] = root_logger
    
    def getLogger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name"""
        if name not in self._loggers:
            logger = logging.getLogger(f'app.{name}')
            logger.setLevel(self.base_log_level)
            # Don't add handlers - they will be inherited from root logger
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def setLevel(self, level: str):
        """Set log level for all loggers"""
        level = level.upper()
        self.base_log_level = level
        for logger in self._loggers.values():
            logger.setLevel(level)
