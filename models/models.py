from datetime import date, datetime, timedelta
from flask import Markup
from flask_sqlalchemy import SQLAlchemy
from __init__ import create_app

# APP
app, environment = create_app()

db = SQLAlchemy()

#Decorador hecho para cualquier class que tenga un start_date y un end_date
def jsonable(cls):
    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def clean_json(self):
        ret = self.__dict__.copy()
        try:
            ret.pop("_sa_instance_state")
        except KeyError as KE: 
            ret
        return ret

    setattr(cls, "JSON", clean_json)
    setattr(cls, "to_JSON", as_dict)

    return cls

def timeDecorator(cls):
    def duration_days(self):
        days = self.end_date - self.start_date
        return days
    def timedelta_left(self)->timedelta:
        return self.end_date.__sub__(dateV.date_today())

    def days_left(self):
        days = self.timedelta_left().days
        return 0 if days < 0 else days

    def days_left_class_color(self):
        daysLeft = self.days_left()
        if daysLeft <= 5:
            badgeColor = 'danger'
        elif daysLeft <= 10:
            badgeColor = 'warning'
        else:
            badgeColor = 'success'
        return badgeColor
    
    def months_left(self):
        days = self.days_left()
        if days<21:     return 0
        else:           return self.end_date.month - dateV.date_today().month

    
    
    def time_left_message(self):
        dias = self.days_left()
        meses = self.months_left()
        return f'{dias} {"dias" if dias>1 else "dia"}' if meses < 1 else f'{meses} {"meses" if meses>1 else "mes"}'
    
    setattr(cls, "duration_days", duration_days)
    setattr(cls, "timedelta_left", timedelta_left)
    setattr(cls, "days_left", days_left)
    setattr(cls, "days_left_class_color", days_left_class_color)
    setattr(cls, "months_left", months_left)
    setattr(cls, "time_left_message", time_left_message)

    return cls

class dateV:
    tz = app.config["TZ_INFO"]

    @classmethod
    def datetime_now(cls):
        return datetime.now(tz=cls.tz)

    @classmethod
    def date_today(cls) ->date:
        now = cls.datetime_now()
        return date(year=now.year, month=now.month, day=now.day)
    
class Admin:
    def __init__(self, user):
        if user.user_type != "admin":
            raise "El usuario debe ser administrador"

        self.user = user
    
    def notififyUsersofAccounts(self, account, content):
        notify = []
        notified = []
        for screen in account.screens():
            user = screen.user()
            if user and user not in notified:
                now = dateV.datetime_now()
                notify.append(Notifications(user=user.id, date=now, content=content, showed=0))
                notified.append(user)
        db.session.add_all(notify)
        db.session.commit()
        pass

    def notififyUser(self, user, content):
        notification = Notifications(user=user, date=dateV.date_today(), content=content, showed=0)
        db.session.add(notification)
        db.session.commit()
        pass

    def notifyUsers(self, users, content):
        notifications = []
        for user in users:
            notification = Notifications(user=user, date=dateV.date_today(), content=content, showed=0)
            notifications.append(notification)
        db.session.add_all(notifications)
        db.session.commit()
        pass
    
    def notifyAllUsers(self, content):
        users = [user.id for user in User.query.all() if user.user_type in ["client", "seller"]]
        notifications = []
        for user in users:
            notification = Notifications(user=user, date=dateV.date_today(), content=content, showed=0)
            notifications.append(notification)
        db.session.add_all(notifications)
        db.session.commit()


@jsonable
class BuyHistory(db.Model):
    __tablename__ = "buy_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    product = db.Column(db.String(255))
    price = db.Column(db.Integer)
    references_reward = db.Column(db.Integer)
    buy_description = db.Column(db.String(255))
    fecha = db.Column(db.DateTime)

    @classmethod
    def all_of_user(cls, user):
        return BuyHistory.query.filter(BuyHistory.user_id == user.id).order_by(BuyHistory.fecha.desc()).all()

    @classmethod
    def all_of_child(cls, user):
        subquery = db.text(f"buy_history.user_id IN (SELECT id FROM user WHERE parent_id = {user.id}) ")
        # subquery = db.select(db.text(f"id from user where parent_id = {user.id}"))
        return db.session.query(cls, User).join(User, User.id == cls.user_id).filter(subquery).order_by(BuyHistory.fecha.desc()).all()
        
    def user(self):
        return User.query.get(self.user_id)
        

@jsonable
class CompleteAccountRequest(db.Model):
    __tablename__ = "complete_account_request"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    account_id = db.Column(db.Integer)
    platform_id = db.Column(db.Integer)
    status = db.Column(db.Integer)

    @classmethod
    def all_with_dependencies(cls, user=None):
        from flask import g
        query = db.session.query(cls, StreamingAccount, Platform)\
            .join(StreamingAccount, StreamingAccount.id == cls.account_id)\
            .join(Platform, Platform.id == cls.platform_id)\
            .order_by(db.text(f"DATEDIFF(streaming_account.end_date, \"{g.today}\")"))
        if user: query = query.filter(cls.user_id == user)
        return query.all()

    def user(self):  return User.query.filter(User.id == self.user_id).first()
    
    def platform(self):  return Platform.query.filter(Platform.id == self.platform_id).first()

    def account(self): return StreamingAccount.query.filter(StreamingAccount.id == self.account_id).first()
    
    def account_platform(self): 
        return db.session.query(StreamingAccount, Platform).join(Platform, StreamingAccount.select_platform == Platform.id).filter(StreamingAccount.id == self.account_id).first()

    def renew_account(self, user, account = None, platform = None, wallet = None):
        from main import ErrorResponse, SuccessResponse
        if not wallet:
            wallet = user.wallet()
        if not account:
            account = self.account()
        if not platform:
            platform = account.platform()

        final_price = platform.final_price(user)
        wallet.amount -= final_price

        if wallet.amount < 0 :
            return ErrorResponse("No tiene dinero suficiente")
        account.end_date = account.end_date + account.duration_days()
        history = BuyHistory(  user_id = user.id,
                                product = "platform",
                                price = final_price,
                                references_reward = 0,
                                buy_description = f"Renovacion de cuenta completa de {platform.name}",
                                fecha = dateV.datetime_now())

        db.session.add_all([account, wallet, history])
        db.session.commit()
        user.reward_parent(account.final_reward, history=history)
        return SuccessResponse({ "msg":"Usted ha renovado correctamente su cuenta" })
        

