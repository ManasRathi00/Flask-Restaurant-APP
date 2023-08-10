from app import application
from flask import jsonify, Response, session
from app.models import *
from app import *
import uuid
import datetime
from marshmallow import Schema, fields
from flask_restful import Resource, Api
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc, use_kwargs
import json

# Creating Schemas for various API calls
class SignUpRequest(Schema):
    name = fields.Str(default = "name")
    username = fields.Str(default = "username")
    password = fields.Str(default = "password")
    level = fields.Integer(default=0)

class CreateItemOrderRequest(Schema):
    user_id = fields.Str(default = "user_id")
    item_id = fields.Str(default = "item_id")
    quantity = fields.Integer(default=0)

class APIResponse(Schema):
    message = fields.Str(default="Success")

class PlaceOrderRequest(Schema):
    order_id = fields.String()

class VendorAPIResponse(Schema):
    message = fields.Str(default="Success")

class LoginRequest(Schema):
    username = fields.Str(default="username")
    password = fields.Str(default="password")
    
class AddItemRequest(Schema):
    item_id=fields.Str(default="1")
    item_name=fields.Str(default="name")
    calories_per_gm=fields.Integer(default=0)
    available_quantity=fields.Integer(default=0)
    restaurant_name=fields.Str(default="restaurant_Name")
    unit_price=fields.Integer(default=0)

class AddVendorRequest(Schema):
    user_id=fields.Str(default="user id")

class ListOrdersByCustomerRequest(Schema):
    customer_id=fields.Str(default="customer id")  

# Creating API call classes and Functions

# This is a signup API. This should take, “name,username, password,level” as parameters.
#  Here, the level is 0 for the customer, 1 for the vendor and 2 for Admin.
class SignUpAPI(MethodResource, Resource):
    @doc(description='Sign Up API', tags=['SignUp API'])
    @use_kwargs(SignUpRequest, location=('json'))
    @marshal_with(APIResponse)  # marshalling
    def post(self, **kwargs):
        try:
            user = User(
                uuid.uuid4(), 
                kwargs['name'], 
                kwargs['username'], 
                kwargs['password'], 
                kwargs['level'])
            db.session.add(user)
            db.session.commit()
            return APIResponse().dump(dict(message='User is successfully registerd')), 200     
        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message=f'Not able to register user : {str(e)}')), 404
    pass 

api.add_resource(SignUpAPI, '/signup')
docs.register(SignUpAPI)

# This API should take the username and password of signed-up users and successfully log them in. 
class LoginAPI(MethodResource, Resource):
    @doc(description='Login API', tags=['Login API'])
    @use_kwargs(LoginRequest, location=('json'))
    @marshal_with(APIResponse)  # marshalling
    def post(self, **kwargs):
        try:
            user = User.query.filter_by(username=kwargs['username'], password = kwargs['password']).first()
            if user:
                print('logged in')
                session['user_id'] = user.user_id
                print(f'User id : {str(session["user_id"])}')
                return APIResponse().dump(dict(message='User is successfully logged in')), 200
                # return jsonify({'message':'User is successfully logged in'}), 200
            else:
                return APIResponse().dump(dict(message='User not found')), 404
                # return jsonify({'message':'User not found'}), 404
        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message=f'Not able to login user : {str(e)}')), 400
            # return jsonify({'message':f'Not able to login user : {str(e)}'}), 400
    pass
         
api.add_resource(LoginAPI, '/login')
docs.register(LoginAPI)

# This API should log out the customer.
class LogoutAPI(MethodResource, Resource):
    @doc(description='Logout API', tags=['Logout API'])
    @marshal_with(APIResponse)  # marshalling
    def post(self, **kwargs):
        try:
            if session['user_id']:
                session['user_id'] = None
                print('logged out')
                return APIResponse().dump(dict(message='User is successfully logged out')), 200
            else:
                print('user not found')
                return APIResponse().dump(dict(message='User is not logged in')), 401
        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message=f'Not able to logout user : {str(e)}')), 400


api.add_resource(LogoutAPI, '/logout')  
docs.register(LogoutAPI)

