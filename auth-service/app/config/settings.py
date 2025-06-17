
import os

class Config:
    """Base configuration class"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-key-change-in-production')
    MONGO_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/auth_db')
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 15))
    TOKEN_EXPIRE_HOURS = int(os.environ.get('TOKEN_EXPIRE_HOURS', 24))
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    MONGO_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/auth_test_db')
    
class ProductionConfig(Config):
    """Production configuration"""
    # Production config should use secure values from environment variables
    pass

# Select config based on environment
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

# Default config to use
Config = config_by_name[os.environ.get('FLASK_ENV', 'development')]