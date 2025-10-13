"""
Virtual Relay System - Main Application
Automated shipping relay management system for Flowers Foods operations.

Features:
- Order management with 252+ products across 135+ routes
- Automated trailer assignment with 98-stack capacity limits
- Real-time dispatch tracking with color-coded status
- API integration for North Carolina timezone
- Interactive web interface with Streamlit
"""

import os
import json
import streamlit as st
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from orders import OrderSystem, Order, OrderItem
from relay_logic import RelaySystem, Location


# ============================================================================
# CORE BUSINESS LOGIC
# ============================================================================

def analyze_inbound_products() -> Optional[Dict]:
    """
    Analyze orders to identify products that need to be ordered from other plants.
    
    Returns:
        Dict mapping origin_plant -> list of products with totals
    """
    try:
        # Load products and orders data
        with open("products.json", 'r') as f:
            products_data = json.load(f)
        with open("orders.json", 'r') as f:
            orders_data = json.load(f)
        
        # Create product lookup for efficient access
        products_lookup = {p['product_number']: p for p in products_data}
        
        # Analyze each order for inbound products (not from plant 191)
        inbound_products = {}
        
        for order in orders_data:
            for item in order['items']:
                product_number = item['product_number']
                
                if product_number in products_lookup:
                    product_info = products_lookup[product_number]
                    origin_plant = product_info['origin_plant']
                    
                    # Only track products from other plants
                    if origin_plant != 191:
                        if origin_plant not in inbound_products:
                            inbound_products[origin_plant] = {}
                        
                        product_key = f"{product_number}_{product_info['name']}"
                        
                        if product_key not in inbound_products[origin_plant]:
                            inbound_products[origin_plant][product_key] = {
                                'product_number': product_number,
                                'product_name': product_info['name'],
                                'origin_plant': origin_plant,
                                'total_units': 0,
                                'total_trays': 0,
                                'total_stacks': 0
                            }
                        
                        # Accumulate totals
                        inbound_products[origin_plant][product_key]['total_units'] += item['units_ordered']
                        inbound_products[origin_plant][product_key]['total_trays'] += item['trays_needed']
                        inbound_products[origin_plant][product_key]['total_stacks'] += item['stacks_needed']
        
        # Convert to list format for display
        result = {}
        for origin_plant, products in inbound_products.items():
            result[origin_plant] = list(products.values())
        
        return result
        
    except Exception as e:
        st.error(f"Error analyzing inbound products: {str(e)}")
        return None


# ============================================================================
# SYSTEM INITIALIZATION
# ============================================================================

def initialize_systems() -> str:
    """Initialize the order and relay systems."""
    global order_system, relay_system
    try:
        # Clean up old order files on startup
        cleanup_old_order_files()

        order_system = OrderSystem()
        relay_system = RelaySystem()
        relay_system.order_system = order_system
        return f"System ready: {len(order_system.products)} products, {len(order_system.routes)} routes."
    except Exception as e:
        return f"Error initializing system: {str(e)}"


def cleanup_old_order_files():
    """Clean up duplicate order files from previous runs."""
    try:
        import glob
        import os

        # Find all order files
        order_files = glob.glob("all_orders_*.json") + glob.glob("confirmed_orders_*.json") + glob.glob("orders_*.json")

        if not order_files:
            return

        print(f"Found {len(order_files)} order files to clean up")

        # Group files by base name (without timestamp variations)
        file_groups = {}
        for file in order_files:
            base_name = file.replace('.json', '')
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(file)

        # Keep only the newest file in each group
        kept_files = []
        deleted_files = []

        for base_name, files in file_groups.items():
            if len(files) > 1:
                # Sort by modification time (newest first)
                files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                
                # Keep the newest, delete the rest
                kept_files.append(files[0])
                for old_file in files[1:]:
                    try:
                        os.remove(old_file)
                        deleted_files.append(old_file)
                        print(f"Deleted duplicate file: {old_file}")
                    except Exception as e:
                        print(f"Error deleting {old_file}: {e}")
            else:
                kept_files.append(files[0])

        print(f"Cleanup complete: {len(deleted_files)} duplicate files deleted, {len(kept_files)} unique files kept")

    except Exception as e:
        print(f"Error during cleanup: {e}")


