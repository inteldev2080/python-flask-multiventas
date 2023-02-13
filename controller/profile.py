from flask import Blueprint, request, jsonify
from models.models import BuyHistory, User
from flask_jwt_extended import jwt_required, current_user

# BLUEPRINTS
profile_bp = Blueprint('profile_bp', __name__)

@profile_bp.before_request
def profile_before_request():
    pass

def union(buy_history, child_history):
    return {
        "buy_history":buy_history,
        "child_history":child_history
    }

def mov_JSON(buy_history):
    return {
        "id":buy_history.id,
        "date":buy_history.fecha.strftime("%d-%m-%Y"),
        "description":buy_history.buy_description,
        "amount":buy_history.price,
    }

def child_JSON(buy_history, username):
    return {
        "id":buy_history.id,
        "date":buy_history.fecha.strftime("%d-%m-%Y"),
        "description":buy_history.buy_description,
        "amount":buy_history.price,
        "utilities":buy_history.references_reward,
        "username":username
    }

@profile_bp.route("/movements/")
@jwt_required()
def movements():
    buy_history = [ mov_JSON(history) for history in BuyHistory.all_of_user(current_user) ]
    child_history = [ child_JSON(history, user.username) for history, user in BuyHistory.all_of_child(current_user) ]
    return union(buy_history=buy_history, child_history=child_history)

@profile_bp.route("/util/")
def util():
    return "Hola"

@profile_bp.route("/utilities/", methods=["POST"])
@jwt_required()
def utilities():
    response = ""
    try:
        action = request.json["actionSelect"]
        amount = float(request.json["amount"])
        wallet = current_user.wallet()
        if not 0 < amount <= wallet.balance:
            raise Exception("Ingrese un cantidad valida que no exceda sus utilidades ni sea menor a cero")

        if action == "wallet":
            if amount > 0:
                wallet.balanceToAmount(amount=amount)
                response = {"msg":"Se ha trapasado correctamente {} bs de sus utilidades a su billetera".format(amount), "status":True}
            else:
                response = {"error":"Cantidad no valida para transferir", "status":False}
        elif action == "pagomovil":
            if not current_user.ci:
                raise Exception("No tienes una cédula registrada")

            banco = request.json["banco"]
            phone = request.json["phone"]

            if (len(banco) != 4):  raise Exception("El campo de banco debe ser un codigo de 4 digitos")
            try:int(banco) 
            except ValueError: raise Exception("El codigo del banco debe ser solamente numeros, sin signos, ni guiones ejemplo: 0102")

            if (len(phone) != 11): raise Exception("El telefono debe ser 11 digitos solamente,")
            try:int(phone) 
            except ValueError: raise Exception("El telefono debe ser solamente numeros, sin signos, ni guiones")

            wallet.balanceToPagoMovil(user_id = current_user.id, phone=phone, banco=banco, amount=amount)
            
            response = {"msg":"Su peticion ha sido enviada correctamente", "status":True}

    except KeyError as e:
        response = { "error":"ERROR\nCampos no rellenados correctamente", "status":False }
    except ValueError as e:
        response = { "error":"Error inesperado, la cantidad deben ser un número valido", "status":False }
    except Exception as e:
        response = { "error":str(e), "status":False }
    return response

    
@profile_bp.route("/childs/")
@jwt_required()
def childs():
    childs = current_user.childs()
    ret = [{
        "username":child.username,
        "email":child.email,
        "phone":child.phone
    } for child in childs ] if childs else []
    return ret