@jsonable
class ExpiredAccount(db.Model):
    __tablename__ = "expired_accounts"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer)
    platform_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    expired_date = db.Column(db.Date)

    @property
    def platform(self): return Platform.query.get(self.platform_id)

    def user(self): return User.query.get(self.user_id)
    
    def account(self): return StreamingAccount.query.get(self.user_id)
        

@jsonable
class Notifications(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer)
    date = db.Column(db.DateTime)
    content = db.Column(db.String(255))
    showed = db.Column(db.Integer)

@jsonable
class PaymentMethod(db.Model):
    __tablename__ = "payment_method"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer)
    payment_platform_name = db.Column(db.String(255))
    data = db.Column(db.String(255))
    file_name = db.Column(db.String(255))

@jsonable
class Platform(db.Model):
    __tablename__ = "platform"
    
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer)
    name = db.Column(db.String(255))
    url = db.Column(db.String(255))
    screen_amount = db.Column(db.Integer)
    price = db.Column(db.Float)
    afiliated_price = db.Column(db.Float)
    reference_reward = db.Column(db.Float)
    file_name = db.Column(db.String(255))
    """
        SELECT platform.*, streaming_account.price
        FROM platform 
        INNER JOIN streaming_account ON streaming_account.select_platform = platform.id 
        WHERE streaming_account.id = 
        (SELECT id FROM streaming_account WHERE streaming_account.`select_platform` = platform.id ORDER BY start_date desc LIMIT 1);
    """
    @classmethod
    def all_with_price(cls):
        subselect =db.select(db.text("id FROM streaming_account WHERE streaming_account.`select_platform` = platform.id ORDER BY start_date desc LIMIT 1")).subquery()
        subselect2 =db.text("(select COUNT(id) FROM screen WHERE ISNULL(screen.client) AND screen.platform = platform.id)")

        query = db.session.query(Platform, StreamingAccount, subselect2)\
            .select_from(Platform)\
            .join(StreamingAccount, StreamingAccount.select_platform == Platform.id)\
            .filter(StreamingAccount.id == subselect)

        return query.all()

    @classmethod
    def create(cls, user = None, name = None, url = None, screen_amount = None, price = None, afiliated_price = None, reference_reward = None, file_name = None):
        return Platform(user=user, name=name, url=url, screen_amount=screen_amount, price=price, afiliated_price=afiliated_price, reference_reward=reference_reward,file_name=file_name)

    @property
    def complete_account_price(self): return self.complete_account_price

    def final_price(self, user=None):
        from flask import g
        return round(self.price * g.get_dollar(), 2)
        
    @property
    def hasAccount(self): return self.hasStreaming_account()

    def img_path(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'client/assets/img/{self.file_name}/')

    def account_final_price(self, user=None):
        pass

    def hasStreaming_account(self):
        for res in self.streaming_accounts():
            if res.hasScreen():return True
        return False

    #Devuelve cuentas que solo tengan dias diferentes
    def streaming_accounts_dif_day(self, onlyAvailable=True, orderByDaysLeft = True, hidden_expired=True, reverse=True):
        sa = StreamingAccount.query.filter(StreamingAccount.select_platform == self.id).all()
        dif_day = dict()

        if onlyAvailable:
            accounts = list()
            availableScreens = set()
            for account in sa:
                accounts.append(account.id)
            screens = Screen.query.filter(Screen.account_id.in_(accounts))
            for screen in screens:
                if screen.available():
                    availableScreens.add(screen.account_id)
            sa = filter(lambda account: account.id in availableScreens, sa)

        for a in sa:
            key = f'{a.start_date}-{a.end_date}'
            if key not in dif_day.keys():
                dif_day[key] = a
        sa = dif_day.values()
        if hidden_expired:
            sa = filter(lambda obj: obj.days_left() > 0, sa)
        if orderByDaysLeft:
            #Devuelve las cuentas ordenadas y muestra primero las que más dias le quedan
            sa = sorted(sa, key = lambda account: account.days_left(), reverse=reverse)
        
        return [s for s in sa if not CompleteAccountRequest.query.filter_by(account_id=s.id).first()]

    def first_streaming_accounts(self, orderByDaysLeft = True, reverse=True):
        return  list( self.streaming_accounts(orderByDaysLeft = orderByDaysLeft, reverse=reverse) )[0]

    def streaming_accounts(self, onlyAvailable=True, orderByDaysLeft = True, reverse=True):
        sa = StreamingAccount.query.filter_by(select_platform = self.id).all()

        if onlyAvailable:
            sa = filter(lambda obj: obj.hasScreen(), sa)

        if orderByDaysLeft:
            #Devuelve las cuentas ordenadas y muestra primero las que más dias le quedan
            sa = sorted(sa, key = lambda account: account.days_left(), reverse=reverse)
        return sa
        return [s for s in sa if not CompleteAccountRequest.query.filter_by(account_id=s.id).first()]
    
    def public_json(self, user):
        json = self.to_JSON()
        json.pop("afiliated_price")
        json.pop("reference_reward")
        json["price"] =  self.final_price(user)
        return json
