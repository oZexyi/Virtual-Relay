import os
import json
import gradio as gr
import requests
from datetime import datetime

from orders import OrderSystem, Order
from relay_logic import RelaySystem


# Global systems (re-initialized as needed)
order_system: OrderSystem | None = None
relay_system: RelaySystem | None = None

# Initialize systems on startup
def initialize_systems():
	global order_system, relay_system
	try:
		order_system = OrderSystem()
		relay_system = RelaySystem()
		relay_system.order_system = order_system
		return f"System ready: {len(order_system.products)} products, {len(order_system.routes)} routes."
	except Exception as e:
		return f"Error initializing system: {str(e)}"

def ensure_order_system() -> str:
	global order_system
	try:
		if order_system is None:
			order_system = OrderSystem()
		return f"Catalog ready: {len(order_system.products)} products, {len(order_system.routes)} routes."
	except Exception as e:
		return f"Error loading catalog: {str(e)}"


def ensure_relay_system() -> None:
	global relay_system
	try:
		if relay_system is None:
			relay_system = RelaySystem()
		# Keep relay_system's order_system in sync with global order_system
		if order_system is not None:
			relay_system.order_system = order_system
	except Exception as e:
		raise Exception(f"Error initializing relay system: {str(e)}")




def create_orders_for_date_and_day(order_date: str, order_day: str, max_products: int):
	"""Create orders for a specific date and day"""
	try:
		if not order_date or not order_date.strip():
			return "Please enter a date in MM/DD/YYYY format (e.g., 12/25/2024)", []
		
		if not order_day:
			return "Please select a day from the dropdown (1, 2, 4, 5, or 6)", []
		
		# Validate date format
		try:
			from datetime import datetime
			datetime.strptime(order_date.strip(), "%m/%d/%Y")
		except ValueError:
			return "Invalid date format. Please use MM/DD/YYYY format (e.g., 12/25/2024)", []
		
		# Validate day number (from dropdown, so should be valid)
		try:
			day_num = int(order_day)
			if day_num not in [1, 2, 4, 5, 6]:
				return "Invalid day selected. Please select Day 1, 2, 4, 5, or 6.", []
		except ValueError:
			return "Invalid day selected. Please select Day 1, 2, 4, 5, or 6.", []
		
		if max_products is None or max_products <= 0:
			max_products = len(order_system.products) if order_system else 100
		
		msg = ensure_order_system()
		ensure_relay_system()
		
		# Create orders with the specified date and day
		orders = order_system.simulate_random_orders(max_products, order_date.strip(), day_num)
		
		# Save orders to JSON file with confirmed date/day information
		if orders:
			save_orders_with_confirmation(orders, order_date.strip(), day_num)
		
		dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders()))
		
		return f"{msg}\nCreated {len(orders)} orders for {order_date} Day {day_num} with up to {max_products} products per route.\n\nOrders saved to JSON file with confirmed date/day for relay generation.", dates
	
	except Exception as e:
		return f"Error creating orders: {str(e)}", []


def create_orders_for_date(order_date: str, max_products: int):
	"""Legacy function - kept for compatibility"""
	try:
		if not order_date or not order_date.strip():
			return "Please enter a date in MM/DD/YYYY format (e.g., 12/25/2024)", []
		
		# Validate date format
		try:
			from datetime import datetime
			datetime.strptime(order_date.strip(), "%m/%d/%Y")
		except ValueError:
			return "Invalid date format. Please use MM/DD/YYYY format (e.g., 12/25/2024)", []
		
		if max_products is None or max_products <= 0:
			max_products = len(order_system.products) if order_system else 100
		
		msg = ensure_order_system()
		ensure_relay_system()
		
		# Create orders with the specified date
		orders = order_system.simulate_random_orders(max_products, order_date.strip())
		dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders()))
		
		return f"{msg}\nCreated {len(orders)} orders for {order_date} with up to {max_products} products per route.", dates
	
	except Exception as e:
		return f"Error creating orders: {str(e)}", []


def simulate_orders(max_products: int):
	"""Legacy function - kept for compatibility"""
	if max_products is None or max_products <= 0:
		max_products = len(order_system.products) if order_system else 100
	msg = ensure_order_system()
	ensure_relay_system()
	orders = order_system.simulate_random_orders(max_products)
	dates = sorted(set(o.order_date.split(" ")[0] for o in orders))
	return f"{msg}\nCreated {len(orders)} demo orders with up to {max_products} products per route.", dates


