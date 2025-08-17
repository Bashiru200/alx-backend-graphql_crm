import graphene
from .models import Customer, Product, Order
from .types import CustomerType, ProductType, OrderType
from django.core.validators import validate_email
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction
from datetime import datetime

# -------------------------------
# CreateCustomer Mutation
# -------------------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    customer = graphene.Field(CustomerType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        try:
            validate_email(email)
            if Customer.objects.filter(email=email).exists():
                return CreateCustomer(success=False, message="Email already exists")

            if phone:
                import re
                if not re.match(r'^(\+?\d{10,15}|\d{3}-\d{3}-\d{4})$', phone):
                    return CreateCustomer(success=False, message="Invalid phone format")

            customer = Customer(name=name, email=email, phone=phone or "")
            customer.save()

            return CreateCustomer(customer=customer, success=True, message="Customer created successfully")
        except ValidationError as e:
            return CreateCustomer(success=False, message="Invalid email format")

# -------------------------------
# BulkCreateCustomers Mutation
# -------------------------------
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(CustomerInput)

    created_customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, customers):
        created = []
        errors = []

        for idx, c in enumerate(customers):
            try:
                validate_email(c.email)
                if Customer.objects.filter(email=c.email).exists():
                    errors.append(f"{c.email}: Email already exists")
                    continue
                if c.phone:
                    import re
                    if not re.match(r'^(\+?\d{10,15}|\d{3}-\d{3}-\d{4})$', c.phone):
                        errors.append(f"{c.email}: Invalid phone format")
                        continue

                customer = Customer(name=c.name, email=c.email, phone=c.phone or "")
                created.append(customer)
            except ValidationError:
                errors.append(f"{c.email}: Invalid email format")

        with transaction.atomic():
            Customer.objects.bulk_create(created)

        return BulkCreateCustomers(created_customers=created, errors=errors)

# -------------------------------
# CreateProduct Mutation
# -------------------------------
class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int()

    product = graphene.Field(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, price, stock=0):
        if price <= 0:
            return CreateProduct(success=False, message="Price must be positive")
        if stock < 0:
            return CreateProduct(success=False, message="Stock cannot be negative")

        product = Product(name=name, price=price, stock=stock)
        product.save()
        return CreateProduct(product=product, success=True, message="Product created successfully")

# -------------------------------
# CreateOrder Mutation
# -------------------------------
class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)
        order_date = graphene.DateTime()

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, customer_id, product_ids, order_date=None):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except ObjectDoesNotExist:
            return CreateOrder(success=False, message="Customer not found")

        if not product_ids:
            return CreateOrder(success=False, message="No products selected")

        products = Product.objects.filter(id__in=product_ids)
        if products.count() != len(product_ids):
            return CreateOrder(success=False, message="Invalid product ID(s)")

        total = sum([product.price for product in products])

        order = Order.objects.create(
            customer=customer,
            order_date=order_date or datetime.now(),
            total_amount=total
        )
        order.products.set(products)
        return CreateOrder(order=order, success=True, message="Order created successfully")
