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
		
		if not order_day or not order_day.strip():
			return "Please enter a day number (e.g., 1, 2, 3)", []
		
		# Validate date format
		try:
			from datetime import datetime
			datetime.strptime(order_date.strip(), "%m/%d/%Y")
		except ValueError:
			return "Invalid date format. Please use MM/DD/YYYY format (e.g., 12/25/2024)", []
		
		# Validate day number
		try:
			day_num = int(order_day.strip())
			if day_num < 1:
				return "Day number must be 1 or greater", []
		except ValueError:
			return "Invalid day number. Please enter a valid number (e.g., 1, 2, 3)", []
		
		if max_products is None or max_products <= 0:
			max_products = len(order_system.products) if order_system else 100
		
		msg = ensure_order_system()
		ensure_relay_system()
		
		# Create orders with the specified date and day
		orders = order_system.simulate_random_orders(max_products, order_date.strip(), day_num)
		dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders()))
		
		return f"{msg}\nCreated {len(orders)} orders for {order_date} Day {day_num} with up to {max_products} products per route.", dates
	
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

def get_current_datetime_from_api(timezone="America/New_York"):
	"""
	Get current date and time from WorldTimeAPI
	
	🎓 API Learning: This function demonstrates:
	- Making HTTP GET requests with the 'requests' library
	- Handling API responses and JSON parsing
	- Error handling for network issues
	- Converting API data to usable formats
	
	Args:
		timezone (str): Timezone identifier (e.g., "America/New_York", "Europe/London")
	
	Returns:
		dict: {"success": bool, "datetime": str, "timezone": str, "error": str}
	"""
	try:
		# 🎓 API Request: This is how you call an API
		# requests.get() sends an HTTP GET request to the API endpoint
		api_url = f"http://worldtimeapi.org/api/timezone/{timezone}"
		print(f"🌍 API Call: Fetching time for {timezone}")
		
		# Make the API request with a timeout to prevent hanging
		response = requests.get(api_url, timeout=10)
		
		# 🎓 HTTP Status Codes: 200 = success, 404 = not found, 500 = server error
		if response.status_code == 200:
			# 🎓 JSON Parsing: Convert the API response to Python dictionary
			api_data = response.json()
			
			# Extract the datetime from the API response
			datetime_str = api_data.get("datetime", "")
			timezone_name = api_data.get("timezone", timezone)
			
			print(f"✅ API Success: Got time {datetime_str} for {timezone_name}")
			
			return {
				"success": True,
				"datetime": datetime_str,
				"timezone": timezone_name,
				"error": None
			}
		else:
			# 🎓 Error Handling: Handle different HTTP error codes
			error_msg = f"API returned status code {response.status_code}"
			print(f"❌ API Error: {error_msg}")
			return {
				"success": False,
				"datetime": None,
				"timezone": timezone,
				"error": error_msg
			}
			
	except requests.exceptions.Timeout:
		# 🎓 Network Error Handling: Handle timeout errors
		error_msg = "API request timed out (network too slow)"
		print(f"❌ Network Error: {error_msg}")
		return {
			"success": False,
			"datetime": None,
			"timezone": timezone,
			"error": error_msg
		}
	except requests.exceptions.RequestException as e:
		# 🎓 General Error Handling: Handle other network issues
		error_msg = f"Network error: {str(e)}"
		print(f"❌ Network Error: {error_msg}")
		return {
			"success": False,
			"datetime": None,
			"timezone": timezone,
			"error": error_msg
		}
	except json.JSONDecodeError:
		# 🎓 Data Error Handling: Handle invalid JSON responses
		error_msg = "API returned invalid JSON data"
		print(f"❌ Data Error: {error_msg}")
		return {
			"success": False,
			"datetime": None,
			"timezone": timezone,
			"error": error_msg
		}
	except Exception as e:
		# 🎓 General Error Handling: Catch any other unexpected errors
		error_msg = f"Unexpected error: {str(e)}"
		print(f"❌ Unexpected Error: {error_msg}")
		return {
			"success": False,
			"datetime": None,
			"timezone": timezone,
			"error": error_msg
		}