"""
    Descripcion de ProductsByRequets config
    La clase esta hecha para ser dinamica, las opciones hasta ahora son:
    
    - url:      str|None decidirá si mostrar el nombre del producto con un link
    - price:    int|list precio unico o por tiempo, los elementos de las listas será un diccionariio con un entero para el precio, y tres mas para la cantidad de años
    - campos:   list debe ser una lista de diccionario ejemeplo del diccionario{
        type:["text","number","email", "check", "radio", "date", "select"]
        name:"a gustos"
        label:"=="
        options:[ 
            Esta es unicamente si el type es select, debe ser una lista de diccionarios que van a tener el valor y el texto a mostrar
            { value, text }
        ]
    }
"""
@jsonable
class ProductsByRequest(db.Model):
    __tablename__ = "products_by_request"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    title_slug = db.Column(db.String(256), unique=True, nullable=False)
    description = db.Column(db.String(2000), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    config = db.Column(db.JSON())
    public = db.Column(db.Boolean, default=True)


    # estos valores son usados en el modulo "products.index"
    def img_path(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'client/assets/img/{self.file_path}/')

    @property
    def file_name(self):
        return self.file_path
        
    @property
    def name(self):
        return self.title

    def create_slug(self):
        self.sl

    @property
    def url(self):
        return self.config.get("url") or False

    @property
    def price(self):
        return self.config.get("price") or False

    @property
    def campos(self):
        return self.config.get("campos") or False
        
    def descriptionC(self):
        return self.config.get("description", "")

    def final_price(self, priceIndex=0, user=None, afiliated_price = True):
        from flask import g
        if user == None:
            afiliated_price = False

        if self.price_is_list():
            if afiliated_price:
                price = self.price[priceIndex]["price"] if not user.is_afiliated() else self.price[priceIndex]["afiliated_price"]
            else:
                price = self.price[priceIndex]["price"]
        else:
            if afiliated_price:
                price = self.price["price"] if not user.is_afiliated() else self.price["afiliated_price"]
            else:
                price = self.price["price"]
        return round(price * g.get_dollar(), 2)

    def final_price_list(self, user=None, afiliated_price = True):
        from flask import g
        price_is_list = self.price_is_list()
        is_afiliated = user.is_afiliated() if user else False

        if price_is_list:
            retPrice = []
            for plan in self.price:
                normal_price = plan["price"]
                afiliated = plan["afiliated_price"]

                price = afiliated if is_afiliated and afiliated_price else normal_price
                price = round(price  * g.get_dollar(), 2)
                retPrice.append({ "price":price, "duration":plan.get("duration"), "description":plan.get("description") })
        else:
            price = self.price["afiliated_price"] if is_afiliated and afiliated_price else self.price["price"]
            price = round(price  * g.get_dollar(), 2)
            retPrice = { "price":price, "description":self.price.get("description")}

        return retPrice

    def final_reward(self, priceIndex):
        from flask import g
        if self.price_is_list():
            reference_reward = self.price[priceIndex]["reference_reward"]
        else:
            reference_reward = self.price["reference_reward"]
            
        return round(reference_reward * g.get_dollar(), 2)

    def strfduration(self, priceIndex:int, promomes=""):
        if self.price_is_list():
            price = self.price[priceIndex]
            d = price.get("duration", False)
            if not d:
                return False
            days, months, years = d["days"], d["months"], d["years"]
            days = f'{str(days) + " día" if days==1 else str(days) + " días"} ' if days else ""
            months = f'{str(months) + " mes" if months==1 else str(months) + " meses"} ' if months else ""
            years = f'{str(years) + " año" if years==1 else str(years) + " años"} ' if years else ""
            return f'{days} {months} {years}{f" {promomes}" if price["price"]==0 else ""}'
        return False

    def searchDescription(self, priceIndex:int, promomes=""):
        if self.price_is_list():
            price = self.price[priceIndex]
            return  price.get("description", False)
        return False

    def deltatimeduration(self, priceIndex):
        if not self.price_is_list():
            return False
        d = self.price[priceIndex].get("duration", False)
        if not d:
            return False
        days, months, years = d["days"], d["months"], d["years"]
        now = dateV.date_today()

        days = timedelta(days=int(days))
        
        if months:  months = timedelta(days=months*30)
        else:       months = timedelta()
        
        years = now.replace(year=now.year+years) - now
        
        return days + months + years

    def price_is_list(self):
        return type(self.price) == type([])

    def is_time(self):
        if self.price_is_list():
            return bool(self.price[0].get("duration", False))
        return False

    def requests(self):
        query = db.session.query(UserProducts, User).join(User, UserProducts.user_id == User.id)
        ret = query.filter(UserProducts.product_id==self.id, UserProducts.status==0).all()
        return ret

    def resolved(self):
        query = db.session.query(UserProducts, User).join(User, UserProducts.user_id == User.id)
        ret = query.filter(UserProducts.product_id==self.id, UserProducts.status==1).all()
        if self.is_time():
            return sorted(ret, key = lambda request: request.UserProducts.days_left())
        else:
            return sorted(ret, key = lambda request: request.UserProducts.start_date)

    def expired(self):
        query = db.session.query(UserProducts, User).join(User, UserProducts.user_id == User.id)
        ret = query.filter(UserProducts.product_id==self.id, UserProducts.status==3).all()
        if self.is_time():
            return sorted(ret, key = lambda request: request.UserProducts.days_left())
        else:
            return sorted(ret, key = lambda request: request.UserProducts.start_date)
            
    @property
    def campos(self):
        return self.config.get("campos") or False

    def pedir(self, form, user):
        try:
            data = dict()
            if self.price_is_list():
                plan = int( form.get("price") )
            else:
                plan = 0
            price = self.final_price(plan, user)
            if user.wallet().amount >= price:
                user.wallet().amount -= price
                save = [user.wallet()]
                data["campos"] = dict()
                for campo in self.campos:
                    type = campo["type"]
                    if type in ["text","email"]:
                        data["campos"][campo["name"]] = form[campo["name"]]
                    elif type in ["number"]:
                        data["campos"][campo["name"]] = int(form[campo["name"]])
                data["plan"] = plan
                req = UserProducts(user_id=user.id, product_id = self.id, data=data, status=0)
                save.append(req)
                db.session.add_all(save)
                db.session.commit()
                return True
        except:
            return False
        return False
    
    # Esta funcion crea un objeto que se utiliza en el archivo templates/admin/products.html en la funcion multiprice_data
    def unique(self): return "true" if not self.price_is_list() else "false"
    def time(self): return "true" if self.is_time() else "false"
    def product(self): return "true" if self.price_is_list() and not self.is_time() else "false"

    def notification(self):
        query = db.select(db.func.count().label("notification") ).\
                where(UserProducts.status == 0).\
                where(UserProducts.product_id == self.id).\
                select_from(UserProducts)

        notification = db.session.execute(query).fetchone().notification
        return Markup(f' <span class="bg-danger rounded-circle p-1 text-white">{notification}</span>') if notification else ""



@jsonable
class RechargeAlerts(db.Model):
    __tablename__ = "recharge_alerts"
    id = db.Column(db.Integer, primary_key=True)
    first = db.Column(db.Integer)
    last = db.Column(db.Integer)
    status = db.Column(db.Integer)

    def get_first(self): return RechargeRequest.query.get(self.first)

    def get_last(self): return RechargeRequest.query.get(self.last)

@jsonable
class RechargeRequest(db.Model):
    __tablename__ = "recharge_request"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer)
    date = db.Column(db.DateTime)
    payment_method = db.Column(db.Integer)
    amount = db.Column(db.Float)
    reference = db.Column(db.String(50))
    status = db.Column(db.String(100))

    def bg(self):
        if self.status == "verificado":
            return "--bs-info"
        elif self.status == "rechazado":
            return "--bs-danger"
        elif self.status == "no verificado":
            return "--bs-warning"
        return "--bs-dark"
    
    def classBG(self):
        opa = "bg-opacity-50"
        if self.status == "verificado":
            return f"bg-success {opa}"
        elif self.status == "rechazado":
            return f"bg-danger {opa}"
        else:
            pass

    def alertLayoutBg(self):
        alert = db.session.execute(db.select(RechargeAlerts).where(db.or_(RechargeAlerts.first==self.id, RechargeAlerts.last==self.id))).scalar()
        if alert:
            return {"message":"Esta recarga es una posible duplicada","bg":"bg-danger bg-opacity-50","event":f'ondblclick=showAlert({alert.id})'}
        else:
            return {"message":"","bg":"","event":""}

    def get_user(self): return User.query.get(self.user)

    def getPayment_method(self): return PaymentMethod.query.get(self.payment_method)

    @classmethod
    #los duplicados son cuando la persona envia el mismo reporte varias veces por desespero
    def revisarDuplicados(cls, reference, amount, payment_method, user):
        duplicate = RechargeRequest.query.filter_by(status="no verificado", reference = reference, amount=amount, user=user.id).first()
        if not duplicate:
            recharge = RechargeRequest(user = user.id, date=dateV.datetime_now(), status="no verificado", payment_method=payment_method, amount=amount, reference=reference)
            db.session.add(recharge)
            db.session.commit()
            return recharge
        else:
            return False

    # son cuando quieren meter varias veces la misma recarga para sacar plata
        # Esta parte verifica si el metodo de pago es el mismo, pero salio el caso de que el pago fue reportado por pago movil y por transferencia a la misma cuenta
        # por eso se quitara la verificacion del metodo de pago
        # duplicate = RechargeRequest.query.filter_by(status="verificado", payment_method=payment_method, reference = reference, amount=amount).first()
    def revisarEstafaRepetido(self):
        duplicates = RechargeRequest.query.filter_by(status="verificado", reference = self.reference, amount=self.amount).all()
        if duplicates:
            alertMessage = "Este reporte a sido fichado como un caso de posible duplicacion, será revisado por los administradores"
            alerts = []
            for rr in duplicates:
                alert = RechargeAlerts(last=self.id, first=rr.id, status=0)
                alerts.append(alert)
            notifi = Notifications(user=self.user, date=dateV.date_today(), content=alertMessage, showed=1)
            db.session.add_all([alert, notifi])
            db.session.commit()
            return {"status": False, "error":alertMessage}
        else: return {"status": True, "message":"Su pedido de recarga a sido enviado exitosamente"}

