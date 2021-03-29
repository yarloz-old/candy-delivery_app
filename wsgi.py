from datetime import datetime

from flask import Flask, request
from flask_restful import fields, marshal
from cerberus import Validator
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
from pyrfc3339 import generate, parse
import pytz

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# format validators
schema_courier_post = {'courier_id': {'type': 'integer', 'required': True},
                       'courier_type': {'type': 'string', 'required': True, 'allowed': ['foot', 'bike', 'car']},
                       'regions': {'type': 'list', 'required': True},
                       'working_hours': {'type': 'list', 'required': True}}
schema_courier_patch = {'courier_type': {'type': 'string', 'required': False, 'allowed': ['foot', 'bike', 'car']},
                        'regions': {'type': 'list', 'required': False},
                        'working_hours': {'type': 'list', 'required': False}}
schema_order_post = {'order_id': {'type': 'integer', 'required': True},
                     'weight': {'type': ['integer', 'float'], 'required': True, 'min': 0.01, 'max': 50},
                     'region': {'type': 'integer', 'required': True},
                     'delivery_hours': {'type': 'list', 'required': True}}

v_courier_post = Validator(schema_courier_post)
v_courier_patch = Validator(schema_courier_patch)
v_order_post = Validator(schema_order_post)

# database models
class CourierInfo(db.Model):
    __tablename__ = 'courier_info'
    id = db.Column(db.Integer, primary_key=True)
    courier_id = db.Column(db.Integer)
    courier_type = db.Column(db.String)
    max_weight = db.Column(db.Integer)
    regions = db.relationship('Regions', backref='courier', lazy='dynamic', cascade="all,delete-orphan")
    working_hours = db.relationship('WorkingHours', backref='courier', lazy='dynamic', cascade="all,delete-orphan")
    orders = db.relationship('Orders', backref='courier', lazy='dynamic')
    assign_time = db.Column(db.String)
    last_delivery = db.Column(db.String)
    rate = db.Column(db.String)
    sum_paid = db.Column(db.Integer)

class Orders(db.Model):
    __tablename__ = 'orders_info'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer)
    weight = db.Column(db.String)
    region = db.Column(db.Integer)
    delivery_hours = db.relationship('DeliveryHours', backref='order', lazy='dynamic', cascade="all,delete-orphan")
    courier_id = db.Column(db.Integer, db.ForeignKey('courier_info.courier_id'))
    complete_time = db.Column(db.String)
    completion_time = db.Column(db.Integer)
    courier_id_completed = db.Column(db.Integer)
    completed_on = db.Column(db.String)

class WorkingHours(db.Model):
    __tablename__ = 'working_hours'
    id = db.Column(db.Integer, primary_key=True)
    working_hours_left = db.Column(db.DateTime)
    working_hours_right = db.Column(db.DateTime)
    courier_id = db.Column(db.Integer, db.ForeignKey('courier_info.courier_id'))


class DeliveryHours(db.Model):
    __tablename__ = 'delivery_hours'
    id = db.Column(db.Integer, primary_key=True)
    delivery_hours_left = db.Column(db.DateTime)
    delivery_hours_right = db.Column(db.DateTime)
    order_id = db.Column(db.Integer, db.ForeignKey('orders_info.order_id'))


class Regions(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.Integer)
    courier_id = db.Column(db.Integer, db.ForeignKey('courier_info.id'))

# models for marhaling
class DateRepr(fields.Raw):
    def format(self, x):
        return x.working_hours_left.strftime("%H:%M") + "-" + x.working_hours_right.strftime("%H:%M")

class OrderIDRepr(fields.Raw):
    def format(self, x):
        return {"id": x.order_id}


courier_resource_fields = {"courier_id": fields.Integer,
                           "courier_type": fields.String,
                           "regions": fields.List(fields.Integer(attribute="region")),
                           "working_hours": fields.List(DateRepr)}

courier_assign_fields = {"orders": fields.List(OrderIDRepr),
                         "assign_time": fields.String}

courier_resource_fields_get_1 = {"courier_id": fields.Integer,
                                 "courier_type": fields.String,
                                 "regions": fields.List(fields.Integer(attribute="region")),
                                 "working_hours": fields.List(DateRepr),
                                 "rating": fields.Float,
                                 "earnings": fields.Integer}

courier_resource_fields_get_2 = {"courier_id": fields.Integer,
                                 "courier_type": fields.String,
                                 "regions": fields.List(fields.Integer(attribute="region")),
                                 "working_hours": fields.List(DateRepr),
                                 "earnings": fields.Integer}

