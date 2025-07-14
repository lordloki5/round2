from pydantic import BaseModel
from typing import List, Optional
import json
import os

# Define nested Pydantic models
class Contact(BaseModel):
    phone: str
    email: Optional[str] = None

class Address(BaseModel):
    street: str
    city: str
    zip_code: str
    country: Optional[str] = None

class User(BaseModel):
    name: str
    age: int
    address: Address
    contacts: List[Contact]

class Product(BaseModel):
    product_id: int
    name: str
    price: float
    tags: List[str] = []

class Order(BaseModel):
    order_id: int
    user: User
    products: List[Product]
    status: str

class Review(BaseModel):
    review_id: int
    user: User
    product: Product
    rating: int
    comment: Optional[str] = None

class Store(BaseModel):
    store_id: int
    name: str
    address: Address
    orders: List[Order]
    reviews: List[Review]

# Directory to save schemas
schema_dir = "json_schemas"
os.makedirs(schema_dir, exist_ok=True)

# Generate and save JSON schemas
schemas = {
    "contact_schema.json": Contact.schema(),
    "address_schema.json": Address.schema(),
    "user_schema.json": User.schema(),
    "product_schema.json": Product.schema(),
    "order_schema.json": Order.schema(),
    "review_schema.json": Review.schema(),
    "store_schema.json": Store.schema()
}

for file_name, schema in schemas.items():
    with open(os.path.join(schema_dir, file_name), "w") as f:
        json.dump(schema, f, indent=2)

print(f"JSON schemas generated in {schema_dir}/")