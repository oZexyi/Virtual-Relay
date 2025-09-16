from math import ceil
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import sys

# Add the current directory to the path to import orders
sys.path.append(os.path.dirname(__file__))
from orders import OrderSystem, Order, OrderItem

# Trailer with its associated info (stack count, overload info, etc.)
class Trailer:
    def __init__(self, number, stacks, overload_from=None, order_info=None):
        self.number = number
        self.stacks = stacks
        self.overload_from = overload_from
        self.order_info = order_info  # Store order information for automated relays
        self.ld_number = random.randint(100000000, 999999999)
        self.trailer_number = ""
        self.seal_number = ""
        self.dispatched = False  # Track if trailer has been dispatched
        self.dispatch_timestamp = None  # When the trailer was dispatched
# Shipping location and stack/tray calculations
class Location:
    def __init__(self, name, bread_trays=0, bulk_trays=0, cake_pallets=0, orders=None):
        self.name = name
        self.bread_trays = bread_trays
        self.bulk_trays = bulk_trays
        self.cake_pallets = cake_pallets
        self.orders = orders or []  # Store orders for automated relay creation
        self.total_bread_stacks = ceil(bread_trays / 17) if bread_trays > 0 else 0
        self.total_bulk_stacks = ceil(bulk_trays / 30) if bulk_trays > 0 else 0
        self.total_stacks = self.total_bread_stacks + self.total_bulk_stacks
        self.total_trays = (bread_trays + bulk_trays) if (bread_trays or bulk_trays) else 0
        self.trailers = []
    # Assign trailers based on stack count and cake pallets
    def assign_trailers(self, order_info=None):
        stacks_remaining = self.total_stacks
        trailer_number = 1
        while stacks_remaining > 0:
            count = min(stacks_remaining, 98)
            self.trailers.append(Trailer(trailer_number, count, order_info=order_info))
            stacks_remaining -= count
            trailer_number += 1
    
    # Create location from orders (automated relay creation)
    @classmethod
    def from_orders(cls, location_name: str, orders: List[Order]):
        """Create a Location object from a list of orders for automated relay creation"""
        total_trays = 0
        total_stacks = 0
        
        for order in orders:
            for item in order.items:
                total_trays += item.trays_needed
                total_stacks += item.stacks_needed
        
        location = cls(
            name=location_name,
            bread_trays=0,
            bulk_trays=0,
            cake_pallets=0,
            orders=orders
        )
        
        # Override totals with per-product computed values
        location.total_bread_stacks = 0
        location.total_bulk_stacks = 0
        location.total_stacks = total_stacks
        location.total_trays = total_trays
        
        # Assign trailers with order information
        location.assign_trailers(order_info=orders)
        return location
    # Placeholder for FirstFleet tray information
    def finalize_trailers(self):
        for trailer in self.trailers:
            trailer.bread_trays = None
            trailer.bulk_trays = None
    # Display relay information
    def display_relay(self):
        for trailer in self.trailers:
            # If trailer has an overload, output overload info
            overload_text = f"- Overload [{trailer.overload_from[0]} {trailer.overload_from[1]} stacks]" if trailer.overload_from else ""
            
            # Add order information if available (automated relay)
            order_text = ""
            if trailer.order_info:
                order_text = f" (Auto-generated from {len(trailer.order_info)} orders)"
            
            # Print trailer details (LD number, stack count)
            print(f"{self.name}:\nLD {trailer.ld_number} - Trailer #{trailer.number}: {trailer.stacks} stacks {overload_text}{order_text}")
            # Print empty input fields for trailer number and seal number
            print(f" Trailer #: [ {trailer.trailer_number} ] Seal #: [ {trailer.seal_number} ]")
    
    # Display detailed order information for automated relays
    def display_order_details(self):
        if not self.orders:
            return
        
        print(f"\n{'='*60}")
        print(f"ORDER DETAILS FOR {self.name.upper()}")
        print(f"{'='*60}")
        
        for order in self.orders:
            print(f"\nOrder ID: {order.order_id}")
            print(f"Route: {order.route_id} | Date: {order.order_date}")
            print(f"Total Trays: {order.total_trays} | Total Stacks: {order.total_stacks}")
            print("-" * 40)
            
            for item in order.items:
                print(f"  {item.product_name}: {item.units_ordered} units, {item.trays_needed} trays, {item.stacks_needed} stacks")
        
        print(f"{'='*60}")