# ============================================================================
# ORDER MANAGEMENT
# ============================================================================

def create_orders_for_date_and_day(order_date: str, order_day: str, max_products: int) -> Tuple[str, List[str]]:
    """
    Create orders for a specific date and day.
    
    Args:
        order_date: Date in MM/DD/YYYY format
        order_day: Day number (1, 2, 4, 5, or 6)
        max_products: Maximum products per route
        
    Returns:
        Tuple of (status_message, available_dates)
    """
    try:
        # Validate inputs
        if not order_date or not order_date.strip():
            return "Please enter a date in MM/DD/YYYY format (e.g., 12/25/2024)", []

        if not order_day:
            return "Please select a day from the dropdown (1, 2, 4, 5, or 6)", []

        # Validate date format
        try:
            datetime.strptime(order_date.strip(), "%m/%d/%Y")
        except ValueError:
            return "Invalid date format. Please use MM/DD/YYYY format (e.g., 12/25/2024)", []

        # Validate day number
        try:
            day_num = int(order_day)
            if day_num not in [1, 2, 4, 5, 6]:
                return "Invalid day selected. Please select Day 1, 2, 4, 5, or 6.", []
        except ValueError:
            return "Invalid day selected. Please select Day 1, 2, 4, 5, or 6.", []

        if max_products is None or max_products <= 0:
            max_products = 235  # Use all products for comprehensive order generation

        # Initialize systems
        msg = ensure_order_system()
        ensure_relay_system()

        # Create orders with the specified date and day
        orders = order_system.simulate_random_orders(max_products, order_date.strip(), day_num)

        # Save orders to JSON file with confirmed date/day information
        if orders:
            save_orders_with_confirmation(orders, order_date.strip(), day_num)

        # Get dates from in-memory system
        dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders()))

        return f"{msg}\nCreated {len(orders)} orders for {order_date} Day {day_num} with up to {max_products} products per route.\n\nOrders saved to JSON file with confirmed date/day for relay generation.", dates

    except Exception as e:
        return f"Error creating orders: {str(e)}", []


def ensure_order_system() -> str:
    """Ensure order system is initialized."""
    global order_system
    try:
        if order_system is None:
            order_system = OrderSystem()
        return f"Catalog ready: {len(order_system.products)} products, {len(order_system.routes)} routes."
    except Exception as e:
        return f"Error loading catalog: {str(e)}"


def ensure_relay_system() -> None:
    """Ensure relay system is initialized."""
    global relay_system
    try:
        if relay_system is None:
            relay_system = RelaySystem()
        # Keep relay_system's order_system in sync with global order_system
        if order_system is not None:
            relay_system.order_system = order_system
    except Exception as e:
        raise Exception(f"Error initializing relay system: {str(e)}")


# ============================================================================
# RELAY MANAGEMENT
# ============================================================================

def create_relay_from_orders_data(orders_data: List[Dict]) -> List[Location]:
    """
    Create relay locations from orders data loaded from JSON files.
    
    Args:
        orders_data: List of order dictionaries from JSON
        
    Returns:
        List of Location objects with assigned trailers
    """
    try:
        # Group orders by location
        location_orders = {}
        for order_data in orders_data:
            location = order_data.get('location', 'Unknown')
            if location not in location_orders:
                location_orders[location] = []
            location_orders[location].append(order_data)

        # Create Location objects from orders
        locations = []
        for location_name, location_orders_list in location_orders.items():
            # Calculate total trays and stacks for this location
            total_trays = 0
            total_stacks = 0

            for order_data in location_orders_list:
                total_trays += order_data.get('total_trays', 0)
                total_stacks += order_data.get('total_stacks', 0)

            print(f"Location {location_name}: {total_trays} trays, {total_stacks} stacks")

            # Create location with calculated totals
            location = Location(location_name, bread_trays=total_trays, bulk_trays=0, cake_pallets=0)
            location.total_stacks = total_stacks  # Override with calculated stacks

            # Assign trailers based on stack count
            location.assign_trailers()

            print(f"  Assigned {len(location.trailers)} trailers")
            for trailer in location.trailers:
                print(f"    Trailer #{trailer.number}: {trailer.stacks} stacks")

            locations.append(location)

        return locations

    except Exception as e:
        print(f"Error creating relay from orders data: {e}")
        return []


