from flask import Blueprint
api = Blueprint('api', __name__)

from controller.products import products_bp
from controller.auth import auth_bp
from controller.recharges import recharges_bp
from controller.myProducts  import my_products_bp
from controller.profile  import profile_bp
from controller.seller import seller_bp
from controller.support import support_bp

api.register_blueprint(products_bp, url_prefix='/products')
api.register_blueprint(auth_bp, url_prefix='/auth')
api.register_blueprint(recharges_bp, url_prefix='/recharges')
api.register_blueprint(my_products_bp, url_prefix='/my-products')
api.register_blueprint(profile_bp, url_prefix='/profile')
api.register_blueprint(seller_bp, url_prefix='/seller')
api.register_blueprint(support_bp, url_prefix='/support')