@jsonable
@timeDecorator
class Screen(db.Model):
    __tablename__ = "screen"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer)
    profile = db.Column(db.Integer)
    platform = db.Column(db.Integer)
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())
    client = db.Column(db.Integer)
    month_pay = db.Column(db.String(11))

    @classmethod
    def all_with_dependencies(cls, user=None):
        from flask import g
        query = db.session.query(cls, StreamingAccount, Platform)\
            .join(StreamingAccount, StreamingAccount.id == cls.account_id)\
            .join(Platform, Platform.id == cls.platform)\
            .order_by(db.text(f"DATEDIFF(streaming_account.end_date, \"{g.today}\")"))
        if user: query = query.filter(cls.client == user)
        return query.all()

    @property
    def getPin(self):
        p = self.profile
        pin = str(2+p).rjust(2, "0") if 2+p < 10 else str(2+p)
        return f"2{p}{pin}" if self.account().pin else "Sin pin"
        
    def change_dates(self, start_date=None, end_date=None):
        if start_date != None:self.start_date = start_date 
        if end_date != None:self.end_date = end_date 

    def renew_screen(self, user, account = None, platform = None, wallet = None):
        from main import ErrorResponse, SuccessResponse
        if not wallet:
            wallet = user.wallet()
        if not account:
            account = self.account()
        if not platform:
            platform = account.platform()

        final_price = account.final_price(user, time_discount=False)
        wallet.amount -= final_price

        if wallet.amount < 0 :
            return ErrorResponse("No tiene dinero suficiente")
        self.end_date = self.end_date + self.duration_days()
        history = BuyHistory(  user_id = user.id,
                                product = "platform",
                                price = final_price,
                                references_reward = 0,
                                buy_description = f"Renovacion de pantalla {platform.name}",
                                fecha = dateV.datetime_now())

        db.session.add_all([self, wallet, history])
        db.session.commit()
        user.reward_parent(account.final_reward, history=history)
        return SuccessResponse({ "msg":"Usted ha renovado correctamente su cuenta" })
        
    def messageWhatsApp(self):
        return 'Estimado cliente {}, su cuenta de {} bajo el email {} se vencerá el {}, recuerde renovar a tiempo'.format(
            self.user().username, self.account().platform().name, self.account().email, self.end_date.strftime('%d-%m-%Y'))

    def expired(self, now = None):
        if self.client == None: return
        if now == None: 
            now = dateV.date_today()

        if now >= self.end_date:
            expired_account = ExpiredAccount(account_id = self.account_id,
                                                user_id = self.client,
                                                platform_id = self.platform,
                                                expired_date = now)
            self.client = None
            db.session.add_all([self, expired_account])
            db.session.commit()

    def renew(self, start_date, end_date):
        if self.client == None:
            self.change_dates(start_date=start_date, end_date=end_date)
            db.session.add(self)
            db.session.commit()

    def user(self):
        if self.client == None:
            return None
        return User.query.get(self.client)

    def account(self): return StreamingAccount.query.get(self.account_id)

    def account_platform(self): 
        return db.session.query(StreamingAccount, Platform).join(Platform, StreamingAccount.select_platform == Platform.id).filter(StreamingAccount.id == self.account_id).first()

    def available(self): 
        if self.days_left()<=0: return False
        if self.client != None: return False
        return True