# ============================================================================
# API INTEGRATION
# ============================================================================

def get_north_carolina_datetime() -> Dict:
    """
    Get current date and time from WorldTimeAPI for North Carolina (Eastern Time).
    
    Returns:
        Dict with success status, datetime, timezone, and error info
    """
    try:
        # API Request: North Carolina uses Eastern Time (America/New_York)
        api_url = "http://worldtimeapi.org/api/timezone/America/New_York"
        print("🌍 API Call: Fetching North Carolina (Eastern Time) from WorldTimeAPI")

        # Make the API request with timeout
        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            # Parse JSON response
            api_data = response.json()
            datetime_str = api_data.get("datetime", "")
            timezone_name = "North Carolina (Eastern Time)"

            print(f"✅ API Success: Got North Carolina time {datetime_str}")

            return {
                "success": True,
                "datetime": datetime_str,
                "timezone": timezone_name,
                "error": None
            }
        else:
            error_msg = f"API returned status code {response.status_code}"
            print(f"API Error: {error_msg}")
            return {
                "success": False,
                "datetime": None,
                "timezone": "North Carolina (Eastern Time)",
                "error": error_msg
            }

    except requests.exceptions.Timeout:
        error_msg = "API request timed out (network too slow)"
        print(f"Network Error: {error_msg}")
        return {
            "success": False,
            "datetime": None,
            "timezone": "North Carolina (Eastern Time)",
            "error": error_msg
        }
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {str(e)}"
        print(f"Network Error: {error_msg}")
        return {
            "success": False,
            "datetime": None,
            "timezone": "North Carolina (Eastern Time)",
            "error": error_msg
        }
    except json.JSONDecodeError:
        error_msg = "API returned invalid JSON data"
        print(f"Data Error: {error_msg}")
        return {
            "success": False,
            "datetime": None,
            "timezone": "North Carolina (Eastern Time)",
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"Unexpected Error: {error_msg}")
        return {
            "success": False,
            "datetime": None,
            "timezone": "North Carolina (Eastern Time)",
            "error": error_msg
        }


def get_north_carolina_date_for_orders() -> str:
    """
    Get current North Carolina date in MM/DD/YYYY format for order creation.
    
    Returns:
        Current date in MM/DD/YYYY format
    """
    try:
        # Get current time from North Carolina via API
        api_result = get_north_carolina_datetime()

        if api_result["success"]:
            # Convert API datetime to MM/DD/YYYY format
            formatted_date = format_api_datetime_for_orders(api_result["datetime"])
            print(f"Using API date for orders: {formatted_date}")
            return formatted_date
        else:
            # Fallback: Use local system time if API fails
            fallback_date = datetime.now().strftime("%m/%d/%Y")
            print(f"API failed, using local time: {fallback_date}")
            return fallback_date

    except Exception as e:
        # Always provide a fallback
        fallback_date = datetime.now().strftime("%m/%d/%Y")
        print(f"Error getting API date, using local time: {fallback_date}")
        return fallback_date


def format_api_datetime_for_orders(api_datetime_str: str) -> str:
    """
    Convert API datetime to MM/DD/YYYY format for order creation.
    
    Args:
        api_datetime_str: ISO datetime string from API
        
    Returns:
        Date in MM/DD/YYYY format
    """
    try:
        # Remove timezone info and parse the datetime
        datetime_part = api_datetime_str.split('+')[0].split('-')[0:3]
        if len(datetime_part) >= 3:
            clean_datetime = '-'.join(datetime_part)
        else:
            clean_datetime = api_datetime_str.split('T')[0]

        # Parse the ISO date
        parsed_date = datetime.fromisoformat(clean_datetime)

        # Convert to MM/DD/YYYY format
        formatted_date = parsed_date.strftime("%m/%d/%Y")

        print(f"🔄 Date Conversion: {api_datetime_str} → {formatted_date}")
        return formatted_date

    except Exception as e:
        print(f"❌ Date Conversion Error: {str(e)}")
        # Fallback: Return current date if conversion fails
        return datetime.now().strftime("%m/%d/%Y")


