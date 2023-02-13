from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from main import db, ErrorResponse, SuccessResponse
from models.models import StreamingAccount, Platform, Config, dateV

# BLUEPRINTS
seller_bp = Blueprint('seller_bp', __name__)

def afiliation_final_price(config = None):
    from flask import g
    if not config:
        config = Config.query.filter_by(name="afiliation").first()
    return round(float(config.options["price"])  * g.get_dollar(), 2)

@seller_bp.route("/")
@jwt_required()
def index():
    platform_prices = db.session.query( Platform.name, db.func.max(StreamingAccount.price).label("price"), db.func.max(StreamingAccount.afiliated_price).label("afiliated_price"), db.func.max(StreamingAccount.reference_reward).label("reference_reward") ).\
                        select_from(StreamingAccount).\
                        join(Platform, Platform.id == StreamingAccount.select_platform).\
                        where( db.text("DATEDIFF(end_date, start_date) >28 AND streaming_account.id IN (SELECT screen.account_id FROM screen)") ).\
                        group_by(Platform.name).all()
    config = Config.query.filter_by(name="afiliation").first()

    afiliation = current_user.afiliation()
    is_afiliated = afiliation.status == 1 if afiliation else False
    time = " - " if not afiliation else f"Inicio: {afiliation.start_date.strftime('%d-%m-%Y')} - Fin: {afiliation.end_date.strftime('%d-%m-%Y')}"

    return jsonify({
        "is_afiliated": is_afiliated,
        "afiliation_price":f"{afiliation_final_price(config=config)} Bs",
        "time":time,
        "platform_prices" : [ {
            "name": row.name,
            "price": f"{row.price}$",
            "afiliated_price": f"{row.afiliated_price}$",
            "reference_reward": f"{row.reference_reward}$"
        } for row in platform_prices]
    })

@seller_bp.route("/buy/", methods=["POST"])
@jwt_required()
def afiliar():
    try:
        if current_user.is_afiliated(): raise Exception("Ya estas afiliado")
        wallet = current_user.wallet()
        config = Config.query.filter_by(name="afiliation").first()
        price = afiliation_final_price(config=config)

        if wallet.amount < price: raise Exception("No tienes dinero suficiente")
        
        msg, start_date, end_date = current_user.afiliar(price = price, wallet = wallet)
        return SuccessResponse({ "msg": msg, "start_date":start_date, "end_date":end_date})

    except Exception as e:
        return ErrorResponse(error = str(e))