def get_dates():
	ensure_order_system()
	# Extract dates from order_date strings, handling both formats:
	# "YYYY-MM-DD HH:MM:SS" and "YYYY-MM-DD Day X HH:MM:SS"
	dates = set()
	for order in order_system.get_all_orders():
		date_part = order.order_date.split(" ")[0]  # Get YYYY-MM-DD part
		dates.add(date_part)
	return sorted(dates)


def get_initial_dates():
	"""Get dates on startup, return empty list if no orders exist yet"""
	try:
		ensure_order_system()
		# Extract dates from order_date strings, handling both formats:
		# "YYYY-MM-DD HH:MM:SS" and "YYYY-MM-DD Day X HH:MM:SS"
		dates = set()
		for order in order_system.get_all_orders():
			date_part = order.order_date.split(" ")[0]  # Get YYYY-MM-DD part
			dates.add(date_part)
		return sorted(dates)
	except:
		return []


def get_available_dates_and_days():
	"""Get available dates and days for dropdowns"""
	try:
		ensure_order_system()
		dates = set()
		date_day_combinations = set()
		
		for order in order_system.get_all_orders():
			date_part = order.order_date.split(" ")[0]  # Get YYYY-MM-DD part
			dates.add(date_part)
			
			# Extract day number if present
			if "Day" in order.order_date:
				day_part = order.order_date.split("Day ")[1].split(" ")[0]
				date_day_combinations.add((date_part, day_part))
			else:
				date_day_combinations.add((date_part, "1"))  # Default to day 1
		
		return sorted(dates), sorted(date_day_combinations)
	except Exception as e:
		return [], []


def get_available_days_for_date(selected_date: str):
	"""Get available days for a specific date"""
	try:
		if not selected_date:
			return []
		
		ensure_order_system()
		days = set()
		
		for order in order_system.get_all_orders():
			if order.order_date.startswith(selected_date):
				# Extract day number if present
				if "Day" in order.order_date:
					day_part = order.order_date.split("Day ")[1].split(" ")[0]
					days.add(day_part)
				else:
					days.add("1")  # Default to day 1
		
		return sorted(days, key=lambda x: int(x) if x.isdigit() else 0)
	except Exception as e:
		return []


def get_available_orders_for_relay():
	"""Get available orders from comprehensive JSON files for relay selection"""
	try:
		# Look for comprehensive order JSON files in the current directory
		import os
		import glob
		
		# First try to find confirmed order files
		confirmed_files = glob.glob("confirmed_orders_*.json")
		order_files = glob.glob("orders_*.json")
		
		formatted_orders = []
		order_data = {}
		
		# Process confirmed order files first (preferred)
		for file_path in confirmed_files:
			try:
				with open(file_path, 'r') as f:
					file_data = json.load(f)
				
				# Extract confirmation and orders data
				confirmation = file_data.get('confirmation', {})
				orders = file_data.get('orders', [])
				metadata = file_data.get('metadata', {})
				
				for order in orders:
					order_id = order.get('order_id', 'Unknown')
					order_date = order.get('order_date', '')
					location = order.get('location', 'Unknown')
					
					# Use confirmed date/day from metadata
					confirmed_date = metadata.get('confirmed_date', '')
					confirmed_day = metadata.get('confirmed_day', '1')
					
					# Format for display with confirmation info
					order_display = f"{order_id} - {confirmed_date} Day {confirmed_day} - {location} [CONFIRMED]"
					formatted_orders.append(order_display)
					order_data[order_display] = {
						'order': order,
						'confirmation': confirmation,
						'metadata': metadata
					}
					
			except Exception as e:
				print(f"Error reading confirmed order file {file_path}: {e}")
				continue
		
		# Process regular order files if no confirmed files found
		if not confirmed_files:
			for file_path in order_files:
				try:
					with open(file_path, 'r') as f:
						file_orders = json.load(f)
						
					# Handle both single order and list of orders
					if isinstance(file_orders, dict):
						file_orders = [file_orders]
					
					for order in file_orders:
						order_id = order.get('order_id', 'Unknown')
						order_date = order.get('order_date', '')
						location = order.get('location', 'Unknown')
						
						# Extract date and day from order_date
						date_part = order_date.split(" ")[0] if order_date else "Unknown"
						if "Day" in order_date:
							day_part = order_date.split("Day ")[1].split(" ")[0]
						else:
							day_part = "1"
						
						# Format for display
						order_display = f"{order_id} - {date_part} Day {day_part} - {location}"
						formatted_orders.append(order_display)
						order_data[order_display] = {'order': order}
						
				except Exception as e:
					print(f"Error reading order file {file_path}: {e}")
					continue
		
		return sorted(formatted_orders), order_data
	except Exception as e:
		print(f"Error getting orders for relay: {e}")
		return [], {}