# ============================================================================
# DATA PERSISTENCE
# ============================================================================

def save_orders_with_confirmation(orders: List[Order], date_str: str, day_num: int):
    """
    Save all orders to a single comprehensive JSON file with confirmed date/day information.
    
    Args:
        orders: List of Order objects
        date_str: Date string (MM/DD/YYYY)
        day_num: Day number
    """
    try:
        # Convert date to filename format (MM-DD-YYYY)
        filename_date = date_str.replace("/", "-")
        filename = f"orders_{filename_date}_Day{day_num}.json"

        # Clean up any existing order files
        import glob
        all_order_files = glob.glob("orders_*.json")
        for old_file in all_order_files:
            try:
                os.remove(old_file)
                print(f"Deleted old file: {old_file}")
            except Exception as e:
                print(f"Error deleting {old_file}: {e}")

        # Convert orders to JSON-serializable format
        orders_data = []
        for order in orders:
            order_dict = {
                "order_id": order.order_id,
                "route_id": order.route_id,
                "location": order.location,
                "order_date": order.order_date,
                "total_trays": order.total_trays,
                "total_stacks": order.total_stacks,
                "items": []
            }

            # Add order items
            for item in order.items:
                item_dict = {
                    "product_number": item.product_number,
                    "product_name": item.product_name,
                    "units_ordered": item.units_ordered,
                    "units_per_tray": item.units_per_tray,
                    "trays_needed": item.trays_needed,
                    "stack_height": item.stack_height,
                    "stacks_needed": item.stacks_needed,
                    "tray_type": item.tray_type
                }
                order_dict["items"].append(item_dict)

            orders_data.append(order_dict)

        # Create data structure with metadata
        file_data = {
            "orders": orders_data,
            "metadata": {
                "total_orders": len(orders),
                "confirmed_date": date_str,
                "confirmed_day": day_num,
                "generation_timestamp": datetime.now().isoformat()
            }
        }

        # Save to JSON file
        with open(filename, 'w') as f:
            json.dump(file_data, f, indent=2)

        print(f"Saved {len(orders)} orders to file: {filename}")

    except Exception as e:
        print(f"Error saving orders: {e}")


# ============================================================================
# STREAMLIT APPLICATION
# ============================================================================

# Configure Streamlit for deployment
st.set_page_config(
    page_title="Virtual Relay System",
    page_icon="🚛",
    layout="wide"
)

# Configure for Render deployment
import os
if os.getenv("RENDER"):
    st.config.set_option("server.port", int(os.getenv("PORT", 10000)))
    st.config.set_option("server.address", "0.0.0.0")
    st.config.set_option("server.headless", True)
    st.config.set_option("browser.gatherUsageStats", False)

# Initialize session state
def initialize_session_state():
    """Initialize session state safely."""
    try:
        if 'order_system' not in st.session_state:
            st.session_state.order_system = None
        if 'relay_system' not in st.session_state:
            st.session_state.relay_system = None
        if 'current_locations' not in st.session_state:
            st.session_state.current_locations = []
        return True
    except Exception as e:
        st.error(f"Error initializing session state: {str(e)}")
        return False

def initialize_streamlit_systems():
    """Initialize systems for Streamlit."""
    try:
        if st.session_state.order_system is None:
            st.session_state.order_system = OrderSystem()
        if st.session_state.relay_system is None:
            st.session_state.relay_system = RelaySystem()
            st.session_state.relay_system.order_system = st.session_state.order_system
        return True
    except Exception as e:
        st.error(f"Error initializing system: {str(e)}")
        return False

# Initialize session state
try:
    if not initialize_session_state():
        st.error("Failed to initialize session state. Please refresh the page.")
        st.stop()
except Exception as e:
    st.error(f"Critical error initializing session state: {str(e)}")
    st.stop()

# Main Streamlit interface
st.title("🚛 Virtual Relay System")
st.markdown("**Manufacturing Logistics Management System**")

# Initialize systems
try:
    if not initialize_streamlit_systems():
        st.error("Failed to initialize systems. Please refresh the page.")
        st.stop()
except Exception as e:
    st.error(f"Critical error initializing systems: {str(e)}")
    st.stop()