class RelaySystem:
    """Main relay system that integrates with the order system for automation"""
    
    def __init__(self, orders_file_path: str = None):
        self.order_system = OrderSystem()
        self.locations = []
        self.orders_file_path = orders_file_path
        
        # Load orders if file path is provided
        if orders_file_path and os.path.exists(orders_file_path):
            self.order_system.load_orders_from_file(orders_file_path)
    
    def get_available_dates(self) -> List[str]:
        """Get all available dates from orders"""
        dates = set()
        for order in self.order_system.get_all_orders():
            # Extract date from order_date (format: YYYY-MM-DD HH:MM:SS)
            date_str = order.order_date.split(' ')[0]
            dates.add(date_str)
        return sorted(list(dates))
    
    def get_orders_by_date(self, date: str) -> List[Order]:
        """Get all orders for a specific date"""
        orders = []
        for order in self.order_system.get_all_orders():
            order_date = order.order_date.split(' ')[0]
            if order_date == date:
                orders.append(order)
        return orders
    
    def get_orders_by_location_and_date(self, location: str, date: str) -> List[Order]:
        """Get all orders for a specific location and date"""
        orders = []
        for order in self.order_system.get_all_orders():
            order_date = order.order_date.split(' ')[0]
            if order_date == date and order.location == location:
                orders.append(order)
        return orders
    
    def create_automated_relay(self, date: str, day_number: int = None) -> List[Location]:
        """Create automated relay from orders for a specific date"""
        orders = self.get_orders_by_date(date)
        
        if not orders:
            print(f"No orders found for date {date}")
            return []
        
        # Group orders by location
        location_orders = {}
        for order in orders:
            if order.location not in location_orders:
                location_orders[order.location] = []
            location_orders[order.location].append(order)
        
        # Create Location objects from orders
        locations = []
        for location_name, location_orders_list in location_orders.items():
            location = Location.from_orders(location_name, location_orders_list)
            locations.append(location)
        
        self.locations = locations
        return locations
    
    def display_relay_summary(self, date: str, day_number: int = None):
        """Display a summary of the automated relay"""
        if not self.locations:
            print("No relay created yet. Use 'Create Relay' first.")
            return
        
        day_text = f"Day {day_number} " if day_number else ""
        print(f"\n{'='*80}")
        print(f"AUTOMATED RELAY SUMMARY - {day_text}{date}")
        print(f"{'='*80}")
        
        total_trailers = 0
        total_stacks = 0
        
        for location in self.locations:
            total_trailers += len(location.trailers)
            total_stacks += location.total_stacks
            
            print(f"\n{location.name}:")
            print(f"  Orders: {len(location.orders)}")
            total_trays = getattr(location, 'total_trays', sum(item.trays_needed for o in location.orders for item in o.items))
            print(f"  Total Trays: {total_trays}")
            print(f"  Total Stacks: {location.total_stacks}")
            print(f"  Trailers: {len(location.trailers)}")
        
        print(f"\n{'='*80}")
        print(f"TOTALS: {total_trailers} trailers, {total_stacks} stacks")
        print(f"{'='*80}")
    
    def display_full_relay(self):
        """Display the complete relay with all details"""
        if not self.locations:
            print("No relay created yet. Use 'Create Relay' first.")
            return
        
        for location in self.locations:
            location.display_relay()
            print()  # Add spacing between locations
    
    def display_order_details(self):
        """Display detailed order information for all locations"""
        if not self.locations:
            print("No relay created yet. Use 'Create Relay' first.")
            return
        
        for location in self.locations:
            location.display_order_details()
    
    def add_overload(self, location_name: str, trailer_number: int, overload_from: tuple):
        """Add overload information to a specific trailer (manual input)"""
        for location in self.locations:
            if location.name == location_name:
                for trailer in location.trailers:
                    if trailer.number == trailer_number:
                        trailer.overload_from = overload_from
                        print(f"Added overload to {location_name} Trailer #{trailer_number}")
                        return
        print(f"Trailer not found: {location_name} Trailer #{trailer_number}")
    
    def interactive_menu(self):
        """Interactive menu for the relay system"""
        while True:
            print("\n" + "="*80)
            print("VIRTUAL RELAY SYSTEM - AUTOMATED")
            print("="*80)
            print("1. Create Relay (Automated from Orders)")
            print("2. View Relay Summary")
            print("3. View Full Relay")
            print("4. View Order Details")
            print("5. Add Overload (Manual Input)")
            print("6. Load Orders from File")
            print("7. View Available Dates")
            print("8. Exit")
            print("="*80)
            
            choice = input("Enter your choice (1-8): ").strip()
            
            if choice == "1":
                self._create_relay_menu()
            elif choice == "2":
                self.display_relay_summary("", None)
            elif choice == "3":
                self.display_full_relay()
            elif choice == "4":
                self.display_order_details()
            elif choice == "5":
                self._add_overload_menu()
            elif choice == "6":
                self._load_orders_menu()
            elif choice == "7":
                self._view_dates_menu()
            elif choice == "8":
                print("Exiting Virtual Relay System. Goodbye!")
                break
            else:
                print("Invalid choice. Please select 1-8.")
    
    def _create_relay_menu(self):
        """Menu for creating automated relay"""
        dates = self.get_available_dates()
        
        if not dates:
            print("No orders available. Please load orders first.")
            return
        
        print(f"\nAvailable dates with orders:")
        for i, date in enumerate(dates, 1):
            orders_count = len(self.get_orders_by_date(date))
            print(f"{i}. {date} ({orders_count} orders)")
        
        try:
            date_choice = int(input("Select date (number): ")) - 1
            selected_date = dates[date_choice]
            
            day_number = input("Enter day number (optional, e.g., 1): ").strip()
            day_number = int(day_number) if day_number else None
            
            print(f"\nCreating automated relay for {selected_date}...")
            locations = self.create_automated_relay(selected_date, day_number)
            
            if locations:
                print(f"✅ Successfully created relay with {len(locations)} locations!")
                self.display_relay_summary(selected_date, day_number)
            else:
                print("❌ Failed to create relay.")
                
        except (ValueError, IndexError):
            print("Invalid selection.")
    
    def _add_overload_menu(self):
        """Menu for adding overload information"""
        if not self.locations:
            print("No relay created yet. Create a relay first.")
            return
        
        print(f"\nAvailable locations:")
        for i, location in enumerate(self.locations, 1):
            print(f"{i}. {location.name}")
        
        try:
            location_choice = int(input("Select location (number): ")) - 1
            selected_location = self.locations[location_choice]
            
            print(f"\nTrailers for {selected_location.name}:")
            for trailer in selected_location.trailers:
                print(f"  Trailer #{trailer.number}: {trailer.stacks} stacks")
            
            trailer_number = int(input("Enter trailer number: "))
            overload_location = input("Enter overload from location: ").strip()
            overload_stacks = int(input("Enter overload stacks: "))
            
            self.add_overload(selected_location.name, trailer_number, (overload_location, overload_stacks))
            
        except (ValueError, IndexError):
            print("Invalid input.")
    
    def _load_orders_menu(self):
        """Menu for loading orders from file"""
        filename = input("Enter orders filename: ").strip()
        if filename:
            success = self.order_system.load_orders_from_file(filename)
            if success:
                print(f"✅ Loaded orders successfully!")
                dates = self.get_available_dates()
                print(f"Available dates: {', '.join(dates)}")
            else:
                print("❌ Failed to load orders.")
    
    def _view_dates_menu(self):
        """Menu for viewing available dates"""
        dates = self.get_available_dates()
        
        if not dates:
            print("No orders available.")
            return
        
        print(f"\nAvailable dates with orders:")
        for date in dates:
            orders = self.get_orders_by_date(date)
            locations = set(order.location for order in orders)
            print(f"  {date}: {len(orders)} orders, {len(locations)} locations")
            for location in sorted(locations):
                location_orders = [o for o in orders if o.location == location]
                total_stacks = sum(o.total_stacks for o in location_orders)
                print(f"    - {location}: {len(location_orders)} orders, {total_stacks} stacks")


def main():
    """Main function to run the relay system"""
    print("Virtual Relay System - Automated")
    print("="*50)
    
    # Check if orders file exists in current directory
    orders_file = os.path.join(os.path.dirname(__file__), 'orders_*.json')
    
    relay_system = RelaySystem()
    relay_system.interactive_menu()


if __name__ == "__main__":
    main()