def get_order_summary_for_date_and_day(selected_date: str, selected_day: str):
	"""Get detailed summary of orders for a specific date and day"""
	try:
		if not selected_date or not selected_day:
			return "Select both date and day to view orders"

		ensure_order_system()
		# Filter orders by date and day
		orders_for_date_day = []
		for order in order_system.get_all_orders():
			if order.order_date.startswith(selected_date):
				# Check if the order matches the selected day
				if f"Day {selected_day}" in order.order_date:
					orders_for_date_day.append(order)
				elif selected_day == "1" and "Day" not in order.order_date:
					# Legacy orders without day info default to day 1
					orders_for_date_day.append(order)
		
		if not orders_for_date_day:
			return f"No orders found for {selected_date} Day {selected_day}"
		
		# Group orders by location
		locations = {}
		for order in orders_for_date_day:
			location = order.location
			if location not in locations:
				locations[location] = []
			locations[location].append(order)
		
		summary_lines = [
			f"=== ORDERS FOR {selected_date} DAY {selected_day} ===",
			f"Total Orders: {len(orders_for_date_day)}",
			f"Total Locations: {len(locations)}",
			""
		]
		
		for location, orders in sorted(locations.items()):
			total_trays = sum(order.total_trays for order in orders)
			total_stacks = sum(order.total_stacks for order in orders)
			summary_lines.append(f"📍 {location}")
			summary_lines.append(f"   Orders: {len(orders)}")
			summary_lines.append(f"   Total Trays: {total_trays}")
			summary_lines.append(f"   Total Stacks: {total_stacks}")
			summary_lines.append("")
		
		return "\n".join(summary_lines)
	except Exception as e:
		return f"Error getting order summary: {str(e)}"


def get_order_summary(selected_date: str):
	"""Get detailed summary of orders for a specific date (legacy function)"""
	try:
		if not selected_date:
			return "Select a date to view orders"

		ensure_order_system()
		# Filter orders by date, handling both formats:
		# "YYYY-MM-DD HH:MM:SS" and "YYYY-MM-DD Day X HH:MM:SS"
		orders_for_date = [o for o in order_system.get_all_orders() if o.order_date.startswith(selected_date)]
		
		if not orders_for_date:
			return f"No orders found for {selected_date}"
		
		# Group orders by location
		locations = {}
		for order in orders_for_date:
			location = order.location
			if location not in locations:
				locations[location] = []
			locations[location].append(order)
		
		summary_lines = [
			f"=== ORDERS FOR {selected_date} ===",
			f"Total Orders: {len(orders_for_date)}",
			f"Total Locations: {len(locations)}",
			""
		]
		
		for location, orders in sorted(locations.items()):
			total_trays = sum(order.total_trays for order in orders)
			total_stacks = sum(order.total_stacks for order in orders)
			summary_lines.append(f"📍 {location}")
			summary_lines.append(f"   Orders: {len(orders)}")
			summary_lines.append(f"   Total Trays: {total_trays}")
			summary_lines.append(f"   Total Stacks: {total_stacks}")
			summary_lines.append("")
		
		return "\n".join(summary_lines)
	except Exception as e:
		return f"Error getting order summary: {str(e)}"


def create_relay(selected_date: str, day_number: str | None):
	try:
		if not selected_date:
			return "Please select a date first.", ""
		
		ensure_order_system()
		ensure_relay_system()

		day_num_int = None
		if day_number:
			try:
				day_num_int = int(day_number)
			except ValueError:
				day_num_int = None

		locations = relay_system.create_automated_relay(selected_date, day_num_int)
		if not locations:
			return f"No orders found for {selected_date} Day {day_number if day_number else '1'}.", ""

		# Build summary
		summary_lines = [
			"== AUTOMATED RELAY SUMMARY ==",
			f"Date: {selected_date}  Day: {day_num_int if day_num_int else '-'}",
		]

		for loc in relay_system.locations:
			total_trays = getattr(loc, 'total_trays', sum(item.trays_needed for o in loc.orders for item in o.items))
			summary_lines.append(f"\n{loc.name}: Orders={len(loc.orders)}  Trays={total_trays}  Stacks={loc.total_stacks}  Trailers={len(loc.trailers)}")

		# Build detailed trailer and order info
		details_lines = ["== TRAILER ASSIGNMENTS =="]
		for loc in relay_system.locations:
			details_lines.append(f"\n📍 {loc.name}")
			details_lines.append(f"   Total Stacks: {loc.total_stacks} | Total Trailers: {len(loc.trailers)}")
			
			# Show each trailer
			for trailer in loc.trailers:
				details_lines.append(f"   🚛 Trailer #{trailer.number}: {trailer.stacks} stacks")
			
			details_lines.append(f"\n   📋 Orders for {loc.name}:")
			for o in loc.orders:
				details_lines.append(f"      Order {o.order_id} (Route {o.route_id}): {o.total_trays} trays, {o.total_stacks} stacks")
				for it in o.items:
					details_lines.append(f"        - {it.product_name}: {it.units_ordered} units → {it.trays_needed} trays → {it.stacks_needed} stacks")

		return "\n".join(summary_lines), "\n".join(details_lines)
	
	except Exception as e:
		return f"Error creating relay: {str(e)}", ""


