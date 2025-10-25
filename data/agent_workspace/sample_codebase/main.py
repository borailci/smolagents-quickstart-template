"""
TaskFlow - Task Management Application Entry Point
"""

import os
from dotenv import load_dotenv
from flask import Flask, jsonify
from src.api.routes import api_bp
from src.models.database import init_db
from src.api.middleware.logging import setup_logging

# Load environment variables
load_dotenv()

# Initialize app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Setup logging
setup_logging(app)

# Initialize database
try:
    init_db(app)
except Exception as e:
    print(f"Warning: Database initialization skipped - {e}")

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'taskflow',
        'version': '0.1.0'
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'code': 'NOT_FOUND',
        'status': 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR',
        'status': 500
    }), 500


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