@jsonable
@timeDecorator
class StreamingAccount(db.Model):
    __tablename__ = "streaming_account"

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer)
    select_platform = db.Column(db.Integer)
    select_supplier = db.Column(db.Integer)
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())
    email = db.Column(db.String(255))
    password = db.Column(db.String(255))
    last_screens = db.Column(db.Integer)
    price = db.Column(db.Float, nullable=False, default=0)
    afiliated_price = db.Column(db.Float, nullable=False, default=0)
    reference_reward = db.Column(db.Float, nullable=False, default=0)
    pin = db.Column(db.Integer)

    # @property
    def final_price(self, user=None, afiliated_price = True, time_discount=True):
        from flask import g
        if user == None: afiliated_price = False
        if afiliated_price:     price = self.price if not user.is_afiliated() else self.afiliated_price
        else:                   price = self.price
        list_discount = {
            "0":  0,
            "1": .05,
            "2": .1,
            "3": .3,
        }
        default = .5
        left = self.duration_days() - self.timedelta_left()
        discount = list_discount.get(str(left.days), default)
        if time_discount:
            price = price - (price * discount)
        
        return round(price * g.get_dollar(), 2)

    @property
    def final_reward(self, time_discount=True):
        from flask import g
        reward = self.reference_reward
        list_discount = {
            "0":  0,
            "1": .05,
            "2": .1,
            "3": .3,
        }
        default = .5
        left = self.duration_days() - self.timedelta_left()
        discount = list_discount.get(str(left.days), default)
        if time_discount:
            reward = reward - (reward * discount)
        return round(reward * g.get_dollar(), 2)

    def getAvailableScreen(self):
        for screen in self.screens():
            if screen.client == None:
                return screen
        return None
        
    def buy_screen(self, user):
        if self.hasScreen():
            screen = self.getAvailableScreen()
        
            final_price = self.final_price(user)
            wallet = user.wallet()
            wallet.amount -= final_price
            if wallet.amount < 0 :
                return False
            Lottery.reward_user(user= user, buy_amount=final_price)

            screen.client = user.id
            screen.change_dates(start_date = self.start_date, end_date = self.end_date)
            history = BuyHistory(  user_id = user.id,
                                    product = "platform",
                                    price = final_price,
                                    references_reward = 0,
                                    buy_description = f"Compra de pantalla {self.platform().name}",
                                    fecha = dateV.date_today())

            db.session.add_all([self, screen, user.wallet(), history])
            db.session.commit()
            user.reward_parent(self.final_reward, history = history)
            return screen
        else: return False


    def hasScreen(self):
        for screen in self.screens():
            if screen.available(): return True
        return False

    def screens(self):
        return db.session.execute(db.select(Screen).where(Screen.account_id == self.id)).scalars()

    def platform(self):
        return db.session.execute(db.select(Platform).filter_by(id=self.select_platform)).scalar()

    def expired_accounts(self):
        return db.session.execute(db.select(ExpiredAccount).filter_by(account_id=self.id)).scalars()

    def complete_account(self): 
        query = db.session.query(CompleteAccountRequest, User).join(User, User.id == CompleteAccountRequest.user_id)
        return query.filter(CompleteAccountRequest.account_id == self.id).first() or False

    def delete_all(self):
        screens = self.screens()
        if screens:
            for screen in screens: db.session.delete(screen)
        self.delete_me()

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    def delete_me(self):
        db.session.delete(self)
        db.session.commit()