def update_order_day_choices(selected_date):
	"""Update order day dropdown when date changes"""
	if selected_date:
		days = get_available_days_for_date(selected_date)
		return gr.Dropdown(choices=days, value=days[0] if days else None)
	else:
		return gr.Dropdown(choices=[], value=None)


def update_relay_day_choices(selected_date):
	"""Update relay day dropdown when date changes"""
	if selected_date:
		days = get_available_days_for_date(selected_date)
		return gr.Dropdown(choices=days, value=days[0] if days else None)
	else:
		return gr.Dropdown(choices=[], value=None)


def get_order_summary_for_date_day(selected_date, selected_day):
	"""Get order summary for specific date and day"""
	if not selected_date or not selected_day:
		return "Select both date and day to view orders"
	return get_order_summary_for_date_and_day(selected_date, selected_day)


# ============================================================================
# 🌍 WORLD TIME API INTEGRATION
# ============================================================================

def get_north_carolina_datetime():
	"""
	Get current date and time from WorldTimeAPI for North Carolina (Eastern Time)
	
	🎓 API Learning: This function demonstrates:
	- Making HTTP GET requests with the 'requests' library
	- Handling API responses and JSON parsing
	- Error handling for network issues
	- Converting API data to usable formats
	- Using real-time data for business applications
	
	Returns:
		dict: {"success": bool, "datetime": str, "timezone": str, "error": str}
	"""
	try:
		# 🎓 API Request: North Carolina uses Eastern Time (America/New_York)
		# This is the same timezone as New York, which covers the entire Eastern US
		api_url = "http://worldtimeapi.org/api/timezone/America/New_York"
		print("🌍 API Call: Fetching North Carolina (Eastern Time) from WorldTimeAPI")
		
		# Make the API request with a timeout to prevent hanging
		response = requests.get(api_url, timeout=10)
		
		# 🎓 HTTP Status Codes: 200 = success, 404 = not found, 500 = server error
		if response.status_code == 200:
			# 🎓 JSON Parsing: Convert the API response to Python dictionary
			api_data = response.json()
			
			# Extract the datetime from the API response
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
			# 🎓 Error Handling: Handle different HTTP error codes
			error_msg = f"API returned status code {response.status_code}"
			print(f"API Error: {error_msg}")
			return {
				"success": False,
				"datetime": None,
				"timezone": "North Carolina (Eastern Time)",
				"error": error_msg
			}
			
	except requests.exceptions.Timeout:
		# 🎓 Network Error Handling: Handle timeout errors
		error_msg = "API request timed out (network too slow)"
		print(f"Network Error: {error_msg}")
		return {
			"success": False,
			"datetime": None,
			"timezone": "North Carolina (Eastern Time)",
			"error": error_msg
		}
	except requests.exceptions.RequestException as e:
		# 🎓 General Error Handling: Handle other network issues
		error_msg = f"Network error: {str(e)}"
		print(f"Network Error: {error_msg}")
		return {
			"success": False,
			"datetime": None,
			"timezone": "North Carolina (Eastern Time)",
			"error": error_msg
		}
	except json.JSONDecodeError:
		# 🎓 Data Error Handling: Handle invalid JSON responses
		error_msg = "API returned invalid JSON data"
		print(f"Data Error: {error_msg}")
		return {
			"success": False,
			"datetime": None,
			"timezone": "North Carolina (Eastern Time)",
			"error": error_msg
		}
	except Exception as e:
		# 🎓 General Error Handling: Catch any other unexpected errors
		error_msg = f"Unexpected error: {str(e)}"
		print(f"Unexpected Error: {error_msg}")
		return {
			"success": False,
			"datetime": None,
			"timezone": "North Carolina (Eastern Time)",
			"error": error_msg
		}