# constans dictionaries
max_weight_dic = {"foot": 10, "bike": 15, "car": 50}
coef_dict = {"foot": 2, "bike": 5, "car": 9}


@app.route('/couriers', methods=["PUT"])
def couriers_put():
    request_json = request.get_json( )
    faild_ids = []
    courier_ids = []
    for courier_data in request_json:
        courier_id = courier_data["courier_id"]
        courier_ids.append({'id': courier_id})
        if not v_courier_post(courier_data):
            faild_ids.append({'id': courier_id})
    if faild_ids:
        return {"validation_error": {"couriers": faild_ids}}, 400
    else:
        for courier_data in request_json:
            courier_id = courier_data["courier_id"]
            courier_type = courier_data["courier_type"]
            max_weight = max_weight_dic[courier_type]
            regions = courier_data["regions"]
            working_hours = courier_data["working_hours"]
            courier = CourierInfo(courier_id=int(courier_id),
                                  courier_type=courier_type,
                                  max_weight=max_weight)
            for working_hours_pair in working_hours:
                working_hours_pair = working_hours_pair.split("-")
                working_hours_left = datetime.strptime(working_hours_pair[0], "%H:%M")
                working_hours_right = datetime.strptime(working_hours_pair[1], "%H:%M")
                wh = WorkingHours(working_hours_left=working_hours_left,
                                  working_hours_right=working_hours_right)
                courier.working_hours.append(wh)

            for region in regions:
                r = Regions(region=region)
                courier.regions.append(r)
            db.session.add(courier)
            db.session.commit()
        return {"couriers": courier_ids}, 202


@app.route('/couriers/<int:courier_id>', methods=["PATCH"])
def couriers_patch(courier_id):
    request_json = request.get_json( )
    if not v_courier_patch(request_json):
        return '', 400
    else:
        courier = CourierInfo.query.filter_by(courier_id=int(courier_id)).first()
        if "courier_type" in request_json:
            courier_type = request_json['courier_type']
            courier.courier_type = courier_type
            courier.max_weight = max_weight_dic[courier_type]
            orders = courier.orders.filter(Orders.weight > courier.max_weight).all()
            if not orders:
                for order in orders:
                    order.courier = None
                    db.session.add(order)
                    db.session.add(courier)
                    db.session.commit()

        if "regions" in request_json:
            regions = request_json["regions"]
            courier.regions = []
            for region in regions:
                r = Regions(region=region)
                courier.regions.append(r)
            orders = courier.orders.filter(Orders.region.notin_(tuple(region.region for region in courier.regions))).all()
            if orders:
                for order in orders:
                    order.courier = None
                    db.session.add(order)
                    db.session.add(courier)
                    db.session.commit()
        if "working_hours" in request_json:
            courier.working_hours = []
            orders = courier.orders.all()
            working_hours = request_json["working_hours"]
            for working_hours_pair in working_hours:
                working_hours_pair = working_hours_pair.split("-")
                working_hours_left = datetime.strptime(working_hours_pair[0], "%H:%M")
                working_hours_right = datetime.strptime(working_hours_pair[1], "%H:%M")
                wh = WorkingHours(working_hours_left=working_hours_left,
                                  working_hours_right=working_hours_right)
                courier.working_hours.append(wh)
            if not orders:
                for order in orders:
                    suitable_time_found = False
                    for delivery_hours in order.delivery_hours:
                        order_delivery_hours_left = delivery_hours.delivery_hours_left
                        order_delivery_hours_right = delivery_hours.delivery_hours_right
                        for working_hours in courier.working_hours:
                            working_hours_left = working_hours.working_hours_left
                            working_hours_right = working_hours.working_hours_right
                            if (order_delivery_hours_left < working_hours_right) and (
                                    order_delivery_hours_right > working_hours_left):
                                suitable_time_found = True
                                break
                    if not suitable_time_found:
                        order.courier = None
                        db.session.add(order)
                        db.session.add(courier)
                        db.session.commit()
        db.session.commit()
        return marshal(courier, courier_resource_fields), 200


