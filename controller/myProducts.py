from flask import Blueprint, request, jsonify
from models.models import UserProducts, CompleteAccountRequest, Screen
from flask_jwt_extended import jwt_required, current_user
from main import ErrorResponse, SuccessResponse
import os

# BLUEPRINTS
my_products_bp = Blueprint('my_products_bp', __name__)

@my_products_bp.before_request
def users_before_request():
    pass

def userProductsJSON(req, product):
    return {
        "id":req.id,
        "title": product.title,
        "start_date":req.start_date.strftime("%d-%m-%Y"),
        "end_date":req.end_date.strftime("%d-%m-%Y") if req.end_date else req.start_date.strftime("%d-%m-%Y"),
        "data":req.data["campos"],
        "info":req.data.get("info", "-")


    }

def completeAccountJSON(req, account, platform):
    from flask import g
    ret =  {
        "id":req.id,
        "title":platform.name,
        "platform_url":platform.url,
        "start_date":account.start_date.strftime("%d-%m-%Y"),
        "end_date":account.end_date.strftime("%d-%m-%Y"),
        "days_left":(account.end_date - g.today).days,
        "email":account.email,
        "password":account.password
    }
    return ret

def screensJSON(screen, account, platform):
    from flask import g
    return {
        "id":screen.id,
        "title":platform.name,
        "platform_url":platform.url,
        "start_date":screen.start_date.strftime("%d-%m-%Y"),
        "end_date":screen.end_date.strftime("%d-%m-%Y"),
        "days_left":(screen.end_date - g.today).days,
        "email":account.email,
        "password":account.password,
        "profile":screen.profile,
        "pin":screen.getPin if account.pin else "Sin pin"
    }

@my_products_bp.route('/')
@jwt_required()
def index():
    all = {"product_by_requests":[], "complete_accounts":[], "screens":[]}
    all["screens"] =  [screensJSON(screen, account, platform) for screen, account, platform in Screen.all_with_dependencies(current_user.id)]
    all["complete_accounts"] =  [completeAccountJSON(req, account, platform) for req, account, platform in CompleteAccountRequest.all_with_dependencies(current_user.id)]
    all["product_by_requests"] = [userProductsJSON(req, product) for req, product in UserProducts.all_with_dependencies(current_user.id)]
    return jsonify(all)


@my_products_bp.route("/renew/screen/<id>/", methods = ["GET","POST"])
@jwt_required()
def renew_screen(id):
    screen = Screen.query.filter(Screen.id == id).first()
    if not screen:
        return ErrorResponse("Esta pantalla no existe")

    wallet = current_user.wallet()
    account, platform = screen.account_platform()
    price = account.final_price(current_user, time_discount=False)

    if screen.client == None or screen.client != current_user.id:
        return ErrorResponse("No puedes renovar esta cuenta, ya que no es tuya")
    elif wallet.amount - price < 0:
        return ErrorResponse(f"Usted no cuenta con suficiente dinero para renovar su pantalla necesita por lo menos {price} Bs, por favor recargue")
    elif request.method == "POST":
        return screen.renew_screen(user = current_user, account = account, platform = platform, wallet = wallet)
    return SuccessResponse({
        "msg":"El precio es {} bs, y usted tiene {} bs Va a renovar su cuenta por {} d&iacute;as m&aacute;s.</br></br>¿Esta seguro?"
                .format(price, wallet.amount, account.duration_days().days)
    })

@my_products_bp.route("/renew/complete_account/<id>/", methods = ["GET","POST"])
@jwt_required()
def renew_complete_account(id):
    complete = CompleteAccountRequest.query.filter(CompleteAccountRequest.id == id).first()
    print(complete, id)
    if not complete:
        return ErrorResponse("Esta cuenta no existe")

    wallet = current_user.wallet()
    account, platform = complete.account_platform()
    price = platform.final_price(current_user)

    if complete.user_id != current_user.id:
        return ErrorResponse("No puedes renovar esta cuenta, ya que no es tuya")
    elif wallet.amount - price < 0:
        return ErrorResponse(f"Usted no cuenta con suficiente dinero para renovar su pantalla necesita por lo menos {price} Bs, por favor recargue")
    elif request.method == "POST":
        complete.renew_account(user = current_user, account = account, platform = platform, wallet = wallet)
        return SuccessResponse({ "msg":"Usted ha renovado correctamente su cuenta" })
    return SuccessResponse({
        "msg":"El precio es {} bs, y usted tiene {} bs Va a renovar su cuenta por {} d&iacute;as m&aacute;s.</br></br>¿Esta seguro?"
                .format(price, wallet.amount, account.duration_days().days)
    })

@my_products_bp.route("/renew/dynamic/")
@jwt_required()
def renew_dynamic(id):
    return { "status":False, "error": "este metodo no esta implementado"}