# Only added customers can be made vendors.This API should take“user_id” as a parameter.
class AddVendorAPI(MethodResource, Resource):
    @doc(description="Add a vendor",tags=['add_vendor API'])
    @use_kwargs(AddVendorRequest,location=('json'))
    @marshal_with(APIResponse) # marshalling
    def post(self,**kwargs):
        try:
            if session['user_id']:
                user_id = kwargs['user_id']
                user_type=User.query.filter_by(user_id=user_id).first().level
                print(user_id)
                if(user_type ==0):
                    User.level = 1
                    db.session.commit()
                    return APIResponse().dump(dict(message="Customer is upgraded to vendor")),200
                else :
                    return APIResponse().dump(dict(message="Customer is already a vendor")),405
            else:
                return APIResponse().dump(dict(message="Customer is not logged in")),401
        except Exception as e :
            print(str(e))
            return  APIResponse().dump(dict(message=f"Not able to upgrade to vendor:  {e}")),400
    pass        

api.add_resource(AddVendorAPI, '/add_vendor')
docs.register(AddVendorAPI)

# Only logged-in users can call this API. This should return all the vendor details with their store and item offerings.
class GetVendorsAPI(MethodResource, Resource):
    @doc(description="Get vendors API", tags=['Vendors API'])
    @marshal_with(APIResponse)
    def get(self):
        try:
            if session['user_id']:
                vendors = []
                for vendor in User.query.filter_by(level=1).all():
                    items = []
                    for item in Item.query.filter_by(vendor_id=vendor.user_id).all():
                        items.append({"item_id": item.item_id, "item_name": item.item_name, "calories_per_gm": item.calories_per_gm, "available_quantity": item.available_quantity, "restaurant_name": item.restaurant_name, "unit_price": item.unit_price})
                    vendors.append({"vendor_id": vendor.user_id, "name": vendor.name, "items": items})
                return jsonify(vendors)
            else:
                return VendorAPIResponse().dump(dict(message="User is not logged in")), 401
        except Exception as e:
            print(str(e))
            return VendorAPIResponse().dump(dict(message=f"Not able to list vendors: {str(e)}")), 400
    pass
    

api.add_resource(GetVendorsAPI, '/list_vendors')
docs.register(GetVendorsAPI)

# Only logged-in vendors can add items. 
# This API should take, “item_id,item_name, restaurant_name, available_quantity, unit_price, calories_per_gm”.
class AddItemAPI(MethodResource, Resource):
    @doc(description="Add an item API",tags=['item API'])
    @use_kwargs(AddItemRequest,location=('json'))
    @marshal_with(APIResponse) # marshalling
    def post(self,**kwargs):
        try:
            if session['user_id']:
                user_id = session['user_id']
                user_type=User.query.filter_by(user_id=user_id).first().level
                print(user_id)
                if(user_type ==1):
                    item=Item(
                        kwargs['item_id'],
                        user_id,
                        kwargs['item_name'],
                        kwargs['calories_per_gm'],
                        kwargs['available_quantity'],
                        kwargs['restaurant_name'],
                        kwargs['unit_price']
                    )
                    db.session.add(item)
                    db.session.commit()
                    return APIResponse().dump(dict(message="Item is succesfully created")),200
                else :
                    return APIResponse().dump(dict(message="Logged in User is not a vendor")),405
            else:
                return APIResponse().dump(dict(message="Vendor is not logged in")),401
        except Exception as e :
            print(str(e))
            return  APIResponse().dump(dict(message=f"Not able to list vendors:  {e}")),400

    pass
            
api.add_resource(AddItemAPI, '/add_item')
docs.register(AddItemAPI)


class ListItemsAPI(MethodResource, Resource):
    @doc(description="Item List API",tags=['item_list API'])
    @marshal_with(APIResponse) 
    def get(self):
        try:
            items = Item.query.all()
            items_list = []
            for item in items:
                items_list.append({
                    "item_id": item.item_id,
                    "vendor_id": item.vendor_id,
                    "item_name": item.item_name,
                    "calories_per_gm": item.calories_per_gm,
                    "available_quantity": item.available_quantity,
                    "restaurant_name": item.restaurant_name,
                    "unit_price": item.unit_price
                })
            return jsonify(items_list)
        except Exception as e:
            return {'message': 'Error: ' + str(e)}, 500
    pass

api.add_resource(ListItemsAPI, '/list_items')
docs.register(ListItemsAPI)


