import pytz

class Config(object):
    SECRET_KEY = 'secret_key'
    JWT_SECRET_KEY = 'jwt_secret_key'
    WTF_CSRF_CHECK_DEFAULT = False
    # CORS_SUPPORTS_CREDENTIALS=True
    TEMPLATES_PATH = "../templates/"
    MANTENIMIENTO = False
    TZ_INFO = pytz.timezone('America/Caracas')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProductionConfig(Config):
    DEBUG=False
    SECRET_KEY = 'multiventas_vip_secret_key'
    JWT_SECRET_KEY = 'multiventas_vip_jwt_secret_key'
    MYSQL_HOST="localhost"
    MYSQL_USER="kabk53nb_mpvipu"
    MYSQL_PASSWORD="x0eF5%hxvCYT_Np*6Ls?rU1N"
    MYSQL_DB="kabk53nb_mpvip"
    SQLALCHEMY_DATABASE_URI  = f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"

class DevelopmentConfig(Config):
    DEBUG=True
    MYSQL_HOST=""
    MYSQL_USER="root"
    MYSQL_PASSWORD=""
    MYSQL_DB="streaming_system"
    SQLALCHEMY_DATABASE_URI  = f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"