@jsonable
class Supplier(db.Model):
    __tablename__ = "supplier"
    id = db.Column(db.Integer, primary_key=True)
    user=db.Column(db.Integer)
    name=db.Column(db.String(255))
    platform_that_supplies=db.Column(db.String(255))
    email=db.Column(db.String(255))
    phone=db.Column(db.String(255))
    local_phone=db.Column(db.String(255))
    country=db.Column(db.String(255))
    paypal=db.Column(db.String(255))
    pago_movil=db.Column(db.String(255))
    bank=db.Column(db.String(255))
    pass

@jsonable
class User(db.Model):
    __tablename__ = "user"
    
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(255))
    parent_id = db.Column(db.Integer)
    username = db.Column(db.String(255))
    email = db.Column(db.String(255))
    password = db.Column(db.String(255))
    phone = db.Column(db.String(100))
    ci = db.Column(db.String(255), nullable = True)
    gender = db.Column(db.String(255), nullable = True)
    
    @classmethod
    def create(cls, user_type = None, parent_id = None, username = None, email = None, password = None, phone = None, ci = None, gender = None):
        user = User(user_type=user_type, parent_id=parent_id, username=username, email=email, password=password, phone=phone, ci=ci, gender="null")
        db.session.add(user)
        db.session.commit()
        return user
        
    @classmethod
    def verify(cls, email=email, password=password):
        return User.query.filter(User.email == email).filter(User.password == password).first()

    def edit(self, user_type = None, parent_id = None, username = None, email = None, password = None, phone = None, ci = None, gender = None):
        
        self.user_type=user_type    if user_type else self.user_type
        self.parent_id=parent_id    if parent_id else self.parent_id
        self.username=username      if username else self.username
        self.email=email            if email else self.email
        self.password=password      if password else self.password
        self.phone=phone            if phone else self.phone
        self.ci=ci                  if ci else self.ci
        self.gender=gender          if gender else self.gender
        return self

    def parent(self):
        return User.query.filter_by(id =self.parent_id).first()

    def CI(self, default=None):
        defaultM = default if default else None
        return self.ci if self.ci else defaultM
    
    @property
    def standarPhone(self):
        return f'58{self.phone[1:]}'

    def wa_me(self, text = False):
        return f"https://api.whatsapp.com/send?phone={self.standarPhone}{'&text='+text if text else ''}"

    def childs(self):
        childs = db.session.execute(db.select(User).where(User.parent_id == self.id)).scalars().all()
        return childs if bool(childs) else False
        
    def reward_parent(self, reward=0, history = None):
        if self.parent() != None:
            self.parent().wallet().balance += reward
            if history != None:
                history.references_reward = reward
                db.session.add_all([self.parent(), history])
            else:
                db.session.add(self.parent())
            db.session.commit()

    def history(self):
        return db.session.execute(db.select(BuyHistory).where(BuyHistory.user_id == self.id)).scalars()
    
    def childs_history(self):
        childs = self.childs()
        if childs:
            childs_id = [child.id for child in childs]
            return db.session.execute( db.select(BuyHistory).where(BuyHistory.user_id.in_(childs_id)) ).scalars().all()
        return childs

    def screens_p(self, page = 1):
        return db.paginate(db.select(Screen).where(Screen.client == self.id), page=page, per_page=3, error_out=False)
        
    def recharge_requests(self):
        return db.session.execute(db.select(RechargeRequest).where(RechargeRequest.user == self.id)).scalars()

    def screens(self, platform = None):
        if platform:
            return db.session.execute(db.select(Screen)
                    .where(Screen.client == self.id)
                    .where(Screen.platform == platform)
                ).scalars()

        return db.session.execute(db.select(Screen).where(Screen.client == self.id)).scalars()
    
    def complete_accounts(self, with_account=False):
        comp_acc_req = CompleteAccountRequest.query
        if with_account:
            comp_acc_req = db.session.query(CompleteAccountRequest, StreamingAccount).join(StreamingAccount, StreamingAccount.id == CompleteAccountRequest.account_id)
        ret =  comp_acc_req.filter(CompleteAccountRequest.user_id == self.id, CompleteAccountRequest.status==1).all()

        print("\n\n\n\n", ret )
        return ret
    
    def expired_accounts(self):
        return db.session.execute(db.select(ExpiredAccount).where(ExpiredAccount.user_id == self.id)).scalars()

    def expired_accounts_diff_platform(self):
        ea = self.expired_accounts()
        response = dict()
        for a in ea:
            key = a.platform.name
            if key not in response.keys():
                response[key] = a
        return response.values()
    
    def wallet(self):
        return db.session.execute(db.select(Wallet).where(Wallet.user == self.id)).scalar()

    def afiliar(self, price = None, wallet = None):
        from flask import g
        if not price:
            config =  Config.query.filter(Config.name == "afiliation").first()
            price = round(float(config.options["price"])  * g.get_dollar(), 2)
        if not wallet or ( wallet and wallet.user != self.id):
            wallet = self.wallet

        wallet.amount -= price
        hoy = dateV.date_today()
        un_mes = hoy + timedelta( days=30 )

        afiliacion = Afiliated.query.filter_by(user_id = self.id).first()
        msg=""

        if afiliacion:
            afiliacion.status       = 1
            afiliacion.start_date   = hoy
            afiliacion.end_date     = un_mes
            msg = "Su membresía ha sido renovada"
        else:
            afiliacion = Afiliated(user_id=self.id, status=1, start_date=hoy, end_date=un_mes)
            msg = "Ha comprado la membresia de revendedor"

        history = BuyHistory(  user_id = self.id,
                                product = "afiliation",
                                price = price,
                                references_reward = 0,
                                buy_description = f"{self.username} te convertiste en revendedor",
                                fecha = hoy)
                        
        db.session.add_all([ wallet, afiliacion, history ])
        db.session.commit()
        
        return msg, hoy, un_mes
    
    def is_afiliated(self):
        try:
            return self.afiliation().status == 1
        except Exception as ae:
            return False
    
    def afiliation(self):
        return Afiliated.query.filter_by(user_id=self.id).first()
    
    def products(self):
        return UserProducts.query.filter_by(user_id=self.id).all()
    
    def expiredAll(self):
        now = dateV.date_today()
        screens = self.screens()
        for screen in screens:
            screen.expired(now = now)
        afiliated = self.afiliation()
        if afiliated:
            afiliated.expired(now = now)

        products = self.products()
        if products:
            for product in products: product.expired(now = now)
            
    def wsphone(self):
        try:
            import re
            response = self.phone

            if response.startswith("0"): 
                response= response[1:]
            if response[0] in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]: 
                response = f"+58{response}"
            response = response.replace("-", "")
            response = response.replace(".", "")
            response = response.replace(" ", "")
            return response
        except Exception as e:
            return str(e)

    def first_recharge(self):
        rr = RechargeRequest.query.filter_by(user = self.id).order_by(RechargeRequest.date.desc()).first()
        if rr:return rr.date.strftime("%d-%m-%Y")
        else: return None
    
    def save_me(self):
        db.session.add(self)
        db.session.commit()
        