# Check if systems are available
if not (hasattr(st.session_state, 'order_system') and st.session_state.order_system is not None and
        hasattr(st.session_state, 'relay_system') and st.session_state.relay_system is not None):
    st.error("⚠️ Systems not properly initialized. Please refresh the page.")
    st.info("If the problem persists, check the debug information in the sidebar.")
    st.stop()

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["System Overview", "Order Management", "Relay Management"])

if page == "System Overview":
    st.header("System Overview")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("System Status")
        if hasattr(st.session_state, 'order_system') and st.session_state.order_system is not None:
            st.success("✅ System Ready")
            st.info(f"Products: {len(st.session_state.order_system.products)}")
            st.info(f"Routes: {len(st.session_state.order_system.routes)}")
            st.info(f"Locations: {len(st.session_state.order_system.get_available_locations())}")
        else:
            st.error("❌ System Not Ready")
            st.info("Please refresh the page to reinitialize the system.")

    with col2:
        st.subheader("System Capabilities")
        st.markdown("""
        - **Products**: 252+ unique items
        - **Routes**: 135+ delivery routes
        - **Locations**: Multi-location support
        - **API Integration**: North Carolina timezone
        - **Data Persistence**: JSON file storage
        - **Trailer Management**: 98-stack limit with overflow
        """)

    st.subheader("Getting Started")
    st.markdown("""
    1. **Order Management**: Get today's date, select day, confirm selection, then generate orders
    2. **Relay Management**: Select generated orders to create automated relay assignments
    3. **Professional Workflow**: Complete order-to-relay process with persistent data storage
    """)

    # System management buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh System Status"):
            st.rerun()
    with col2:
        if st.button("Clean Up Duplicate Files"):
            cleanup_old_order_files()
            st.info("Cleanup completed")

elif page == "Order Management":
    st.header("Order Management")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Create Orders")

        # Date input
        order_date = st.text_input(
            "Order Date", 
            value=get_north_carolina_date_for_orders(),
            placeholder="MM/DD/YYYY (e.g., 12/25/2024)",
            help="Enter the date for the orders"
        )

        # Day selection
        order_day = st.selectbox(
            "Select Day",
            options=["1", "2", "4", "5", "6"],
            index=0,
            help="Select the day number for the orders"
        )

        st.info("📋 Order System: Immutable - Orders are generated randomly")

    with col2:
        st.subheader("Actions")

        if st.button("Get Today's Date"):
            today_date = get_north_carolina_date_for_orders()
            st.session_state.today_date = today_date
            st.rerun()

        if st.button("Generate Random Orders", type="primary"):
            if order_date and order_day:
                try:
                    # Validate date format
                    datetime.strptime(order_date, "%m/%d/%Y")

                    # Debug: Show system info
                    total_routes = len(st.session_state.order_system.routes)
                    total_locations = len(st.session_state.order_system.get_available_locations())
                    st.info(f"🔍 System has {total_routes} routes across {total_locations} locations")

                    # Create orders with larger sizes to generate multiple trailers
                    orders = st.session_state.order_system.simulate_random_orders(
                        5, order_date, int(order_day)  # 5 products per route for larger orders
                    )

                    st.success(f"✅ Created {len(orders)} orders for {order_date} Day {order_day}")

                    # Debug: Show order distribution
                    locations_in_orders = set(order.location for order in orders)
                    st.info(f"📊 Orders created for {len(locations_in_orders)} locations: {', '.join(sorted(locations_in_orders))}")

                    # Save orders to single JSON file
                    filename = "orders.json"
                    try:
                        # Load existing orders from file
                        existing_orders = []
                        if os.path.exists(filename):
                            with open(filename, 'r') as f:
                                existing_orders = json.load(f)

                        # Convert new orders to JSON-serializable format
                        new_orders_data = []
                        for order in orders:
                            order_dict = {
                                "order_id": order.order_id,
                                "route_id": order.route_id,
                                "location": order.location,
                                "order_date": order.order_date,
                                "items": [
                                    {
                                        "product_number": item.product_number,
                                        "product_name": item.product_name,
                                        "units_ordered": item.units_ordered,
                                        "units_per_tray": item.units_per_tray,
                                        "trays_needed": item.trays_needed,
                                        "stack_height": item.stack_height,
                                        "stacks_needed": item.stacks_needed,
                                        "tray_type": item.tray_type
                                    } for item in order.items
                                ],
                                "total_trays": order.total_trays,
                                "total_stacks": order.total_stacks
                            }
                            new_orders_data.append(order_dict)

                        # Combine existing and new orders
                        all_orders = existing_orders + new_orders_data

                        # Save all orders to single file
                        with open(filename, 'w') as f:
                            json.dump(all_orders, f, indent=2)

                        st.success(f"💾 {len(new_orders_data)} new orders added to {filename} (Total: {len(all_orders)} orders)")

                    except Exception as e:
                        st.error(f"Error saving orders to file: {str(e)}")

                    # Show summary
                    location_summary = {}
                    for order in orders:
                        if order.location not in location_summary:
                            location_summary[order.location] = {'orders': 0, 'trays': 0, 'stacks': 0}
                        location_summary[order.location]['orders'] += 1
                        location_summary[order.location]['trays'] += order.total_trays
                        location_summary[order.location]['stacks'] += order.total_stacks

                except ValueError:
                    st.error("Invalid date format. Please use MM/DD/YYYY format.")
                except Exception as e:
                    st.error(f"Error creating orders: {str(e)}")
            else:
                st.error("Please enter a date and select a day.")

