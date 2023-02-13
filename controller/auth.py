from flask import Blueprint, request, g
from models.models import User, Wallet
from flask_jwt_extended import create_access_token, jwt_required, current_user, get_jwt_identity
from main import ErrorResponse, SuccessResponse

# BLUEPRINTS
auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.before_request
def auth_before_request():
    pass

def create_user_token(user):
    identity = user.to_JSON().copy()
    identity.pop("password")
    identity.pop("parent_id")
    identity["link"] = f"/signup/{user.id}"
    access_token = create_access_token(identity=user)
    identity["access_token"] = access_token
    return identity


@auth_bp.post('/signin/')
def signin():
    try:
        email = request.json.get("email", None)
        password = request.json.get("password", None)
        user = User.verify(email=email, password=password)
        if not user:
            return {"msg": "Usuario o contraseña invalida"}, 401
        return create_user_token(user=user)
    except:
        return {"msg": "Usuario o contraseña invalida"}, 401

@auth_bp.post('/signup/')
def signup():
    username = request.json.get("name", None)
    email = request.json.get("email", None)
    password = request.json.get("password", None)
    phone = request.json.get("phone", None)
    parent_id = request.json.get("parent_id", None)

    phone_regex = r"(^\+)?[\d]{6,}$"
    email_regex = r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$"

    error_msg = []
    if not 8 < len(password) < 18:
        error_msg.append("Su contraseña debe ser mayor de 8 digitos")
    if not 6 < len(phone) < 16:
        error_msg.append("Su telefono debe contener minimo 6 caracteres y maximo 16")
    if User.query.filter_by(email=email).first():
        error_msg.append("Ya existe una cuenta de usuario registrado con ese correo")

    if len(error_msg) > 0:
        return ErrorResponse(error="Datos invalidos", errors=error_msg)
    user = User.create(username=username, email=email, password=password, phone=phone, user_type="client", parent_id=parent_id)
    wallet = Wallet.create(user=user)
    print(user.to_JSON(), wallet.to_JSON())
    if not user or not wallet:
        return ErrorResponse("Datos invalidos")
    return SuccessResponse({"user": create_user_token(user=user)})

@auth_bp.route("/wallet/", methods=["GET"])
@jwt_required()
def get_wallet():
    wallet = current_user.wallet()
    ret = {
        "amount":f"{wallet.amount} Bs",
        "balance":f"{wallet.balance} Bs"
    }
    return { "wallet":ret }, 200

@auth_bp.route("/protected/", methods=["GET"])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    return { "logged_in_as":current_user.to_JSON() }, 200