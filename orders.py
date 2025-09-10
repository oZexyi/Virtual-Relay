import json
import math
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Product:
    name: str
    product_number: int
    stack_height: int
    tray_type: str
    units_per_tray: int
    origin_plant: int

@dataclass
class Route:
    route_id: int
    location: str

@dataclass
class OrderItem:
    product_number: int
    product_name: str
    units_ordered: int
    units_per_tray: int
    trays_needed: int
    stack_height: int
    stacks_needed: int
    tray_type: str

@dataclass
class Order:
    order_id: str
    route_id: int
    location: str
    order_date: str
    items: List[OrderItem]
    total_trays: int
    total_stacks: int

class OrderSystem:
    def __init__(self, products_file: str = "products.json", routes_file: str = "routes.json"):
        self.products_file = products_file
        self.routes_file = routes_file
        self.products: {}
        self.routes: {}
        self.orders: {}
        self.load_data()
    def load_data(self):
        try:
            with open(self.products_file, "r") as f:
                products_data = json.load(f)
                for product_data in products_data:
                    product = Product(**product_data)
                    self.products[product.product_number] = product
            with open(self.routes_file, "r") as f:
                routes_data = json.load(f)
                for location, route_numbers in routes_data.items():
                    for route_number in route_numbers:
                        route = Route(
                            route_id=route_number,
                            location=location,
                        )
                        self.routes[route_number] = route
            print(f"Loaded {len(self.products)} products and {len(self.routes)} routes.")
            return True
        except FileNotFoundError as e:
            print(f"Error loading data: {e}")
            print(f"Please ensure products.json and routes.json exist in the current directory.")
            return False
        except Exception as e:
            print(f"Error parsing JSON files: {e}")
            return False
    def get_available_routes(self) -> List[Route]:
