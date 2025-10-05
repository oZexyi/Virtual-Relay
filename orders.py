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
    route_id: int  # Route number (e.g., 6278, 5539)
    location: str  # Warehouse location (e.g., Anderson, Galax)


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
        self.products = {}
        self.routes = {}
        self.orders = {}
        self.load_data()

    def load_data(self):
        """Load products and routes from JSON files"""
        try:
            # Load products
            with open(self.products_file, 'r') as f:
                products_data = json.load(f)
                for product_data in products_data:
                    product = Product(**product_data)
                    self.products[product.product_number] = product

            # Load routes
            with open(self.routes_file, 'r') as f:
                routes_data = json.load(f)
                for location, route_numbers in routes_data.items():
                    for route_number in route_numbers:
                        route = Route(
                            route_id=route_number,
                            location=location
                        )
                        self.routes[route_number] = route

            print(f"Loaded {len(self.products)} products and {len(self.routes)} routes.")
            return True
        except FileNotFoundError as e:
            print(f"Error loading data: {e}")
            print("Please ensure products.json and routes.json exist in the current directory.")
            return False
        except Exception as e:
            print(f"Error parsing JSON files: {e}")
            return False

    def get_available_routes(self) -> List[Route]:
        """Get all available routes"""
        return list(self.routes.values())

    def get_routes_for_location(self, location: str) -> List[Route]:
        """Get all routes available for a specific location"""
        location_routes = []
        for route in self.routes.values():
            if route.location == location:
                location_routes.append(route)
        return location_routes

    def get_available_locations(self) -> List[str]:
        """Get all available locations"""
        locations = set()
        for route in self.routes.values():
            locations.add(route.location)
        return sorted(list(locations))

    def get_products_for_route(self, route_id: int) -> List[Product]:
        """Get all products available for a specific route (all products are available for every route)"""
        if route_id not in self.routes:
            return []

        # All products are available for every route
        return list(self.products.values())

    def simulate_random_orders(self, max_products_per_order: int = 50, order_date: str = None, day_number: int = None) -> List[Order]:
        """Simulate random orders for every single route available"""
        simulated_orders = []
        routes = list(self.routes.values())
        products = list(self.products.values())

        # Define locations that should have guaranteed large orders (2+ trailers)
        large_order_locations = ['Greenville', 'Anderson', 'Gastonia', 'Spartanburg']


        for route in routes:
            # Select random products (1 to max_products_per_order)
            # Limit to realistic demo size - max 5 products per order
            num_products = random.randint(1, min(5, max_products_per_order, len(products)))
            selected_products = random.sample(products, num_products)

            order_items = []
            for product in selected_products:
                # Generate random units that are multiples of units_per_tray
                if route.location in large_order_locations:
                    # Guarantee large orders for specific locations (2-3 trailers max)
                    # We need 100-200 stacks total to get 2-3 trailers (realistic demo)
                    # With stack heights of 17-20, we need 1700-4000 trays total
                    # With 5 products max, each product needs 100-200 trays
                    min_trays = 100
                    max_trays = 200
                else:
                    # Regular random orders for other locations
                    min_trays = 1
                    max_trays = 20

                num_trays = random.randint(min_trays, max_trays)
                units_ordered = num_trays * product.units_per_tray

                order_items.append({
                    'product_number': product.product_number,
                    'units_ordered': units_ordered
                })

            # Create the order for this route
            order = self.create_order(route.route_id, order_items, order_date, day_number)
            if order:
                simulated_orders.append(order)

        return simulated_orders

    def get_system_stats(self):
        """Get system statistics for demo purposes"""
        stats = {
            'total_products': len(self.products),
            'total_routes': len(self.routes),
            'total_locations': len(self.get_available_locations()),
            'total_orders': len(self.orders)
        }

        if self.orders:
            stats['total_trays'] = sum(order.total_trays for order in self.orders.values())
            stats['total_stacks'] = sum(order.total_stacks for order in self.orders.values())

        stats['locations'] = {}
        for location in sorted(self.get_available_locations()):
            routes_in_location = len([r for r in self.routes.values() if r.location == location])
            stats['locations'][location] = routes_in_location

        return stats

    def calculate_order_quantities(self, product_number: int, units_ordered: int) -> Tuple[int, int]:
        """
        Calculate trays and stacks needed for a given number of units
        Returns: (trays_needed, stacks_needed)
        """
        if product_number not in self.products:
            return 0, 0

        product = self.products[product_number]

        # Calculate trays needed (using ceiling to round up)
        trays_needed = math.ceil(units_ordered / product.units_per_tray)

        # Calculate stacks needed
        stacks_needed = math.ceil(trays_needed / product.stack_height)

        return trays_needed, stacks_needed

    def create_order(self, route_id: int, order_items: List[Dict], order_date: str = None, day_number: int = None) -> Optional[Order]:
        """
        Create a new order
        order_items: List of dicts with 'product_number' and 'units_ordered'
        order_date: Optional date string in MM/DD/YYYY format
        day_number: Optional day number
        """
        if route_id not in self.routes:
            return None

        route = self.routes[route_id]
        # Create order ID with day number if provided
        if day_number:
            order_id = f"ORD_D{day_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Validate and process order items
        processed_items = []
        total_trays = 0
        total_stacks = 0

        for item in order_items:
            product_number = item.get('product_number')
            units_ordered = item.get('units_ordered', 0)

            if product_number not in self.products:
                continue

            # All products are available for every route
            if units_ordered <= 0:
                continue

            product = self.products[product_number]
            trays_needed, stacks_needed = self.calculate_order_quantities(product_number, units_ordered)

            # Validate that units are in increments of units_per_tray
            if units_ordered % product.units_per_tray != 0:
                units_ordered = math.ceil(units_ordered / product.units_per_tray) * product.units_per_tray
                trays_needed, stacks_needed = self.calculate_order_quantities(product_number, units_ordered)

            order_item = OrderItem(
                product_number=product_number,
                product_name=product.name,
                units_ordered=units_ordered,
                units_per_tray=product.units_per_tray,
                trays_needed=trays_needed,
                stack_height=product.stack_height,
                stacks_needed=stacks_needed,
                tray_type=product.tray_type
            )

            processed_items.append(order_item)
            total_trays += trays_needed
            total_stacks += stacks_needed

        if not processed_items:
            return None

        # Use provided date or current date
        if order_date:
            # Convert MM/DD/YYYY to YYYY-MM-DD format
            try:
                parsed_date = datetime.strptime(order_date, "%m/%d/%Y")
                if day_number:
                    formatted_date = f"{parsed_date.strftime('%Y-%m-%d')} Day {day_number} {datetime.now().strftime('%H:%M:%S')}"
                else:
                    formatted_date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                if day_number:
                    formatted_date = f"{datetime.now().strftime('%Y-%m-%d')} Day {day_number} {datetime.now().strftime('%H:%M:%S')}"
                else:
                    formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            if day_number:
                formatted_date = f"{datetime.now().strftime('%Y-%m-%d')} Day {day_number} {datetime.now().strftime('%H:%M:%S')}"
            else:
                formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        order = Order(
            order_id=order_id,
            route_id=route_id,
            location=route.location,
            order_date=formatted_date,
            items=processed_items,
            total_trays=total_trays,
            total_stacks=total_stacks
        )

        self.orders[order_id] = order
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID"""
        return self.orders.get(order_id)

    def get_all_orders(self) -> List[Order]:
        """Get all orders"""
        return list(self.orders.values())

    @staticmethod
    def get_order_summary(order: Order):
        """Get a detailed summary of an order"""
        summary = f"Order ID: {order.order_id}\n"
        summary += f"Route: {order.route_id}\n"
        summary += f"Location: {order.location}\n"
        summary += f"Order Date: {order.order_date}\n"
        summary += f"Total Trays: {order.total_trays}\n"
        summary += f"Total Stacks: {order.total_stacks}\n"
        summary += f"Items: {len(order.items)}"
        return summary

    def save_orders_to_file(self, filename: str = None):
        """Save all orders to a JSON file"""
        if filename is None:
            filename = f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        orders_data = {
            "orders": [asdict(order) for order in self.orders.values()],
            "export_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        with open(filename, 'w') as f:
            json.dump(orders_data, f, indent=2)

        return filename

    def load_orders_from_file(self, filename: str):
        """Load orders from a JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            loaded_count = 0
            for order_data in data.get("orders", []):
                # Convert items back to OrderItem objects
                items = [OrderItem(**item_data) for item_data in order_data["items"]]
                order_data["items"] = items

                order = Order(**order_data)
                self.orders[order.order_id] = order
                loaded_count += 1

            return True
        except Exception as e:
            return False


def main():
    """Main interactive interface for the Order System"""
    order_system = OrderSystem()

    if not order_system.products or not order_system.routes:
        print("Failed to load products or routes. Please check your JSON files.")
        return

    while True:
        print("\n" + "="*60)
        print("VIRTUAL RELAY ORDER SYSTEM - DEMO")
        print("="*60)
        print("1. View Available Routes")
        print("2. View Products for Route")
        print("3. Simulate Random Orders (Demo)")
        print("4. View All Orders")
        print("5. View Order Summary")
        print("6. System Statistics")
        print("7. Save Orders to File")
        print("8. Load Orders from File")
        print("9. Exit")
        print("="*60)

        choice = input("Enter your choice (1-9): ").strip()

        if choice == "1":
            routes = order_system.get_available_routes()
            print(f"\nAvailable Routes ({len(routes)}):")
            print("-" * 50)
            for i, route in enumerate(routes, 1):
                print(f"{i}. Route {route.route_id} - {route.location}")

        elif choice == "2":
            routes = order_system.get_available_routes()
            if not routes:
                print("No routes available.")
                continue

            print("\nSelect a route:")
            for i, route in enumerate(routes, 1):
                print(f"{i}. Route {route.route_id} - {route.location}")

            try:
                route_choice = int(input("Enter route number: ")) - 1
                selected_route = routes[route_choice]
                products = order_system.get_products_for_route(selected_route.route_id)

                print(f"\nProducts available for Route {selected_route.route_id} ({selected_route.location}):")
                print("-" * 80)
                print(f"{'Product Name':<25} {'Product #':<12} {'Units/Tray':<10} {'Stack Height':<12} {'Tray Type':<12}")
                print("-" * 80)

                for product in products:
                    print(f"{product.name:<25} {product.product_number:<12} {product.units_per_tray:<10} {product.stack_height:<12} {product.tray_type:<12}")

            except (ValueError, IndexError):
                print("Invalid route selection.")

        elif choice == "3":
            print("\n" + "="*50)
            print("SIMULATE RANDOM ORDERS - DEMO")
            print("="*50)
            print("This will create random orders for EVERY SINGLE ROUTE available.")
            print("Units are ordered in multiples of units_per_tray for each product.")
            print(f"Total routes available: {len(order_system.get_available_routes())}")

            try:
                max_products = int(input("Max products per order? (default 3): ") or "3")

                print(f"\nGenerating orders for all routes...")
                simulated_orders = order_system.simulate_random_orders(max_products)

                print(f"\n✅ Successfully created {len(simulated_orders)} orders!")
                print("(One order for each route)")

                # Show summary by location
                location_summary = {}
                for order in simulated_orders:
                    if order.location not in location_summary:
                        location_summary[order.location] = {'orders': 0, 'trays': 0, 'stacks': 0}
                    location_summary[order.location]['orders'] += 1
                    location_summary[order.location]['trays'] += order.total_trays
                    location_summary[order.location]['stacks'] += order.total_stacks

                print(f"\nSummary by Location:")
                print("-" * 60)
                for location, stats in sorted(location_summary.items()):
                    print(f"{location}: {stats['orders']} orders, {stats['trays']} trays, {stats['stacks']} stacks")

                print(f"\nAll orders have been added to the system.")
                print("Use option 4 to view detailed order information.")

            except ValueError:
                print("Please enter valid numbers.")

        elif choice == "4":
            orders = order_system.get_all_orders()
            if not orders:
                print("No orders created yet.")
                continue

            print(f"\nAll Orders ({len(orders)}):")
            print("-" * 80)
            for order in orders:
                print(f"Order ID: {order.order_id}")
                print(f"Route: {order.route_id} | Location: {order.location}")
                print(f"Date: {order.order_date}")
                print(f"Items: {len(order.items)} | Total Trays: {order.total_trays} | Total Stacks: {order.total_stacks}")
                print("-" * 80)

        elif choice == "5":
            if not order_system.orders:
                print("No orders created yet.")
                continue

            print("\nSelect an order to view:")
            orders = order_system.get_all_orders()
            for i, order in enumerate(orders, 1):
                print(f"{i}. {order.order_id} - Route {order.route_id} ({order.location})")

            try:
                order_choice = int(input("Enter order number: ")) - 1
                selected_order = orders[order_choice]
                print(order_system.get_order_summary(selected_order))
            except (ValueError, IndexError):
                print("Invalid order selection.")

        elif choice == "6":
            stats = order_system.get_system_stats()
            print(f"Total Products: {stats['total_products']}")
            print(f"Total Routes: {stats['total_routes']}")
            print(f"Total Locations: {stats['total_locations']}")
            print(f"Total Orders: {stats['total_orders']}")
            if 'total_trays' in stats:
                print(f"Total Trays: {stats['total_trays']}")
                print(f"Total Stacks: {stats['total_stacks']}")

        elif choice == "7":
            if not order_system.orders:
                print("No orders to save.")
                continue

            filename = input("Enter filename (or press Enter for auto-generated name): ").strip()
            if not filename:
                filename = None

            order_system.save_orders_to_file(filename)

        elif choice == "8":
            filename = input("Enter filename to load: ").strip()
            order_system.load_orders_from_file(filename)

        elif choice == "9":
            print("Exiting Order System Demo. Goodbye!")
            break

        else:
            print("Invalid choice. Please select 1-9.")


if __name__ == "__main__":
    main()