class CreateItemOrderAPI(MethodResource, Resource):
    @doc(description="Create Item Order API",tags=['create_item_order API'])
    @use_kwargs(CreateItemOrderRequest,location=('json'))
    @marshal_with(APIResponse) 
    def post(self,**kwargs):
        try:
            user_id = kwargs['user_id']
            item_id = kwargs['item_id']
            quantity = kwargs['quantity']
            user = User.query.filter_by(user_id=user_id).first()
            item = Item.query.filter_by(item_id=item_id).first()
            if not user:
                return APIResponse().dump(dict(message="Invalid user_id")),400
            if not item:
                return APIResponse().dump(dict(message="Invalid item_id")),400

            if quantity > item.available_quantity:
                return APIResponse().dump(dict(message="Requested quantity is not available")),400
            order_id = str(uuid.uuid1())
            order = Order(order_id, user_id)
            db.session.add(order)
            db.session.commit()
            order_item = OrderItems(order_id, item_id, quantity, item.unit_price)
            db.session.add(order_item)
            item.available_quantity -= quantity
            db.session.commit()
            return APIResponse().dump(dict(message="Order placed successfully")),200
        except Exception as e:
            return {'message': str(e)}, 500
                

api.add_resource(CreateItemOrderAPI, '/create_items_order')
docs.register(CreateItemOrderAPI)

# Only logged-in customers can place orders.This API should take“order_id” as a parameter.
class PlaceOrderAPI(MethodResource, Resource):
    @doc(description="Place an Order API",tags=['order API'])
    @use_kwargs(PlaceOrderRequest,location=('json'))
    @marshal_with(APIResponse) 
    def post(self,**kwargs):
        order_id=kwargs['order_id']
        # Get user information from a session or token
        user = User.query.filter_by(user_id=session['user_id']).first()
        if not user:
            return APIResponse().dump(dict(message="You must be logged in to place an order.")),401

        # Check if order with given id already exists
        order = Order.query.filter_by(order_id=order_id).first()
        if order:
            return APIResponse().dump(dict(message="Order with this id already exists.")),409
        # Create new order
        new_order = Order(order_id, user.user_id)
        db.session.add(new_order)
        db.session.commit()
        return APIResponse().dump(dict(message="Order placed successfully.")),201

            
api.add_resource(PlaceOrderAPI, '/place_order')
docs.register(PlaceOrderAPI)

# Only logged-in users can call this API. This returns all the orders placed by that customer.
# This should take “customer_id” as a parameter.
class ListOrdersByCustomerAPI(MethodResource, Resource):
    @doc(description="List Order API by Customer",tags=['list_order_by_customer API'])
    @use_kwargs(ListOrdersByCustomerRequest,location=('json'))
    @marshal_with(APIResponse) 
    def get(self, **kwargs):
        customer_id=kwargs['customer_id']
            # Check if user is logged in
        user = User.query.filter_by(user_id=session['user_id']).first()
        if not user:
            return APIResponse().dump(dict(message="You must be logged in to view your orders.")),401

        # Get all orders placed by the customer
        orders = Order.query.filter_by(user_id=customer_id).all()
        if not orders:
            return APIResponse().dump(dict(message="No orders found for this customer.")),404 
        order_list = []
        for order in orders:
            order_list.append({"order_id": order.order_id, "total_amount": order.total_amount, "created_ts": order.created_ts})

        return {"orders": order_list}, 200
      
api.add_resource(ListOrdersByCustomerAPI, '/list_orders')
docs.register(ListOrdersByCustomerAPI)

# Only the admin can call this API.This API returns all the ordersin the orders table.
class ListAllOrdersAPI(MethodResource, Resource):
    @doc(description="List all Order API",tags=['list_all_orders API'])
    @marshal_with(APIResponse)
    def get(self):
        # Check if user is admin
        user = User.query.filter_by(user_id=session['user_id']).first()
        if not user or user.level != 1:
            return APIResponse().dump(dict(message="You must be an admin to view all orders.")),401 
        # Get all orders
        orders = Order.query.all()
        if not orders:
            return APIResponse().dump(dict(message="No orders found.")),404
        order_list = []
        for order in orders:
            order_list.append({"order_id": order.order_id, "user_id": order.user_id, "total_amount": order.total_amount, "created_ts": order.created_ts})
        return {"orders": order_list}, 200
            
api.add_resource(ListAllOrdersAPI, '/list_all_orders')
docs.register(ListAllOrdersAPI)