"""
    Compras de los usuarios de los productos dinámicos 
"""

@timeDecorator
@jsonable
class UserProducts(db.Model):
    __tablename__ = "user_products"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    data = db.Column(db.JSON)
    status = db.Column(db.Integer)
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())

    @classmethod
    def all_with_dependencies(cls, user=None, onlyAccept = True):
        query = db.session.query(cls, ProductsByRequest).join(ProductsByRequest, ProductsByRequest.id == cls.product_id)
        if user: query = query.filter(cls.user_id == user)
        if onlyAccept: query = query.filter(cls.status == 1)
        return query.all()

    def product(self): return ProductsByRequest.query.get(self.product_id)

    def user(self): return User.query.get(self.user_id)

    def containDate(self): 
        def element(inside):
            return f'<div class="d-flex flex-column">{inside}</div>'
        start, end = bool(self.start_date), bool(self.end_date)
        if start and end:
            ret = element(f'<p class="m-0 border-bottom border-2 border-dark"><b>Inicio:</b> {self.start_date.strftime("%d-%m-%Y")}</p><p class="m-0"><b>Fin:</b> {self.end_date.strftime("%d-%m-%Y")}</p>')
        elif start:
            ret = element(f'<p class="m-0 border-bottom border-2 border-dark"><b>Fecha:</b> {self.start_date.strftime("%d-%m-%Y")}</p><p class="m-0">{self.product().searchDescription(self.data.get("plan", 0))}</p>')
        else: 
            ret = "<p>00-00-0000</p>"
        return Markup(ret)
            

    def active(self, info=None):
        ppp = self.product()
        if not ppp:
            return False
        self.status = 1
        self.start_date = dateV.date_today()
        time = ppp.deltatimeduration(self.data.get("plan", -1))
        hoy = dateV.date_today()
        self.end_date = hoy + time if time else None

        if info:
            copy = self.data.copy()
            copy["info"] = info
            self.data = copy
        
        db.session.add(self)
        db.session.commit()

        Lottery.reward_user(user= self.user(), buy_amount=self.getBuyPrice())
        
        self.sendBuyHistory(reference_reward= ppp.final_reward(self.data.get("plan")))
        return True

    def reject(self, description, admin):
        self.status=2

        uWallet = self.user().wallet()


        uWallet.amount += self.getBuyPrice()

        db.session.add_all([self, uWallet])
        db.session.commit()

        if description:
            mensaje = f"Su peticion de {self.product().title} fué rechazada, Motivo: {description}. Se le ha repuesto su dinero."
            admin.notififyUser(user=self.user_id, content=mensaje)
        return True

    def sendBuyHistory(self, reference_reward=0):
        product = self.product()
        price = self.getBuyPrice()
        history = BuyHistory(  user_id = self.user_id,
                                product = "product",
                                price = price,
                                references_reward = 0,
                                buy_description = f"Compra de {product.title}",
                                fecha = dateV.date_today())
        db.session.add(history)
        db.session.commit()

        self.user().reward_parent(reference_reward, history)
        pass
    
    def getBuyPrice(self):
        return self.product().final_price(self.data.get("plan"), self.user())
    
    def expired(self, now = None):
        if self.status != 1: return
        if now == None: 
            now = dateV.date_today()

        if not self.end_date: return

        if now >= self.end_date:
            self.status = 3
            db.session.add(self)
            db.session.commit()