elif page == "Relay Management":
    st.header("Relay Management")

    # Check for single orders.json file
    if not os.path.exists("orders.json"):
        st.warning("No orders.json file available. Please generate some random orders first.")
    else:
        st.subheader("Create Relay from Orders")

        col1, col2 = st.columns([2, 1])

        with col1:
            try:
                # Load orders from single file
                with open("orders.json", 'r') as f:
                    orders_data = json.load(f)

                if not orders_data:
                    st.warning("orders.json is empty. Please generate some random orders first.")
                else:
                    st.info(f"📄 Loaded {len(orders_data)} orders from orders.json")

            except Exception as e:
                st.error(f"Error loading orders.json: {str(e)}")
                orders_data = None

        with col2:
            st.subheader("Actions")

            if st.button("Create Relay", type="primary"):
                if orders_data:
                    try:
                        # Convert JSON orders back to Order objects for relay system
                        orders = []
                        for order_data in orders_data:
                            # Create OrderItem objects from JSON data
                            items = []
                            for item_data in order_data['items']:
                                item = OrderItem(
                                    product_number=item_data['product_number'],
                                    product_name=item_data['product_name'],
                                    units_ordered=item_data['units_ordered'],
                                    units_per_tray=item_data['units_per_tray'],
                                    trays_needed=item_data['trays_needed'],
                                    stack_height=item_data['stack_height'],
                                    stacks_needed=item_data['stacks_needed'],
                                    tray_type=item_data['tray_type']
                                )
                                items.append(item)

                            # Create Order object from JSON data
                            order = Order(
                                order_id=order_data['order_id'],
                                route_id=order_data['route_id'],
                                location=order_data['location'],
                                order_date=order_data['order_date'],
                                items=items,
                                total_trays=order_data['total_trays'],
                                total_stacks=order_data['total_stacks']
                            )
                            orders.append(order)

                        # Create relay from loaded orders
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
                        
                        if locations:
                            st.session_state.current_locations = locations
                            st.success(f"✅ Created relay with {len(locations)} locations")

                        else:
                            st.error("Failed to create relay.")
                    except Exception as e:
                        st.error(f"Error creating relay: {str(e)}")
                else:
                    st.error("No orders available. Please generate some random orders first.")

        # Display existing relay
        if st.session_state.current_locations:
            st.subheader("Current Relay")
            
            # Calculate totals
            total_trailers = 0
            total_stacks = 0
            for location in st.session_state.current_locations:
                total_trailers += len(location.trailers)
                total_stacks += location.total_stacks
            
            # Display totals
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Trailers", total_trailers)
            with col2:
                st.metric("Total Stacks", total_stacks)
            
            for location in st.session_state.current_locations:
                with st.expander(f"{location.name} - {len(location.trailers)} trailers"):
                    for trailer in location.trailers:
                        status = "🟢 Dispatched" if trailer.dispatched else "🔴 Active"

                        # Create a unique key for each trailer
                        trailer_key = f"current_{location.name}_trailer_{trailer.number}"

                        # Display trailer info with clickable button
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.write(f"**Trailer #{trailer.number}**: {trailer.stacks} stacks - {status}")
                            st.write(f"  LD: {trailer.ld_number}")
                            if trailer.trailer_number:
                                st.write(f"  Trailer #: {trailer.trailer_number}")
                            if trailer.seal_number:
                                st.write(f"  Seal #: {trailer.seal_number}")
                            if trailer.dispatched and trailer.dispatch_timestamp:
                                st.write(f"  Dispatched: {trailer.dispatch_timestamp}")

                        with col2:
                            if not trailer.dispatched:
                                if st.button("Edit", key=f"edit_{trailer_key}"):
                                    st.session_state[f"editing_{trailer_key}"] = True
                            else:
                                st.write("✅ Dispatched")

                        # Show editing form if this trailer is being edited
                        if st.session_state.get(f"editing_{trailer_key}", False):
                            with st.container():
                                st.markdown("---")
                                st.subheader(f"Edit Trailer #{trailer.number}")

                                col1, col2 = st.columns(2)

                                with col1:
                                    new_trailer_number = st.text_input(
                                        "Trailer Number",
                                        value=trailer.trailer_number,
                                        key=f"trailer_num_{trailer_key}"
                                    )

                                with col2:
                                    new_seal_number = st.text_input(
                                        "Seal Number",
                                        value=trailer.seal_number,
                                        key=f"seal_num_{trailer_key}"
                                    )

                                col1, col2, col3 = st.columns(3)

                                with col1:
                                    if st.button("Save Changes", key=f"save_{trailer_key}"):
                                        trailer.trailer_number = new_trailer_number
                                        trailer.seal_number = new_seal_number
                                        st.session_state[f"editing_{trailer_key}"] = False
                                        st.rerun()

                                with col2:
                                    if st.button("Dispatch Trailer", key=f"dispatch_{trailer_key}", type="primary"):
                                        trailer.trailer_number = new_trailer_number
                                        trailer.seal_number = new_seal_number
                                        trailer.dispatched = True
                                        trailer.dispatch_timestamp = datetime.now().isoformat()
                                        st.session_state[f"editing_{trailer_key}"] = False
                                        st.success(f"✅ Trailer #{trailer.number} dispatched!")
                                        st.rerun()

                                with col3:
                                    if st.button("Cancel", key=f"cancel_{trailer_key}"):
                                        st.session_state[f"editing_{trailer_key}"] = False
                                        st.rerun()

                                st.markdown("---")

        # Inbound Trailers Analysis
        if st.session_state.current_locations:
            st.subheader("Inbound Trailers Analysis")
            st.info("📥 Products that need to be ordered from other plants (origin_plant ≠ 191)")
            
            # Analyze orders for inbound products
            inbound_analysis = analyze_inbound_products()
            
            if inbound_analysis:
                # Display inbound products by origin plant
                for origin_plant, products in inbound_analysis.items():
                    with st.expander(f"Origin Plant {origin_plant} - {len(products)} products"):
                        total_units = sum(product['total_units'] for product in products)
                        total_trays = sum(product['total_trays'] for product in products)
                        total_stacks = sum(product['total_stacks'] for product in products)
                        
                        st.write(f"**Total**: {total_units} units, {total_trays} trays, {total_stacks} stacks")
                        st.write("**Products needed:**")
                        
                        for product in products:
                            st.write(f"  • {product['product_name']} (Product #{product['product_number']})")
                            st.write(f"    Units: {product['total_units']}, Trays: {product['total_trays']}, Stacks: {product['total_stacks']}")
            else:
                st.success("✅ All products are from our plant (191) - No inbound trailers needed!")


# Global systems (re-initialized as needed)
order_system: Optional[OrderSystem] = None
relay_system: Optional[RelaySystem] = None
current_locations = []  # Store current locations for trailer editing
selected_trailer_location = ""  # Store currently selected trailer location
selected_trailer_number = 0  # Store currently selected trailer number