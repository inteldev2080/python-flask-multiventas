from flask import Flask
from libs.config import DevelopmentConfig, ProductionConfig

def create_app(): 
    # ENVIRONMENT
    environment = "development"
    app = Flask(__name__, static_folder ='static')
    if environment == "production": app.config.from_object(ProductionConfig)
    else:                           app.config.from_object(DevelopmentConfig)

    
    return app, environment