def get_north_carolina_date_for_orders():
	"""
	Get current North Carolina date in MM/DD/YYYY format for order creation
	
	🎓 API Learning: This function demonstrates:
	- Integrating API data into business workflows
	- Providing fallback mechanisms for reliability
	- Converting API data to application-specific formats
	
	Returns:
		str: Current date in MM/DD/YYYY format (e.g., "12/25/2024")
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
			# 🎓 Fallback: Use local system time if API fails
			fallback_date = datetime.now().strftime("%m/%d/%Y")
			print(f"API failed, using local time: {fallback_date}")
			return fallback_date
			
	except Exception as e:
		# 🎓 Error Handling: Always provide a fallback
		fallback_date = datetime.now().strftime("%m/%d/%Y")
		print(f"Error getting API date, using local time: {fallback_date}")
		return fallback_date


def save_orders_to_json(orders, date_str, day_num):
	"""
	Save orders to JSON file for persistence and relay generation
	
	🎓 Data Persistence: This function demonstrates:
	- File I/O operations for data persistence
	- JSON serialization for data storage
	- Separation of concerns between order creation and relay generation
	
	Args:
		orders: List of Order objects
		date_str: Date string (MM/DD/YYYY)
		day_num: Day number
	"""
	try:
		# Convert date to filename format (MM-DD-YYYY)
		filename_date = date_str.replace("/", "-")
		filename = f"orders_{filename_date}_Day{day_num}.json"
		
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
		
		# Save to JSON file
		with open(filename, 'w') as f:
			json.dump(orders_data, f, indent=2)
		
		print(f"Saved {len(orders)} orders to {filename}")
		
	except Exception as e:
		print(f"Error saving orders to JSON: {e}")


def save_orders_with_confirmation(orders, date_str, day_num):
	"""
	Save orders to JSON file with confirmed date/day information for relay generation
	
	This function creates a comprehensive JSON file that includes:
	- All order data
	- Confirmed date and day information
	- Metadata for relay generation
	
	Args:
		orders: List of Order objects
		date_str: Date string (MM/DD/YYYY)
		day_num: Day number
	"""
	try:
		# Convert date to filename format (MM-DD-YYYY)
		filename_date = date_str.replace("/", "-")
		filename = f"confirmed_orders_{filename_date}_Day{day_num}.json"
		
		# Load current confirmation state
		confirmation_data = load_confirmation_state()
		
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
		
		# Create comprehensive data structure
		comprehensive_data = {
			"confirmation": confirmation_data,
			"orders": orders_data,
			"metadata": {
				"total_orders": len(orders),
				"confirmed_date": date_str,
				"confirmed_day": day_num,
				"generation_timestamp": datetime.now().isoformat(),
				"ready_for_relay": True
			}
		}
		
		# Save to JSON file
		with open(filename, 'w') as f:
			json.dump(comprehensive_data, f, indent=2)
		
		print(f"Saved {len(orders)} orders with confirmation data to {filename}")
		
	except Exception as e:
		print(f"Error saving orders with confirmation: {e}")


def load_confirmation_state():
	"""Load the current confirmation state from selection_state.json"""
	try:
		with open("selection_state.json", "r") as f:
			state_data = json.load(f)
		return state_data
	except FileNotFoundError:
		return {"confirmed": False, "status": "not_confirmed"}
	except Exception as e:
		print(f"Error loading confirmation state: {e}")
		return {"confirmed": False, "status": "error"}


def get_north_carolina_datetime_for_audit():
	"""
	Get current North Carolina date and time for audit trail purposes
	
	🎓 API Learning: This function demonstrates:
	- Using API data for business audit requirements
	- Providing detailed timestamp information
	- Maintaining data integrity for compliance
	
	Returns:
		dict: {"date": str, "datetime": str, "timezone": str, "api_success": bool}
	"""
	try:
		# Get current time from North Carolina via API
		api_result = get_north_carolina_datetime()
		
		if api_result["success"]:
			# Convert API datetime to MM/DD/YYYY format for orders
			formatted_date = format_api_datetime_for_orders(api_result["datetime"])
			
			# Extract time for audit purposes
			api_datetime = api_result["datetime"]
			time_part = api_datetime.split('T')[1].split('.')[0] if 'T' in api_datetime else "Unknown"
			
			print(f"✅ Using API datetime for audit: {formatted_date} at {time_part} NC Time")
			
			return {
				"date": formatted_date,
				"datetime": api_datetime,
				"time": time_part,
				"timezone": "North Carolina (Eastern Time)",
				"api_success": True
			}
		else:
			# 🎓 Fallback: Use local system time if API fails
			fallback_datetime = datetime.now()
			fallback_date = fallback_datetime.strftime("%m/%d/%Y")
			fallback_time = fallback_datetime.strftime("%H:%M:%S")
			
			print(f"⚠️ API failed, using local time for audit: {fallback_date} at {fallback_time}")
			
			return {
				"date": fallback_date,
				"datetime": fallback_datetime.isoformat(),
				"time": fallback_time,
				"timezone": "Local System Time",
				"api_success": False
			}
			
	except Exception as e:
		# 🎓 Error Handling: Always provide a fallback
		fallback_datetime = datetime.now()
		fallback_date = fallback_datetime.strftime("%m/%d/%Y")
		fallback_time = fallback_datetime.strftime("%H:%M:%S")
		
		print(f"❌ Error getting API datetime, using local time: {fallback_date} at {fallback_time}")
		
		return {
			"date": fallback_date,
			"datetime": fallback_datetime.isoformat(),
			"time": fallback_time,
			"timezone": "Local System Time (Error)",
			"api_success": False
		}


def format_api_datetime_for_orders(api_datetime_str):
	"""
	Convert API datetime to MM/DD/YYYY format for order creation
	
	🎓 Data Processing: This function demonstrates:
	- Parsing ISO datetime strings from APIs
	- Converting between different date formats
	- Handling timezone information
	
	Args:
		api_datetime_str (str): ISO datetime string from API (e.g., "2024-12-25T14:30:00-05:00")
	
	Returns:
		str: Date in MM/DD/YYYY format (e.g., "12/25/2024")
	"""
	try:
		# 🎓 Date Parsing: APIs often return ISO format dates
		# ISO format: "2024-12-25T14:30:00-05:00" (date, time, timezone)
		
		# Remove timezone info and parse the datetime
		datetime_part = api_datetime_str.split('+')[0].split('-')[0:3]
		if len(datetime_part) >= 3:
			# Reconstruct without timezone
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
		# 🎓 Fallback: Return current date if conversion fails
		return datetime.now().strftime("%m/%d/%Y")


with gr.Blocks(title="Virtual Relay System") as demo:
	gr.Markdown("# Virtual Relay System — Shipping Dashboard (HF Spaces)")
	
	# Initialize systems on startup
	initial_status = initialize_systems()
	initial_dates = get_initial_dates()
	
	with gr.Tab("Catalog"):
		gr.Markdown("System is ready with built-in products and routes catalog.")
		catalog_msg = gr.Textbox(label="Status", value=initial_status, interactive=False)
		date_dropdown_1 = gr.Dropdown(choices=initial_dates, label="Available Dates", interactive=False)
		
		# Refresh button to reload the catalog
		refresh_btn = gr.Button("Refresh Catalog")
		refresh_btn.click(lambda: (initialize_systems(), get_initial_dates()), outputs=[catalog_msg, date_dropdown_1])

	with gr.Tab("Orders"):
		gr.Markdown("## Order Management System")
		gr.Markdown("This page demonstrates the order management capabilities of the Virtual Relay System.")
		
		with gr.Row():
			with gr.Column(scale=1):
				gr.Markdown("### Create Orders")
				gr.Markdown("**Step 1:** Get today's date and select day")
				gr.Markdown("**API Integration:** Get current North Carolina date automatically")
				with gr.Row():
					order_date_input = gr.Textbox(label="Order Date", placeholder="MM/DD/YYYY (e.g., 12/25/2024)", interactive=True, value="")
					get_today_btn = gr.Button("Get Today's Date", variant="secondary", size="sm")
				order_day_dropdown = gr.Dropdown(
					choices=["1", "2", "4", "5", "6"],
					label="Select Day",
					interactive=True,
					value="1"
				)
				with gr.Row():
					confirm_date_day_btn = gr.Button("Confirm Date & Day Selection", variant="primary")
					clear_selection_btn = gr.Button("Clear Selection", variant="secondary")
				date_day_status = gr.Textbox(label="Selection Status", value="Please select date and day, then confirm", interactive=False)
				
				gr.Markdown("**Step 2:** Configure order parameters")
				max_products = gr.Slider(1, 235, value=235, step=1, label="Max products per order")
				simulate_btn = gr.Button("Generate Orders for Confirmed Date & Day", variant="primary")
				sim_msg = gr.Textbox(label="Order Creation Status", interactive=False)
			
			with gr.Column(scale=1):
				gr.Markdown("### View Existing Orders")
				gr.Markdown("View orders that have already been created:")
				refresh_orders_btn = gr.Button("Refresh Order List")
				order_date_dropdown = gr.Dropdown(choices=initial_dates, label="Select Date with Orders", interactive=True)
				order_day_dropdown = gr.Dropdown(choices=[], label="Select Day with Orders", interactive=True)
				order_summary = gr.Textbox(label="Order Summary", lines=8, interactive=False, value="Select a date and day to view existing orders")
		
		
		# 🎓 API Integration: Connect the "Get Today's Date" button to our API function
		def get_todays_date():
			"""Get current North Carolina date and populate the order date field"""
			nc_date = get_north_carolina_date_for_orders()
			return nc_date
		
		def save_selection_state(order_date, order_day):
			"""Save date and day selection to a persistent state file"""
			try:
				state_data = {
					"selected_date": order_date.strip() if order_date else "",
					"selected_day": order_day,
					"timestamp": datetime.now().isoformat(),
					"confirmed": True,
					"status": "confirmed"
				}
				
				with open("selection_state.json", "w") as f:
					json.dump(state_data, f, indent=2)
				
				print(f"Saved selection state: {order_date} Day {order_day}")
				return True
			except Exception as e:
				print(f"Error saving selection state: {e}")
				return False
		
		def load_selection_state():
			"""Load date and day selection from persistent state file"""
			try:
				with open("selection_state.json", "r") as f:
					state_data = json.load(f)
				
				date = state_data.get("selected_date", "")
				day = state_data.get("selected_day", "1")
				confirmed = state_data.get("confirmed", False)
				
				print(f"Loaded selection state: {date} Day {day} (confirmed: {confirmed})")
				return date, day, confirmed
			except FileNotFoundError:
				print("No selection state file found")
				return "", "1", False
			except Exception as e:
				print(f"Error loading selection state: {e}")
				return "", "1", False
		
		def confirm_date_and_day(order_date, order_day):
			"""Confirm and lock in the selected date and day with persistent storage"""
			
			if not order_date or not order_date.strip():
				return "Please enter a date first", "Please select date and day, then confirm"
			
			if not order_day:
				return "Please select a day first", "Please select date and day, then confirm"
			
			# Validate date format
			try:
				datetime.strptime(order_date.strip(), "%m/%d/%Y")
			except ValueError:
				return "Invalid date format. Use MM/DD/YYYY", "Please select date and day, then confirm"
			
			# Validate day
			try:
				day_num = int(order_day)
				if day_num not in [1, 2, 4, 5, 6]:
					return "Invalid day. Select 1, 2, 4, 5, or 6", "Please select date and day, then confirm"
			except ValueError:
				return "Invalid day selection", "Please select date and day, then confirm"
			
			# Save to persistent state file
			if save_selection_state(order_date, order_day):
				status_msg = f"CONFIRMED: {order_date.strip()} Day {order_day}\nSaved to persistent state\nReady to generate orders!"
				return f"Date and day confirmed: {order_date.strip()} Day {order_day}", status_msg
			else:
				return "Error saving selection state", "Please try again"
		
		def create_orders_with_confirmed_data(max_products):
			"""Create orders using the confirmed date and day from persistent state"""
			
			# Load confirmed data from file
			confirmed_date, confirmed_day, is_confirmed = load_selection_state()
			
			if not is_confirmed or not confirmed_date:
				return "Please confirm date and day selection first", []
			
			return create_orders_for_date_and_day(confirmed_date, confirmed_day, max_products)
		
		def clear_selection_state():
			"""Clear the persistent selection state"""
			try:
				import os
				if os.path.exists("selection_state.json"):
					os.remove("selection_state.json")
					print("Cleared selection state")
				
				return "", "1", "Selection cleared. Please select date and day, then confirm"
			except Exception as e:
				print(f"Error clearing selection state: {e}")
				return "", "1", "Error clearing selection"
		
		def initialize_order_ui():
			"""Initialize the order UI with any existing confirmed state"""
			try:
				confirmed_date, confirmed_day, is_confirmed = load_selection_state()
				
				if is_confirmed and confirmed_date:
					status_msg = f"CONFIRMED: {confirmed_date} Day {confirmed_day}\nLoaded from persistent state\nReady to generate orders!"
					return confirmed_date, confirmed_day, status_msg
				else:
					return "", "1", "Please select date and day, then confirm"
			except Exception as e:
				return "", "1", "Please select date and day, then confirm"
		
		# Initialize UI with existing state
		initial_date, initial_day, initial_status = initialize_order_ui()
		
		# Update UI components with initial values if they exist
		if initial_date:
			order_date_input.value = initial_date
		if initial_day:
			order_day_dropdown.value = initial_day
		if initial_status:
			date_day_status.value = initial_status
		
		confirm_date_day_btn.click(confirm_date_and_day, inputs=[order_date_input, order_day_dropdown], outputs=[sim_msg, date_day_status])
		clear_selection_btn.click(clear_selection_state, inputs=None, outputs=[order_date_input, order_day_dropdown, date_day_status])
		simulate_btn.click(create_orders_with_confirmed_data, inputs=[max_products], outputs=[sim_msg, order_date_dropdown])
		refresh_orders_btn.click(get_dates, inputs=None, outputs=[order_date_dropdown])
		order_date_dropdown.change(update_order_day_choices, inputs=[order_date_dropdown], outputs=[order_day_dropdown])
		order_day_dropdown.change(get_order_summary_for_date_day, inputs=[order_date_dropdown, order_day_dropdown], outputs=[order_summary])
		get_today_btn.click(get_todays_date, inputs=None, outputs=[order_date_input])

	with gr.Tab("Relay"):
		gr.Markdown("## Relay Generation")
		gr.Markdown("Create relays from orders stored in JSON files. Click on order IDs to load order data and generate relays.")
		gr.Markdown("**API Integration:** All dates are synchronized with North Carolina timezone via WorldTimeAPI")
		gr.Markdown("**Data Persistence:** Orders are stored in JSON files for reliable relay generation")
		
		# Get initial orders
		initial_orders, _ = get_available_orders_for_relay()
		
		refresh_orders_btn = gr.Button("Refresh Available Orders")
		order_select = gr.Dropdown(choices=initial_orders, label="Select Orders for Relay", interactive=True, multiselect=True)
		create_btn = gr.Button("Create Relay from Selected Orders", variant="primary")
		summary_out = gr.Textbox(label="Relay Summary", lines=12, value="Create orders first, then select orders to generate relay")
		details_out = gr.Textbox(label="Trailer & Order Details", lines=16)

		def refresh_relay_orders():
			"""Refresh the relay order dropdown with current order data"""
			orders, _ = get_available_orders_for_relay()
			return gr.Dropdown(choices=orders)

		def create_relay_from_orders(selected_orders):
			"""Create relay from selected orders loaded from comprehensive JSON files"""
			if not selected_orders:
				return "Please select at least one order first.", ""
			
			try:
				ensure_order_system()
				ensure_relay_system()
				
				# Get the actual order data from JSON files
				_, order_data = get_available_orders_for_relay()
				selected_order_data = []
				confirmation_info = None
				
				for selected_order_display in selected_orders:
					if selected_order_display in order_data:
						order_info = order_data[selected_order_display]
						selected_order_data.append(order_info)
						
						# Extract confirmation info from the first order
						if confirmation_info is None and 'confirmation' in order_info:
							confirmation_info = order_info['confirmation']
				
				if not selected_order_data:
					return "No valid orders found for selection.", ""
				
				# Create relay from the selected orders
				# Use confirmed date/day if available, otherwise extract from order
				first_order_info = selected_order_data[0]
				first_order = first_order_info['order']
				
				if 'metadata' in first_order_info:
					# Use confirmed date/day from metadata
					date_part = first_order_info['metadata']['confirmed_date']
					day_part = first_order_info['metadata']['confirmed_day']
				else:
					# Fallback to extracting from order_date
					date_part = first_order['order_date'].split(" ")[0]
					day_part = first_order['order_date'].split("Day ")[1].split(" ")[0] if "Day" in first_order['order_date'] else "1"
				
				# Create relay using the existing system
				summary, details = create_relay(date_part, day_part)
				
				# Add information about selected orders
				order_info = f"\n\nSelected Orders ({len(selected_order_data)}):\n"
				for order_info in selected_order_data:
					order = order_info['order']
					order_info += f"- {order['order_id']}: {order['location']} ({order['total_trays']} trays, {order['total_stacks']} stacks)\n"
				
				# Add confirmation information
				if confirmation_info and confirmation_info.get('confirmed'):
					confirmation_msg = f"\nConfirmation Data: {confirmation_info['selected_date']} Day {confirmation_info['selected_day']} (Confirmed at {confirmation_info['timestamp']})"
				else:
					confirmation_msg = "\nNote: Using legacy order data (no confirmation available)"
				
				# Add JSON file information
				json_info = f"\nOrders loaded from comprehensive JSON files with confirmation data for relay generation"
				
				return summary + order_info + confirmation_msg + json_info, details
				
			except Exception as e:
				return f"Error creating relay from orders: {str(e)}", ""

		refresh_orders_btn.click(refresh_relay_orders, inputs=None, outputs=[order_select])
		create_btn.click(create_relay_from_orders, inputs=[order_select], outputs=[summary_out, details_out])



if __name__ == "__main__":
	demo.launch()


