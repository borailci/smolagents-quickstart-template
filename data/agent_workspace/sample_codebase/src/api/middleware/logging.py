"""
Logging middleware
"""

import logging
import os
from flask import request


def setup_logging(app):
    """Configure application logging"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Set up file handler
    file_handler = logging.FileHandler('logs/taskflow.log')
    file_handler.setLevel(logging.INFO)

    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)

    # Log startup
    app.logger.info('TaskFlow application started')

    @app.before_request
    def log_request():
        """Log incoming requests"""
        app.logger.info(
            f'{request.method} {request.path} from {request.remote_addr}'
        )

    @app.after_request
    def log_response(response):
        """Log outgoing responses"""
        app.logger.info(
            f'{request.method} {request.path} - {response.status_code}'
        )
        return response


def get_logger(name):
    """Get a logger instance"""
    return logging.getLogger(name)
