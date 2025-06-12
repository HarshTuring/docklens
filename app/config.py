import os

class Config:
    """Base config."""
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    LOG_DIR = 'logs'
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/image_processing')

class DevelopmentConfig(Config):
    """Development config."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production config."""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing config."""
    DEBUG = True
    TESTING = True
    UPLOAD_FOLDER = 'tests/uploads'
    LOG_DIR = 'tests/logs'

# Configuration dictionary
config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig,
    'test': TestingConfig
}

def get_config():
    env = os.getenv('FLASK_ENV', 'dev')
    return config_by_name[env]