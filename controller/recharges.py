from flask import Blueprint, request, jsonify
from models.models import RechargeRequest, PaymentMethod, db
from flask_jwt_extended import current_user, jwt_required
import os

# BLUEPRINTS
recharges_bp = Blueprint('recharges_bp', __name__)

@recharges_bp.before_request
def users_before_request():
    pass

def indexJSON(product):
    return {
        "id":product.id,
        "title": product.name,
        "img_path": os.path.join(request.host_url, f'assets/img/{product.file_name}/'),
        "price": product.price
    }

@recharges_bp.route('/')
@jwt_required()
def index():
    recharges =  db.session.query(RechargeRequest, PaymentMethod)\
            .join(PaymentMethod, PaymentMethod.id == RechargeRequest.payment_method)\
            .filter(RechargeRequest.user == current_user.id).all()
    ret = []
    for recharge, payment_method in recharges:
        ret.append({
            "id":recharge.id,
            "reference":recharge.reference,
            "date":recharge.date.strftime("%d-%m-%Y %H:%M"),
            "payment_data":payment_method.payment_platform_name,
            "amount":recharge.amount,
            "status":recharge.status,
            
        })
    return ret

@recharges_bp.route('/', methods=["POST"])
@jwt_required()
def post():
    errors : dict()
    try: payment_method = int(request.json.get("method", 0))
    except: 
        payment_method = 0
        errors["payment_method"] = "-Error al ingresar el método de pago"

    try: amount = float(request.json.get("amount", 0))
    except: 
        amount = 0.0
        errors["amount"] = "-Error al ingresar la cantidad no puede ser cero"

    try: 
        code = request.json.get("code", "")
        int(code)
        if len(code) != 4: 
            raise Exception("La referencia debe contener 4 digitos")
    except Exception as e: 
        code = 0
        errors["code"] = str(e)

    if not payment_method or not amount>0 or not code:
        return jsonify({"status":False, "errors":errors})
    recarga = RechargeRequest.revisarDuplicados(code, amount=amount, payment_method=payment_method, user=current_user)
    if not recarga:
        return jsonify({"status":False, "error":"Recarga repetida, debe esperar a que la anterior sea procesada"})
    revision = recarga.revisarEstafaRepetido()
    return jsonify(revision)

@recharges_bp.route('/payment-method/')
# @jwt_required()
def get():
    payment_methods = PaymentMethod.query.all()
    res = []
    for pm in payment_methods:
        payment_dict = pm.to_JSON()
        payment_dict.pop("user")
        payment_dict.pop("file_name")
        res.append(payment_dict)
    return res