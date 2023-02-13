from flask import Blueprint, request, jsonify
from models.models import Platform, StreamingAccount, Screen, ProductsByRequest, CompleteAccountRequest, db
from flask_jwt_extended import jwt_required, current_user
import os
from main import ErrorResponse, SuccessResponse

# BLUEPRINTS
products_bp = Blueprint('products_bp', __name__)

@products_bp.before_request
def users_before_request():
    pass

def indexJSON(product, price=None, in_buy=0):
    return {
        "id":product.id,
        "title": product.name,
        "img_path": product.img_path(),
        "file_name": product.file_name,
        "price": f"{price if price else product.final_price()} Bs",
        "in_buy":in_buy
    }

def requestJSON(product, price=None, in_buy=0):
    ret = indexJSON(product, price, in_buy)
    ret["slug"] = product.title_slug
    return ret

@products_bp.route('/')
def index():
    all = {"products":"", "platforms":""}
    all["products"] = [requestJSON(products) for products in ProductsByRequest.query.filter(ProductsByRequest.public==1).all()]
    all["platforms"] =  [indexJSON(platforms, price=account.final_price(), in_buy=screens) for platforms, account, screens in Platform.all_with_price()]
    return all

@products_bp.route("/platform/<id>/")
@jwt_required(optional=True)
def platform(id):
    def account_json(account, user=None):
        return {
            "id":account.id,
            "days_left":account.days_left(),
            "start_date":account.start_date.strftime("%d-%m-%Y"),
            "end_date":account.end_date.strftime("%d-%m-%Y"),
            "price":account.final_price(user=user),
            "reference_reward":account.final_reward
        }
    ret = dict()
    platform = Platform.query.filter(Platform.id == id).first()
    streaming_accounts = platform.streaming_accounts_dif_day(reverse=False)
    platformJSON = indexJSON(platform)
    platformJSON["url"] = platform.url

    return jsonify({
        "platform":platformJSON,
        "streaming_accounts":[account_json(account, user=current_user) for account in streaming_accounts ]
    })

    
@products_bp.route("/request/<slug>/")
@jwt_required(optional=True)
def request_(slug):
    def product_json(product, user=None):
        return {
            "id":product.id,
            "title":product.title,
            "img_path":product.img_path(),
            "description":product.description
        }
    def config_json(product, user=None):
        return {
            **product.config,
            "price_is_list":product.price_is_list(),
            "is_time":product.is_time(),
            "price":product.final_price_list(user=user)
        }
    # ret = dict()
    productModel = ProductsByRequest.query.filter(ProductsByRequest.title_slug == slug).first()
    product = product_json(productModel)
    config = config_json(productModel)
    

    return jsonify({
        "product":product,
        "config":config
        # "streaming_accounts":[account_json(account, user=current_user) for account in streaming_accounts ]
    })



@products_bp.route("/buy/<option>/", methods=["GET", "POST"])
@jwt_required()
def buy(option):
    wallet = current_user.wallet()
    if option.lower() == "screen":
        account_id =  request.args.get("account_id")

        if account_id == None: 
            account = StreamingAccount.query.order_by(StreamingAccount.end_date.desc()).first()
        else:
            account = StreamingAccount.query.filter(StreamingAccount.id == account_id).first()

        final_price = account.final_price(current_user)
        if wallet.amount - final_price < 0:
            return ErrorResponse("Saldo insuficiente, por favor recargue su saldo y luego vuelva a pedir su pantalla")
        elif request.method == "POST":
            screen = account.buy_screen(current_user)
            if screen == False: 
                return ErrorResponse("Esta cuenta no tiene pantallas disponibles, por favor vuelve a intentarlo")
            else:
                return SuccessResponse({
                    "msg":"Su compra ha sido satisfactoria",
                    "buy_data":{
                        "screen":screen.to_JSON(),
                        "account":account.to_JSON(),
                        "platform":account.platform().to_JSON()
                    }
                })
        else:
            return SuccessResponse({
                "msg":"El precio es {} bs, y usted tiene {} bs Va a comprar su cuenta por {} días. ¿Esta seguro?"
                        .format(final_price, wallet.amount, account.days_left())
            })
    elif option.lower() == "complete":
        platform =  request.args.get("platform")
        platform = Platform.query.get(platform)
        final_price =  platform.final_price(current_user)
        if request.method == "POST":
            try:
                wallet = current_user.wallet()
                if wallet.amount < final_price:
                    return ErrorResponse("Usted no tiene suficiente dinero para realizar esta transaccion")
                wallet.amount -= final_price
                req = CompleteAccountRequest(user_id = current_user.id, account_id=None, platform_id=platform.id, status=0)
                db.session.add_all([wallet, req])
                db.session.commit()
                return SuccessResponse({ "msg": "Su solicitud fué enviada, espere la respuesta" })
            except Exception as e:
                return ErrorResponse(str(e))
        return ErrorResponse("Metodo no soportado")
    elif option.lower() == "product":
        # El id_product es el slug del producto
        slug =  request .args.get("slug")

        p = ProductsByRequest.query.filter_by(title_slug=slug).first()
        if not p:
            return ErrorResponse("Ese producto no existe")
        compra = p.pedir(form=request.form, user = current_user)
        if compra: return SuccessResponse({ "msg": "Su pedido se ha realizado, pronto se le notificará"})
        else: return ErrorResponse("Este producto sobrepasa tu presupuesto por favor recarga")

def deleteNotusage():
    img_path = []
    for lista in all.values():
        for product in lista:
            img_path.append(product.get("file_name"))
    for img in os.listdir(path="static/img/"):
        if img not in img_path:
            os.remove(path="static/img/"+img)
    pass