from pydantic import BaseModel

class Stock_Update_item(BaseModel):
    product_id: int
    quantity: int