@app.route('/orders', methods=["POST"])
def orders_post():
    request_json = request.get_json()
    fail_ids = []
    order_ids = []
    for order_data in request_json:
        order_id = order_data["order_id"]
        order_ids.append({'id': order_id})
        if not v_order_post(order_data):
            fail_ids.append({'id': order_id})
    if fail_ids:
        return {"validation_error": {"orders": fail_ids}}, 400
    else:
        for order_data in request_json:
            order_id = order_data["order_id"]
            weight = order_data["weight"]
            region = order_data["region"]
            delivery_hours = order_data["delivery_hours"]
            order = Orders(order_id=int(order_id),
                           weight=str(weight),
                           region=int(region))
            for delivery_hours_pair in delivery_hours:
                delivery_hours_pair = delivery_hours_pair.split("-")
                delivery_hours_pair_left = datetime.strptime(delivery_hours_pair[0], "%H:%M")
                delivery_hours_pair_right = datetime.strptime(delivery_hours_pair[1], "%H:%M")
                dh = DeliveryHours(delivery_hours_left=delivery_hours_pair_left,
                                   delivery_hours_right=delivery_hours_pair_right)
                order.delivery_hours.append(dh)

            db.session.add(order)
        db.session.commit()
        return {"orders": order_ids}, 201


@app.route('/orders/assign', methods=["POST"])
def orders_post_assign():
    request_json = request.get_json()
    courier_id = request_json["courier_id"]
    courier = CourierInfo.query.filter_by(courier_id=int(courier_id)).first()
    if courier is None:
        return '', 400
    if not courier.orders.all():
        orders = Orders.query.filter(Orders.region.in_(tuple(region.region for region in courier.regions)),
                                     Orders.weight <= courier.max_weight,
                                     Orders.courier_id_completed == None,
                                     Orders.courier_id == None).all()
        if not orders:
            return {"orders": []}, 200
        assigned_order_ids = []
        for order in orders:
            suitable_time_found = False
            for delivery_hours in order.delivery_hours:
                order_delivery_hours_left = delivery_hours.delivery_hours_left
                order_delivery_hours_right = delivery_hours.delivery_hours_right
                for working_hours in courier.working_hours:
                    working_hours_left = working_hours.working_hours_left
                    working_hours_right = working_hours.working_hours_right
                    if (order_delivery_hours_left < working_hours_right) and (
                            order_delivery_hours_right > working_hours_left):
                        suitable_time_found = True
                        break
            if suitable_time_found:
                courier.orders.append(order)
                assigned_order_ids.append({"id": order.order_id})

        if assigned_order_ids:
            courier.assign_time = generate(datetime.utcnow().replace(tzinfo=pytz.utc))
            db.session.commit()
            return {"orders": assigned_order_ids, "assign_time": courier.assign_time}, 200
        else:
            return {"orders": []}, 200
    else:
        return marshal(courier, courier_assign_fields), 200


@app.route('/orders/complete', methods=["POST"])
def orders_post_complete():
    request_json = request.get_json()
    courier_id = request_json["courier_id"]
    order_id = request_json["order_id"]
    complete_time = request_json["complete_time"]
    courier = CourierInfo.query.filter_by(courier_id=int(courier_id)).first()
    order = courier.orders.filter_by(order_id=order_id).first()
    if not order:
        return '', 400
    order.complete_time = complete_time
    if not courier.last_delivery:
        order.completion_time = (parse(complete_time) - parse(courier.assign_time)).total_seconds()
    else:
        order.completion_time = (parse(complete_time) - parse(courier.last_delivery)).total_seconds()
    courier.last_delivery = complete_time
    order.courier = None
    order.courier_id_completed = order.courier_id
    order.completed_on = courier.courier_type
    db.session.add(order)
    db.session.add(courier)
    db.session.commit()
    return {"order_id": order_id}, 200


@app.route('/couriers/<int:courier_id>', methods=["GET"])
def couriers_get(courier_id):
    courier = CourierInfo.query.filter_by(courier_id=courier_id).first()
    orders = Orders.query.filter_by(courier_id_completed=courier_id).all()
    if len(orders) != 0:
        statement = text(
            """SELECT MIN(avg_completion_time) FROM (SELECT AVG(completion_time) as \
            avg_completion_time FROM orders_info WHERE courier_id_completed={} GROUP BY region)""".format(courier_id))
        t = db.session.execute(statement).all()[0][0]
        rating = round((60 * 60 - min(t, 60 * 60)) / (60 * 60) * 5, 2)
        earnings = sum([500 * coef_dict[order.completed_on] for order in orders])
        courier.earnings = earnings
        courier.rating = rating
        return marshal(courier, courier_resource_fields_get_1), 200
    else:
        courier.earnings = 0
        return marshal(courier, courier_resource_fields_get_2), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0")
