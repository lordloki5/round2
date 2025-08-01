# generated by datamodel-codegen:
#   filename:  product_schema.json
#   timestamp: 2025-07-16T02:15:35+00:00

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_partial import create_partial_model


class Product(BaseModel):
    product_id: int = Field(..., title='Product Id')
    name: str = Field(..., title='Name')
    price: float = Field(..., title='Price')
    tags: Optional[List[str]] = Field([], title='Tags')

PartialProduct = create_partial_model(Product, recursive=True)