def get_available_timezones():
	"""
	Get list of available timezones from WorldTimeAPI
	
	🎓 API Learning: This function demonstrates:
	- Calling different API endpoints
	- Caching API responses to avoid repeated calls
	- Providing fallback data when API fails
	
	Returns:
		list: List of timezone identifiers
	"""
	try:
		# 🎓 API Endpoint: Different APIs have different endpoints
		# This one gets a list of all available timezones
		api_url = "http://worldtimeapi.org/api/timezone"
		print("🌍 API Call: Fetching available timezones")
		
		response = requests.get(api_url, timeout=10)
		
		if response.status_code == 200:
			timezones = response.json()
			print(f"✅ API Success: Got {len(timezones)} timezones")
			return timezones
		else:
			print(f"❌ API Error: Status code {response.status_code}")
			# 🎓 Fallback Data: Provide default timezones if API fails
			return [
				"America/New_York",
				"America/Chicago", 
				"America/Denver",
				"America/Los_Angeles",
				"Europe/London",
				"Europe/Paris",
				"Asia/Tokyo"
			]
			
	except Exception as e:
		print(f"❌ API Error: {str(e)}")
		# 🎓 Fallback Data: Always provide some default options
		return [
			"America/New_York",
			"America/Chicago", 
			"America/Denver",
			"America/Los_Angeles",
			"Europe/London",
			"Europe/Paris",
			"Asia/Tokyo"
		]


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
				gr.Markdown("**Step 1:** Select date and day for your orders")
				order_date_input = gr.Textbox(label="Order Date", placeholder="MM/DD/YYYY (e.g., 12/25/2024)", interactive=True)
				order_day_input = gr.Textbox(label="Day Number", placeholder="e.g., 1", interactive=True)
				gr.Markdown("**Step 2:** Configure order parameters")
				max_products = gr.Slider(1, 235, value=235, step=1, label="Max products per order")
				simulate_btn = gr.Button("Generate Orders for Selected Date & Day", variant="primary")
				sim_msg = gr.Textbox(label="Order Creation Status", interactive=False)
			
			with gr.Column(scale=1):
				gr.Markdown("### View Existing Orders")
				gr.Markdown("View orders that have already been created:")
				refresh_orders_btn = gr.Button("Refresh Order List")
				order_date_dropdown = gr.Dropdown(choices=initial_dates, label="Select Date with Orders", interactive=True)
				order_day_dropdown = gr.Dropdown(choices=[], label="Select Day with Orders", interactive=True)
				order_summary = gr.Textbox(label="Order Summary", lines=8, interactive=False, value="Select a date and day to view existing orders")
		
		
		simulate_btn.click(create_orders_for_date_and_day, inputs=[order_date_input, order_day_input, max_products], outputs=[sim_msg, order_date_dropdown])
		refresh_orders_btn.click(get_dates, inputs=None, outputs=[order_date_dropdown])
		order_date_dropdown.change(update_order_day_choices, inputs=[order_date_dropdown], outputs=[order_day_dropdown])
		order_day_dropdown.change(get_order_summary_for_date_day, inputs=[order_date_dropdown, order_day_dropdown], outputs=[order_summary])

	with gr.Tab("Relay"):
		gr.Markdown("## Relay Generation")
		gr.Markdown("Create relays from existing orders. Only dates and days with orders are available for selection.")
		refresh_dates_btn = gr.Button("Refresh Available Dates & Days")
		date_select = gr.Dropdown(choices=initial_dates, label="Select Date with Orders", interactive=True)
		day_select = gr.Dropdown(choices=[], label="Select Day with Orders", interactive=True)
		create_btn = gr.Button("Create Relay", variant="primary")
		summary_out = gr.Textbox(label="Relay Summary", lines=12, value="Create orders first, then select a date and day with orders to generate relay")
		details_out = gr.Textbox(label="Trailer & Order Details", lines=16)

		refresh_dates_btn.click(get_dates, inputs=None, outputs=[date_select])
		date_select.change(update_relay_day_choices, inputs=[date_select], outputs=[day_select])
		create_btn.click(create_relay, inputs=[date_select, day_select], outputs=[summary_out, details_out])

	with gr.Tab("🌍 World Time API"):
		gr.Markdown("## World Time API Integration")
		gr.Markdown("**🎓 Learning APIs:** This tab demonstrates real-world API integration with WorldTimeAPI.")
		gr.Markdown("**Features:** Get real-time dates from different timezones, automatically populate order dates.")
		
		with gr.Row():
			with gr.Column(scale=1):
				gr.Markdown("### 🌍 Get Current Time")
				timezone_dropdown = gr.Dropdown(
					choices=get_available_timezones(),
					value="America/New_York",
					label="Select Timezone",
					interactive=True
				)
				get_time_btn = gr.Button("Get Current Time", variant="primary")
				api_status = gr.Textbox(label="API Status", interactive=False, value="Click 'Get Current Time' to fetch real-time data")
				current_time_display = gr.Textbox(label="Current Time", interactive=False)
			
			with gr.Column(scale=1):
				gr.Markdown("### 📅 Use API Date for Orders")
				gr.Markdown("**Convert API time to order date format:**")
				api_date_display = gr.Textbox(label="API Date (MM/DD/YYYY)", interactive=False, placeholder="Will show converted date here")
				use_api_date_btn = gr.Button("Use This Date for Orders", variant="secondary")
				api_usage_status = gr.Textbox(label="Status", interactive=False, value="Get current time first, then use it for orders")
		
		# 🎓 API Learning: This is how you connect UI elements to API functions
		def fetch_current_time(selected_timezone):
			"""Fetch current time from API and display it"""
			# Call our API function
			api_result = get_current_datetime_from_api(selected_timezone)
			
			if api_result["success"]:
				# Convert API datetime to readable format
				api_datetime = api_result["datetime"]
				formatted_date = format_api_datetime_for_orders(api_datetime)
				
				status_msg = f"✅ API Success: Got time for {api_result['timezone']}"
				time_display = f"🌍 {api_datetime}\n📍 Timezone: {api_result['timezone']}"
				
				return status_msg, time_display, formatted_date
			else:
				# Handle API errors
				status_msg = f"❌ API Error: {api_result['error']}"
				time_display = "Failed to fetch time from API"
				formatted_date = datetime.now().strftime("%m/%d/%Y")  # Fallback to local time
				
				return status_msg, time_display, formatted_date
		
		def use_api_date_for_orders(api_date):
			"""Use the API date for creating orders"""
			if api_date:
				return f"✅ Ready to use API date: {api_date}\n\nYou can now go to the 'Orders' tab and use this date for creating orders!"
			else:
				return "❌ No API date available. Please fetch current time first."
		
		# 🎓 Event Handlers: Connect buttons to functions
		get_time_btn.click(
			fetch_current_time,
			inputs=[timezone_dropdown],
			outputs=[api_status, current_time_display, api_date_display]
		)
		
		use_api_date_btn.click(
			use_api_date_for_orders,
			inputs=[api_date_display],
			outputs=[api_usage_status]
		)


if __name__ == "__main__":
	demo.launch()