@jsonable
class Wallet(db.Model):
    __tablename__ = "wallet"
    
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0)
    balance = db.Column(db.Float, nullable=False, default=0)
    pass

    @classmethod
    def create(cls, user = None):
        wallet = Wallet(user=user.id, amount=0, balance=0)
        db.session.add(wallet)
        db.session.commit()
        return wallet

    def balanceToAmount(self, amount):
        if self.balance < amount:
            raise Exception("Error al transferir las utilidades")
        self.amount += amount
        self.balance -= amount
        db.session.add(self)
        db.session.commit()

    def balanceToPagoMovil(self, user_id, phone, banco, amount):
        if self.balance < amount:
            raise Exception("Error al transferir las utilidades")
        self.balance -= amount
        pagomovil = PagoMovilRequest(user_id = user_id, phone=phone, banco=banco, amount=amount)
        db.session.add_all([self, pagomovil])
        db.session.commit()

@jsonable
class Config(db.Model):
    __tablename__ = "config"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    options = db.Column(db.JSON)

@jsonable
class Afiliated(db.Model):
    __tablename__ = "afiliated"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Boolean)
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())

    @classmethod
    def config(cls):
        return Config.query.filter_by(name="afiliation").first() or False
    
    def expired(self, now = None):
        if self.status != 1: return
        if now == None: 
            now = dateV.date_today()

        if now >= self.end_date:
            self.status = 0
            db.session.add(self)
            db.session.commit()


@jsonable
class Lottery(db.Model):
    __tablename__ = "lottery"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Integer, default=0)

    def user(self):
        return User.query.get(self.user_id)

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def config(cls):
        return Config.query.filter_by(name="lottery").first() or False
    
    @classmethod
    def is_active(cls):
        active = cls.config().options.get("active")
        if not active:
            return False
        end = cls.end_date
        if dateV.date_today() >= end:
            return False
        return True
    
    @classmethod
    @property
    def start_date(cls):
        active = cls.config().options.get("active")
        if not active:
            return None
        start = cls.config().options.get("active").get("start_date")
        return date.fromisoformat(start)
    
    @classmethod
    @property
    def end_date(cls):
        start = cls.start_date
        duration = cls.duration
        if not (start and duration):
            return None
        return start + duration
    
    @classmethod
    @property
    def duration(cls):
        active = cls.config().options.get("active")
        if not active:
            return None
        return timedelta(seconds=cls.config().options.get("active").get("duration"))

    @classmethod
    def reward_user(cls, user, buy_amount=0):
        try:
            if not user:
                raise Exception("")
            config = cls.config()
            if not config.options.get("active"):
                raise Exception("")
            if not buy_amount >= config.options.get("min_buy"):
                raise Exception("")

            uLottery = Lottery.query.filter_by(user_id = user.id).first()
            parent_reward = False

            if not uLottery:
                uLottery = Lottery(user_id = user.id, amount = config.options.get("buy_reward"))
                uLottery.save_me()
                parent_reward = config.options.get("child_first_buy_reward")

            parent = user.parent()
            if parent:
                pLottery = Lottery.query.filter_by(user_id = parent.id).first()
                if pLottery:
                    pLottery.amount += parent_reward or config.options.get("child_buy_reward")
                    pLottery.save_me()

            return True
        except Exception as e:
            return False
        
@jsonable
class PagoMovilRequest(db.Model):
    __tablename__ = "pago_movil_request"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(16), nullable=False)
    banco = db.Column(db.String(16), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)

    def user(self):
        return User.query.filter_by(id=self.user_id).first()

    def save_me(self):
        db.session.add(self)
        db.session.commit()

@jsonable
class SupportProducts(db.Model):
    __tablenmae__="support_products"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(64), nullable=False)
    file_path = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(255), default="")
    type = db.Column(db.String(64), nullable=False)
    type_id = db.Column(db.Integer)
    status = db.Column(db.Integer, default=1)
    date = db.Column(db.Date(), default=dateV.date_today)

    def img_path(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'client/assets/support_img/{self.file_path}/')

    def user(self):
        return User.query.filter_by(id=self.user_id).first()
    
    def product(self):
        if self.type == "account":
            return StreamingAccount.query.filter_by(id=self.type_id).first()
        elif self.type == "screen":
            return Screen.query.filter_by(id=self.type_id).first()
        elif self.type == "product":
            return UserProducts.query.filter_by(id=self.type_id).first()
        return None
    
    def str_type(self):
        if self.type == "account":
            return "Cuenta completa"
        elif self.type == "screen":
            return "Pantalla"
        elif self.type == "product":
            return "Producto"
        
        return "Indeterminado"
    
    def state(self):
        return "Abierto" if self.status else "Solucionado"

    def url(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'client/assets/support_img/{self.file_path}/')
        return url_for('support_bp.img', filename=self.file_path)

    def save_me(self):
        db.session.add(self)
        db.session.commit()
        
        
@jsonable
class Suggestion(db.Model):
    __tablename__="suggestion"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(64), nullable=False)
    date = db.Column(db.Date(), default=dateV.date_today())
    status = db.Column(db.Boolean, nullable=False, default=False)

    def save_me(self):
        db.session.add(self)
        db.session.commit()
        

def init_DB(app):
    db.init_app(app=app)
        
    with app.app_context():
        db.create_all()
    return db