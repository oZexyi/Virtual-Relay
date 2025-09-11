import os
import json
import gradio as gr
import requests
from datetime import datetime

from orders import OrderSystem, Order
from relay_logic import RelaySystem, Location


# Global systems (re-initialized as needed)
order_system: OrderSystem | None = None
relay_system: RelaySystem | None = None
current_locations = []  # Store current locations for trailer editing
selected_trailer_location = ""  # Store currently selected trailer location
selected_trailer_number = 0  # Store currently selected trailer number

# Initialize systems on startup
def initialize_systems():
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
	"""Clean up old order files from previous runs"""
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
			# Extract base name (e.g., "all_orders_09-10-2025_Day4" from "all_orders_09-10-2025_Day4.json")
			base_name = file.replace('.json', '')
			if base_name not in file_groups:
				file_groups[base_name] = []
			file_groups[base_name].append(file)
		
		# For each group, keep only the newest file
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
				# Only one file in group, keep it
				kept_files.append(files[0])
		
		print(f"Cleanup complete: {len(deleted_files)} duplicate files deleted, {len(kept_files)} unique files kept")
		
	except Exception as e:
		print(f"Error during cleanup: {e}")


def manual_cleanup_order_files():
	"""Manual cleanup function that can be called from the UI"""
	try:
		import glob
		import os
		
		# Find all order files
		order_files = glob.glob("all_orders_*.json") + glob.glob("confirmed_orders_*.json") + glob.glob("orders_*.json")
		
		if not order_files:
			return "No order files found to clean up"
		
		# Delete all order files
		deleted_count = 0
		for file in order_files:
			try:
				os.remove(file)
				deleted_count += 1
				print(f"Deleted: {file}")
			except Exception as e:
				print(f"Error deleting {file}: {e}")
		
		return f"Manual cleanup complete: {deleted_count} files deleted"
		
	except Exception as e:
		return f"Error during manual cleanup: {e}"

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
			max_products = 235  # Use all 235 products for comprehensive order generation
		
		msg = ensure_order_system()
		ensure_relay_system()
		
		# Create orders with the specified date and day
		orders = order_system.simulate_random_orders(max_products, order_date.strip(), day_num)
		
		# Save orders to JSON file with confirmed date/day information
		if orders:
			save_orders_with_confirmation(orders, order_date.strip(), day_num)
		
		# Get dates from in-memory system (for backward compatibility)
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
	"""Get dates from JSON files for dropdown updates"""
	try:
		import glob
		
		
		# Look for consolidated order files first
		consolidated_files = glob.glob("all_orders_*.json")
		confirmed_files = glob.glob("confirmed_orders_*.json")
		order_files = glob.glob("orders_*.json")
		
		
		dates = set()
		
		# Process consolidated order files first (most preferred)
		for file_path in consolidated_files:
			try:
				with open(file_path, 'r') as f:
					file_data = json.load(f)
				
				# Get confirmed date from metadata
				metadata = file_data.get('metadata', {})
				confirmed_date = metadata.get('confirmed_date', '')
				
				if confirmed_date:
					dates.add(confirmed_date)
					
			except Exception as e:
				print(f"Error reading consolidated order file {file_path}: {e}")
				continue
		
		# Process confirmed order files second (fallback)
		for file_path in confirmed_files:
			try:
				with open(file_path, 'r') as f:
					file_data = json.load(f)
				
				# Get confirmed date from metadata
				metadata = file_data.get('metadata', {})
				confirmed_date = metadata.get('confirmed_date', '')
				
				if confirmed_date:
					dates.add(confirmed_date)
					
			except Exception as e:
				print(f"Error reading confirmed order file {file_path}: {e}")
				continue
		
		# Process regular order files if no consolidated or confirmed files found
		if not consolidated_files and not confirmed_files:
			for file_path in order_files:
				try:
					with open(file_path, 'r') as f:
						file_orders = json.load(f)
					
					# Handle both single order and list of orders
					if isinstance(file_orders, dict):
						file_orders = [file_orders]
					
					for order in file_orders:
						order_date = order.get('order_date', '')
						if order_date:
							date_part = order_date.split(" ")[0]  # Get YYYY-MM-DD part
							try:
								# Convert YYYY-MM-DD to MM/DD/YYYY
								parsed_date = datetime.strptime(date_part, "%Y-%m-%d")
								formatted_date = parsed_date.strftime("%m/%d/%Y")
								dates.add(formatted_date)
							except ValueError:
								# If already in MM/DD/YYYY format, use as is
								dates.add(date_part)
								
				except Exception as e:
					print(f"Error reading order file {file_path}: {e}")
					continue
		
		return sorted(dates)
	except Exception as e:
		print(f"Error getting dates: {e}")
		return []


def get_initial_dates():
	"""Get dates on startup from JSON files, return empty list if no orders exist yet"""
	try:
		import glob
		
		
		# Look for consolidated order files first
		consolidated_files = glob.glob("all_orders_*.json")
		confirmed_files = glob.glob("confirmed_orders_*.json")
		order_files = glob.glob("orders_*.json")
		
		
		dates = set()
		
		# Process consolidated order files first (most preferred)
		for file_path in consolidated_files:
			try:
				with open(file_path, 'r') as f:
					file_data = json.load(f)
				
				# Get confirmed date from metadata
				metadata = file_data.get('metadata', {})
				confirmed_date = metadata.get('confirmed_date', '')
				
				if confirmed_date:
					dates.add(confirmed_date)
					
			except Exception as e:
				print(f"Error reading consolidated order file {file_path}: {e}")
				continue
		
		# Process confirmed order files second (fallback)
		for file_path in confirmed_files:
			try:
				with open(file_path, 'r') as f:
					file_data = json.load(f)
				
				# Get confirmed date from metadata
				metadata = file_data.get('metadata', {})
				confirmed_date = metadata.get('confirmed_date', '')
				
				if confirmed_date:
					dates.add(confirmed_date)
					
			except Exception as e:
				print(f"Error reading confirmed order file {file_path}: {e}")
				continue
		
		# Process regular order files if no consolidated or confirmed files found
		if not consolidated_files and not confirmed_files:
			for file_path in order_files:
				try:
					with open(file_path, 'r') as f:
						file_orders = json.load(f)
					
					# Handle both single order and list of orders
					if isinstance(file_orders, dict):
						file_orders = [file_orders]
					
					for order in file_orders:
						order_date = order.get('order_date', '')
						if order_date:
							date_part = order_date.split(" ")[0]  # Get YYYY-MM-DD part
							try:
								# Convert YYYY-MM-DD to MM/DD/YYYY
								parsed_date = datetime.strptime(date_part, "%Y-%m-%d")
								formatted_date = parsed_date.strftime("%m/%d/%Y")
								dates.add(formatted_date)
							except ValueError:
								# If already in MM/DD/YYYY format, use as is
								dates.add(date_part)
								
				except Exception as e:
					print(f"Error reading order file {file_path}: {e}")
					continue
		
		return sorted(dates)
	except Exception as e:
		print(f"Error getting initial dates: {e}")
		return []


def get_available_dates_and_days():
	"""Get available dates and days for dropdowns in MM/DD/YYYY format"""
	try:
		ensure_order_system()
		dates = set()
		date_day_combinations = set()
		
		for order in order_system.get_all_orders():
			date_part = order.order_date.split(" ")[0]  # Get YYYY-MM-DD part
			try:
				# Convert YYYY-MM-DD to MM/DD/YYYY
				parsed_date = datetime.strptime(date_part, "%Y-%m-%d")
				formatted_date = parsed_date.strftime("%m/%d/%Y")
				dates.add(formatted_date)
				
				# Extract day number if present
				if "Day" in order.order_date:
					day_part = order.order_date.split("Day ")[1].split(" ")[0]
					date_day_combinations.add((formatted_date, day_part))
				else:
					date_day_combinations.add((formatted_date, "1"))  # Default to day 1
			except ValueError:
				# If already in MM/DD/YYYY format, use as is
				dates.add(date_part)
				if "Day" in order.order_date:
					day_part = order.order_date.split("Day ")[1].split(" ")[0]
					date_day_combinations.add((date_part, day_part))
				else:
					date_day_combinations.add((date_part, "1"))
		
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
	"""Get available orders from JSON files for relay selection"""
	try:
		import os
		import glob
		
		# Look for order files
		order_files = glob.glob("orders_*.json")
		
		formatted_orders = []
		order_data = {}
		
		# Process order files
		for file_path in order_files:
			try:
				with open(file_path, 'r') as f:
					file_data = json.load(f)
				
				# Get orders and metadata
				orders = file_data.get('orders', [])
				metadata = file_data.get('metadata', {})
				
				# Get confirmed date/day from metadata
				confirmed_date = metadata.get('confirmed_date', '')
				confirmed_day = metadata.get('confirmed_day', '1')
				
				# Create a single entry for this file
				file_display = f"Orders for {confirmed_date} Day {confirmed_day}"
				formatted_orders.append(file_display)
				order_data[file_display] = {
					'orders': orders,
					'metadata': metadata,
					'file_path': file_path
				}
					
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


def load_orders_from_json_files(selected_date: str, day_number: int = None):
	"""Load orders from JSON files for a specific date and day"""
	try:
		import glob
		
		# Look for order files
		order_files = glob.glob("orders_*.json")
		
		# Process order files
		for file_path in order_files:
			try:
				with open(file_path, 'r') as f:
					file_data = json.load(f)
				
				# Get confirmed date from metadata
				metadata = file_data.get('metadata', {})
				confirmed_date = metadata.get('confirmed_date', '')
				confirmed_day = metadata.get('confirmed_day', '1')
				
				# Check if this file matches our search criteria
				if confirmed_date == selected_date:
					if day_number is None or str(day_number) == str(confirmed_day):
						orders = file_data.get('orders', [])
						return orders
						
			except Exception as e:
				print(f"Error reading order file {file_path}: {e}")
				continue
		
		return []
		
	except Exception as e:
		print(f"Error loading orders from JSON files: {e}")
		return []


def create_relay_from_orders_data(orders_data):
	"""Create relay locations from orders data loaded from JSON files"""
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

		# Load orders from JSON files instead of in-memory system
		orders = load_orders_from_json_files(selected_date, day_num_int)
		
		if not orders:
			return f"No orders found for {selected_date} Day {day_number if day_number else '1'}.", ""
		
		
		# Create relay from loaded orders
		locations = create_relay_from_orders_data(orders)
		if not locations:
			return f"Failed to create relay from orders for {selected_date} Day {day_number if day_number else '1'}.", ""
		
		# Store current locations globally for trailer editing
		global current_locations
		current_locations = locations


		# Build simplified summary
		summary_lines = [
			"== RELAY ASSIGNMENTS ==",
			f"Date: {selected_date}  Day: {day_num_int if day_num_int else '-'}",
			f"Total Locations: {len(locations)}",
		]

		# Build simplified trailer assignments with color coding
		details_lines = ["== TRAILER ASSIGNMENTS =="]
		for loc in locations:
			details_lines.append(f"\n{loc.name}: (Total: {loc.total_stacks} stacks, {len(loc.trailers)} trailers)")
			
			# Show each trailer with LD number and stack count
			for trailer in loc.trailers:
				# Color coding: Red for un-dispatched, Green for dispatched
				if trailer.dispatched:
					color = "🟢"  # Green for dispatched
					status = "🚛 DISPATCHED"
					details_lines.append(f"  {color} Trailer #{trailer.number} - LD: {trailer.ld_number} ({trailer.stacks} stacks) - {status}")
				else:
					color = "🔴"  # Red for un-dispatched
					details_lines.append(f"  {color} Trailer #{trailer.number} - LD: {trailer.ld_number} ({trailer.stacks} stacks)")
				
				# Only show seal/trailer numbers if they are set
				if trailer.seal_number or trailer.trailer_number:
					seal_display = trailer.seal_number if trailer.seal_number else "Not set"
					trailer_display = trailer.trailer_number if trailer.trailer_number else "Not set"
					details_lines.append(f"    Seal #: {seal_display} | Trailer #: {trailer_display}")
				
				if trailer.dispatched and trailer.dispatch_timestamp:
					details_lines.append(f"    ✅ Dispatched: {trailer.dispatch_timestamp}")

		# Create clickable trailer buttons
		trailer_buttons = []
		for loc in locations:
			for trailer in loc.trailers:
				# Create button text with status
				if trailer.dispatched:
					button_text = f"🟢 {loc.name} - Trailer #{trailer.number} (DISPATCHED)"
					button_variant = "secondary"
				else:
					button_text = f"🔴 {loc.name} - Trailer #{trailer.number}"
					button_variant = "primary"
				
				trailer_buttons.append({
					'text': button_text,
					'variant': button_variant,
					'location': loc.name,
					'trailer_num': trailer.number,
					'seal': trailer.seal_number,
					'trailer': trailer.trailer_number,
					'dispatched': trailer.dispatched,
					'ld': trailer.ld_number,
					'stacks': trailer.stacks
				})

		return "\n".join(summary_lines), "\n".join(details_lines), trailer_buttons
	
	except Exception as e:
		return f"Error creating relay: {str(e)}", ""


def get_trailer_list():
	"""Get list of all trailers for editing"""
	global current_locations
	if not current_locations:
		print("No current_locations available for trailer list")
		return []
	
	print(f"Getting trailer list from {len(current_locations)} locations")
	trailer_list = []
	for location in current_locations:
		print(f"Processing location {location.name} with {len(location.trailers)} trailers")
		for trailer in location.trailers:
			seal_display = trailer.seal_number if trailer.seal_number else "Not set"
			trailer_display = trailer.trailer_number if trailer.trailer_number else "Not set"
			
			# Color coding for dropdown
			if trailer.dispatched:
				color = "🟢"  # Green for dispatched
				status = "DISPATCHED"
			else:
				color = "🔴"  # Red for un-dispatched
				status = "Active"
			
			trailer_entry = f"{color} {location.name} - Trailer #{trailer.number} (LD: {trailer.ld_number}) - Seal: {seal_display}, Trailer: {trailer_display} [{status}]"
			trailer_list.append(trailer_entry)
			print(f"Added trailer: {trailer_entry}")
	
	print(f"Returning {len(trailer_list)} trailers")
	return trailer_list


def get_trailer_info_by_id(trailer_identifier):
	"""Get current seal and trailer numbers for the selected trailer by identifier"""
	global current_locations
	if not current_locations or not trailer_identifier:
		print(f"get_trailer_info_by_id: No locations ({current_locations is None}) or no identifier ({trailer_identifier})")
		return "", ""
	
	try:
		print(f"get_trailer_info_by_id: Processing identifier: {trailer_identifier}")
		# Parse trailer identifier: "LocationName_TrailerNumber"
		if "_" not in trailer_identifier:
			print(f"get_trailer_info_by_id: Invalid format, no underscore found")
			return "", ""
		
		location_name, trailer_num_str = trailer_identifier.split("_", 1)
		trailer_num = int(trailer_num_str)
		
		print(f"get_trailer_info_by_id: Looking for location '{location_name}', trailer #{trailer_num}")
		
		# Find the location and trailer
		for location in current_locations:
			if location.name == location_name:
				print(f"get_trailer_info_by_id: Found location {location_name}")
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						print(f"get_trailer_info_by_id: Found trailer #{trailer_num}, seal: '{trailer.seal_number}', trailer: '{trailer.trailer_number}'")
						return trailer.seal_number, trailer.trailer_number
		
		print(f"get_trailer_info_by_id: Trailer #{trailer_num} not found at {location_name}")
		return "", ""
		
	except Exception as e:
		print(f"get_trailer_info_by_id: Error: {e}")
		return "", ""


def edit_trailer_info_by_id(trailer_identifier, seal_number, trailer_number):
	"""Edit trailer seal and trailer numbers by identifier"""
	global current_locations
	if not current_locations or not trailer_identifier:
		print(f"edit_trailer_info_by_id: No locations or identifier")
		return "No trailer identifier provided or no locations available."
	
	try:
		print(f"edit_trailer_info_by_id: Processing identifier: {trailer_identifier}")
		print(f"edit_trailer_info_by_id: Seal: '{seal_number}', Trailer: '{trailer_number}'")
		
		# Parse trailer identifier: "LocationName_TrailerNumber"
		if "_" not in trailer_identifier:
			print(f"edit_trailer_info_by_id: Invalid format, no underscore found")
			return "Invalid trailer identifier format. Use: LocationName_TrailerNumber"
		
		location_name, trailer_num_str = trailer_identifier.split("_", 1)
		trailer_num = int(trailer_num_str)
		
		print(f"edit_trailer_info_by_id: Looking for location '{location_name}', trailer #{trailer_num}")
		
		# Find the location and trailer
		for location in current_locations:
			if location.name == location_name:
				print(f"edit_trailer_info_by_id: Found location {location_name}")
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						print(f"edit_trailer_info_by_id: Found trailer #{trailer_num}")
						if trailer.dispatched:
							print(f"edit_trailer_info_by_id: Trailer is dispatched, cannot edit")
							return f"❌ Cannot edit Trailer #{trailer_num} at {location_name} - it has been dispatched and is final."
						
						# Update trailer information
						old_seal = trailer.seal_number
						old_trailer = trailer.trailer_number
						trailer.seal_number = seal_number.strip() if seal_number else ""
						trailer.trailer_number = trailer_number.strip() if trailer_number else ""
						
						print(f"edit_trailer_info_by_id: Updated trailer #{trailer_num}: seal '{old_seal}' -> '{trailer.seal_number}', trailer '{old_trailer}' -> '{trailer.trailer_number}'")
						return f"✅ Updated Trailer #{trailer_num} at {location_name}: Seal #{trailer.seal_number}, Trailer #{trailer.trailer_number}"
		
		print(f"edit_trailer_info_by_id: Trailer #{trailer_num} not found at {location_name}")
		return f"❌ Trailer #{trailer_num} not found at {location_name}."
		
	except Exception as e:
		print(f"edit_trailer_info_by_id: Error: {e}")
		return f"❌ Error updating trailer: {str(e)}"


def dispatch_trailer_by_id(trailer_identifier, confirm_dispatch):
	"""Dispatch a trailer (finalize it) by identifier"""
	global current_locations
	if not current_locations or not trailer_identifier:
		return "No trailer identifier provided or no locations available."
	
	if not confirm_dispatch:
		return "Dispatch cancelled. Trailer remains active."
	
	try:
		print(f"dispatch_trailer_by_id: Processing identifier: {trailer_identifier}")
		
		# Parse trailer identifier: "LocationName_TrailerNumber"
		if "_" not in trailer_identifier:
			return "Invalid trailer identifier format. Use: LocationName_TrailerNumber"
		
		location_name, trailer_num_str = trailer_identifier.split("_", 1)
		trailer_num = int(trailer_num_str)
		
		print(f"dispatch_trailer_by_id: Looking for location '{location_name}', trailer #{trailer_num}")
		
		# Find the location and trailer
		for location in current_locations:
			if location.name == location_name:
				print(f"dispatch_trailer_by_id: Found location {location_name}")
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						print(f"dispatch_trailer_by_id: Found trailer #{trailer_num}")
						if trailer.dispatched:
							return f"❌ Trailer #{trailer_num} at {location_name} is already dispatched."
						
						# Dispatch the trailer
						trailer.dispatched = True
						trailer.dispatch_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
						
						print(f"dispatch_trailer_by_id: Dispatched trailer #{trailer_num} at {location_name}")
						return f"✅ DISPATCHED: Trailer #{trailer_num} at {location_name} has been finalized and shipped. Seal: {trailer.seal_number}, Trailer: {trailer.trailer_number}"
		
		return f"❌ Trailer #{trailer_num} not found at {location_name}."
		
	except Exception as e:
		print(f"dispatch_trailer_by_id: Error: {e}")
		return f"❌ Error dispatching trailer: {str(e)}"


def on_trailer_button_click(location_name, trailer_num):
	"""Handle trailer button click - populate editing fields"""
	global current_locations
	if not current_locations:
		return "No locations available", "", "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
	
	try:
		print(f"on_trailer_button_click: Looking for {location_name} Trailer #{trailer_num}")
		
		# Find the trailer
		for location in current_locations:
			if location.name == location_name:
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						# Create display info
						status = "DISPATCHED" if trailer.dispatched else "Active"
						seal_display = trailer.seal_number if trailer.seal_number else "Not set"
						trailer_display = trailer.trailer_number if trailer.trailer_number else "Not set"
						
						selected_info = f"Selected: {location_name} - Trailer #{trailer_num} (LD: {trailer.ld_number}, {trailer.stacks} stacks) - Status: {status}"
						selected_info += f"\nCurrent Seal #: {seal_display} | Current Trailer #: {trailer_display}"
						
						# Show editing fields
						return (
							selected_info,
							trailer.seal_number,
							trailer.trailer_number,
							gr.update(visible=True),  # seal_input
							gr.update(visible=True),  # trailer_num_input
							gr.update(visible=True),  # update_trailer_btn
							gr.update(visible=True),  # dispatch_btn
							gr.update(visible=True),  # trailer_status
							gr.update(visible=True)   # dispatch_confirm
						)
		
		return f"Trailer #{trailer_num} not found at {location_name}", "", "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
		
	except Exception as e:
		print(f"on_trailer_button_click: Error: {e}")
		return f"Error selecting trailer: {str(e)}", "", "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


def update_trailer_from_button(location_name, trailer_num, seal_number, trailer_number):
	"""Update trailer information from button click"""
	global current_locations
	if not current_locations:
		return "No locations available"
	
	try:
		print(f"update_trailer_from_button: Updating {location_name} Trailer #{trailer_num}")
		
		# Find the trailer
		for location in current_locations:
			if location.name == location_name:
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						if trailer.dispatched:
							return f"❌ Cannot edit Trailer #{trailer_num} at {location_name} - it has been dispatched and is final."
						
						# Update trailer information
						old_seal = trailer.seal_number
						old_trailer = trailer.trailer_number
						trailer.seal_number = seal_number.strip() if seal_number else ""
						trailer.trailer_number = trailer_number.strip() if trailer_number else ""
						
						print(f"update_trailer_from_button: Updated trailer #{trailer_num}: seal '{old_seal}' -> '{trailer.seal_number}', trailer '{old_trailer}' -> '{trailer.trailer_number}'")
						return f"✅ Updated Trailer #{trailer_num} at {location_name}: Seal #{trailer.seal_number}, Trailer #{trailer.trailer_number}"
		
		return f"❌ Trailer #{trailer_num} not found at {location_name}."
		
	except Exception as e:
		print(f"update_trailer_from_button: Error: {e}")
		return f"❌ Error updating trailer: {str(e)}"


def dispatch_trailer_from_button(location_name, trailer_num, confirm_dispatch):
	"""Dispatch trailer from button click"""
	global current_locations
	if not current_locations:
		return "No locations available"
	
	if not confirm_dispatch:
		return "Dispatch cancelled. Trailer remains active."
	
	try:
		print(f"dispatch_trailer_from_button: Dispatching {location_name} Trailer #{trailer_num}")
		
		# Find the trailer
		for location in current_locations:
			if location.name == location_name:
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						if trailer.dispatched:
							return f"❌ Trailer #{trailer_num} at {location_name} is already dispatched."
						
						# Dispatch the trailer
						trailer.dispatched = True
						trailer.dispatch_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
						
						print(f"dispatch_trailer_from_button: Dispatched trailer #{trailer_num} at {location_name}")
						return f"✅ DISPATCHED: Trailer #{trailer_num} at {location_name} has been finalized and shipped. Seal: {trailer.seal_number}, Trailer: {trailer.trailer_number}"
		
		return f"❌ Trailer #{trailer_num} not found at {location_name}."
		
	except Exception as e:
		print(f"dispatch_trailer_from_button: Error: {e}")
		return f"❌ Error dispatching trailer: {str(e)}"


def populate_trailer_buttons(trailer_buttons_data):
	"""Populate trailer buttons with data from relay creation"""
	button_updates = []
	
	# Initialize all buttons as hidden
	for i in range(12):
		button_updates.append(gr.update(visible=False, value=""))
	
	# Populate buttons with trailer data
	for i, trailer_data in enumerate(trailer_buttons_data[:12]):  # Max 12 buttons
		button_text = trailer_data['text']
		button_variant = trailer_data['variant']
		button_updates[i] = gr.update(visible=True, value=button_text, variant=button_variant)
	
	return button_updates


def on_trailer_button_click_from_text(button_text, button_index):
	"""Handle trailer button click from button text"""
	global current_locations, selected_trailer_location, selected_trailer_number
	
	if not button_text or not current_locations:
		return "No trailer selected", "", "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
	
	try:
		print(f"on_trailer_button_click_from_text: Button text: {button_text}")
		
		# Parse button text to extract location and trailer number
		# Format: "🔴/🟢 Location - Trailer #X (DISPATCHED)" or "🔴/🟢 Location - Trailer #X"
		parts = button_text.split(" - ")
		if len(parts) < 2:
			return "Invalid button format", "", "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
		
		# Remove color emoji from location name
		location_name = parts[0].split(" ", 1)[-1]  # Remove emoji and keep location name
		trailer_part = parts[1]
		
		# Extract trailer number from "Trailer #X"
		trailer_num = int(trailer_part.split("#")[1].split(" ")[0])
		
		print(f"on_trailer_button_click_from_text: Looking for {location_name} Trailer #{trailer_num}")
		
		# Store selected trailer info
		selected_trailer_location = location_name
		selected_trailer_number = trailer_num
		
		# Find the trailer
		for location in current_locations:
			if location.name == location_name:
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						# Create display info
						status = "DISPATCHED" if trailer.dispatched else "Active"
						seal_display = trailer.seal_number if trailer.seal_number else "Not set"
						trailer_display = trailer.trailer_number if trailer.trailer_number else "Not set"
						
						selected_info = f"Selected: {location_name} - Trailer #{trailer_num} (LD: {trailer.ld_number}, {trailer.stacks} stacks) - Status: {status}"
						selected_info += f"\nCurrent Seal #: {seal_display} | Current Trailer #: {trailer_display}"
						
						# Show editing fields
						return (
							selected_info,
							trailer.seal_number,
							trailer.trailer_number,
							gr.update(visible=True),  # seal_input
							gr.update(visible=True),  # trailer_num_input
							gr.update(visible=True),  # update_trailer_btn
							gr.update(visible=True),  # dispatch_btn
							gr.update(visible=True),  # trailer_status
							gr.update(visible=True)   # dispatch_confirm
						)
		
		return f"Trailer #{trailer_num} not found at {location_name}", "", "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
		
	except Exception as e:
		print(f"on_trailer_button_click_from_text: Error: {e}")
		return f"Error selecting trailer: {str(e)}", "", "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


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


def save_orders_with_confirmation(orders, date_str, day_num):
	"""
	Save all orders to a single comprehensive JSON file with confirmed date/day information
	
	This function creates one consolidated JSON file that includes:
	- All order data for all routes and locations
	- Confirmed date and day information
	- Complete metadata for relay generation
	
	Args:
		orders: List of Order objects (all orders for all routes)
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
		
		# Convert orders to simple JSON format
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
		
		# Create simple data structure
		file_data = {
			"orders": orders_data,
			"metadata": {
				"total_orders": len(orders),
				"confirmed_date": date_str,
				"confirmed_day": day_num,
				"generation_timestamp": datetime.now().isoformat()
			}
		}
		
		
		# Save to single JSON file
		with open(filename, 'w') as f:
			json.dump(file_data, f, indent=2)
		
		print(f"Saved {len(orders)} orders to file: {filename}")
		
	except Exception as e:
		print(f"Error saving orders: {e}")


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


def save_selection_state_global(order_date, order_day):
	"""Save date and day selection to a persistent state file (global function)"""
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


def load_selection_state_global():
	"""Load date and day selection from persistent state file (global function)"""
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


def confirm_date_and_day_global(order_date, order_day):
	"""Confirm and lock in the selected date and day with persistent storage (global function)"""
	
	
	if not order_date or not order_date.strip():
		return "Please enter a date first", "Please select date and day, then confirm"
	
	# Handle the case where order_day might be 'None' string or None
	if not order_day or order_day == 'None' or order_day == 'null':
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
	if save_selection_state_global(order_date, order_day):
		status_msg = f"CONFIRMED: {order_date.strip()} Day {order_day}\nSaved to persistent state\nReady to generate orders!"
		return f"Date and day confirmed: {order_date.strip()} Day {order_day}", status_msg
	else:
		return "Error saving selection state", "Please try again"


def create_orders_with_confirmed_data_global():
	"""Create orders using the confirmed date and day from persistent state (global function)"""
	
	
	# Load confirmed data from file
	confirmed_date, confirmed_day, is_confirmed = load_selection_state_global()
	
	if not is_confirmed or not confirmed_date:
		return "Please confirm date and day selection first"
	
	# Automatically use all 235 products for comprehensive order generation
	return create_orders_for_date_and_day(confirmed_date, confirmed_day, 235)


def clear_selection_state_global():
	"""Clear the persistent selection state (global function)"""
	try:
		import os
		if os.path.exists("selection_state.json"):
			os.remove("selection_state.json")
			print("Cleared selection state")
		
		return "", "1", "Selection cleared. Please select date and day, then confirm"
	except Exception as e:
		print(f"Error clearing selection state: {e}")
		return "", "1", "Error clearing selection"


def initialize_order_ui_global():
	"""Initialize the order UI with any existing confirmed state (global function)"""
	try:
		confirmed_date, confirmed_day, is_confirmed = load_selection_state_global()
		
		if is_confirmed and confirmed_date:
			status_msg = f"CONFIRMED: {confirmed_date} Day {confirmed_day}\nLoaded from persistent state\nReady to generate orders!"
			return confirmed_date, confirmed_day, status_msg
		else:
			return "", "1", "Please select date and day, then confirm"
	except Exception as e:
		return "", "1", "Please select date and day, then confirm"


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
	
	with gr.Tab("System Overview"):
		gr.Markdown("# Virtual Relay System - Professional Demo")
		gr.Markdown("""
		## **Manufacturing Logistics Management System**
		
		This system demonstrates a comprehensive order management and relay generation platform designed for manufacturing facilities. The application showcases real-world software engineering practices including API integration, data persistence, and professional user interface design.
		
		### **Key Features:**
		
		#### **Order Management**
		- **API-Driven Date Selection**: North Carolina timezone integration via WorldTimeAPI
		- **Structured Day Selection**: Day 1, 2, 4, 5, or 6 workflow management
		- **Persistent State Management**: JSON file-based confirmation system
		- **Comprehensive Order Generation**: 235 products across all routes and locations
		
		#### **Relay Generation**
		- **Automated Trailer Assignment**: 98-stack limit with automatic trailer #2, #3 creation
		- **Location-Based Routing**: Multi-trailer support for high-volume locations
		- **JSON Data Persistence**: Complete order-to-relay workflow with file storage
		- **Professional Data Management**: Comprehensive metadata tracking
		
		#### **Technical Architecture**
		- **Object-Oriented Design**: Clean separation of concerns with Order, Route, and Relay classes
		- **File I/O Operations**: JSON serialization and deserialization for data persistence
		- **Error Handling**: Comprehensive exception handling with fallback mechanisms
		- **State Management**: Professional application state handling across sessions
		
		### **Software Engineering Practices Demonstrated:**
		
		- **API Integration**: WorldTimeAPI for real-time timezone management
		- **Data Persistence**: JSON file storage for orders and system state
		- **User Experience Design**: Professional interface with clear workflow guidance
		- **Error Resilience**: Robust error handling and user feedback systems
		- **Separation of Concerns**: Modular architecture with distinct system responsibilities
		
		### **System Statistics:**
		""")
		
		# System status display
		with gr.Row():
			with gr.Column():
				gr.Markdown("**System Status:**")
				system_status = gr.Textbox(label="Initialization Status", value=initial_status, interactive=False)
				gr.Markdown("**Available Order Dates:**")
				date_dropdown_1 = gr.Dropdown(choices=initial_dates, label="Dates with Orders", interactive=False)
			with gr.Column():
				gr.Markdown("**System Capabilities:**")
				gr.Markdown("""
				- **Products**: 235 unique items
				- **Routes**: 15 delivery routes
				- **Locations**: Multi-location support
				- **API Integration**: North Carolina timezone
				- **Data Persistence**: JSON file storage
				- **Trailer Management**: 98-stack limit with overflow
				""")
		
		gr.Markdown("""
		### **Getting Started:**
		
		1. **Orders Tab**: Get today's date, select day, confirm selection, then generate orders
		2. **Relay Tab**: Select generated orders to create automated relay assignments
		3. **Professional Workflow**: Complete order-to-relay process with persistent data storage
		
		---
		
		**Built with Python, Gradio, and WorldTimeAPI** | **Professional Manufacturing Logistics Demo**
		""")
		
		# System management buttons
		with gr.Row():
			refresh_btn = gr.Button("Refresh System Status")
			cleanup_btn = gr.Button("Clean Up Duplicate Files", variant="secondary")
		
		# Cleanup status display
		cleanup_status = gr.Textbox(label="Cleanup Status", interactive=False, visible=False)
		
		refresh_btn.click(lambda: (initialize_systems(), get_initial_dates()), outputs=[system_status, date_dropdown_1])
		cleanup_btn.click(manual_cleanup_order_files, outputs=[cleanup_status])

	with gr.Tab("Orders"):
		gr.Markdown("## Order Management")
		
		with gr.Row():
			with gr.Column(scale=1):
				with gr.Row():
					order_date_input = gr.Textbox(label="Order Date", placeholder="MM/DD/YYYY (e.g., 12/25/2024)", interactive=True)
					get_today_btn = gr.Button("Get Today's Date", variant="secondary", size="sm")
				order_creation_day_dropdown = gr.Dropdown(
					choices=["1", "2", "4", "5", "6"],
					label="Select Day",
					interactive=True,
					value="1",
					allow_custom_value=False
				)
				with gr.Row():
					confirm_date_day_btn = gr.Button("Confirm Date & Day Selection", variant="primary")
					clear_selection_btn = gr.Button("Clear Selection", variant="secondary")
				date_day_status = gr.Textbox(label="Selection Status", value="Please select date and day, then confirm", interactive=False)
				
				simulate_btn = gr.Button("Generate Orders for Confirmed Date & Day", variant="primary")
				sim_msg = gr.Textbox(label="Order Creation Status", interactive=False)
		
		
		# 🎓 API Integration: Connect the "Get Today's Date" button to our API function
		def get_todays_date():
			"""Get current North Carolina date and populate the order date field"""
			nc_date = get_north_carolina_date_for_orders()
			return nc_date
		
		# Initialize UI with existing state
		initial_date, initial_day, initial_status = initialize_order_ui_global()
		
		# Set initial values for UI components (only if we have valid values)
		if initial_date:
			order_date_input.value = initial_date
		# Don't try to set dropdown value during initialization - let it use its default
		if initial_status:
			date_day_status.value = initial_status
		
		# Debug function to check dropdown value
		def debug_dropdown_value(day_value):
			# Don't return anything - this is just for debugging
			pass
		
		# Function to initialize dropdown with saved day value
		def initialize_dropdown_with_saved_day():
			if initial_day and initial_day in ["1", "2", "4", "5", "6"]:
				return initial_day
			else:
				return "1"
		
		
		# Add change event to debug dropdown
		order_creation_day_dropdown.change(debug_dropdown_value, inputs=[order_creation_day_dropdown], outputs=[])
		
		# Initialize dropdown with saved value after UI is loaded
		initialized_day = initialize_dropdown_with_saved_day()
		
		confirm_date_day_btn.click(confirm_date_and_day_global, inputs=[order_date_input, order_creation_day_dropdown], outputs=[sim_msg, date_day_status])
		clear_selection_btn.click(clear_selection_state_global, inputs=None, outputs=[order_date_input, order_creation_day_dropdown, date_day_status])
		simulate_btn.click(create_orders_with_confirmed_data_global, inputs=None, outputs=[sim_msg])
		get_today_btn.click(get_todays_date, inputs=None, outputs=[order_date_input])

	with gr.Tab("Relay"):
		gr.Markdown("## Relay Generation")
		
		# Get initial orders
		initial_orders, _ = get_available_orders_for_relay()
		
		refresh_orders_btn = gr.Button("Refresh Available Orders")
		order_select = gr.Dropdown(choices=initial_orders, label="Select Orders for Relay", interactive=True, multiselect=True)
		create_btn = gr.Button("Create Relay from Selected Orders", variant="primary")
		summary_out = gr.Textbox(label="Relay Summary", lines=12, value="Create orders first, then select orders to generate relay")
		details_out = gr.Textbox(label="Trailer & Order Details", lines=16)
		
		# Trailer editing section
		gr.Markdown("## Click on a Trailer to Edit")
		gr.Markdown("**Click any trailer button below to edit its information:**")
		
		# Create a grid of trailer buttons (we'll show/hide them dynamically)
		with gr.Row():
			trailer_btn_1 = gr.Button("", visible=False, size="sm")
			trailer_btn_2 = gr.Button("", visible=False, size="sm")
			trailer_btn_3 = gr.Button("", visible=False, size="sm")
		with gr.Row():
			trailer_btn_4 = gr.Button("", visible=False, size="sm")
			trailer_btn_5 = gr.Button("", visible=False, size="sm")
			trailer_btn_6 = gr.Button("", visible=False, size="sm")
		with gr.Row():
			trailer_btn_7 = gr.Button("", visible=False, size="sm")
			trailer_btn_8 = gr.Button("", visible=False, size="sm")
			trailer_btn_9 = gr.Button("", visible=False, size="sm")
		with gr.Row():
			trailer_btn_10 = gr.Button("", visible=False, size="sm")
			trailer_btn_11 = gr.Button("", visible=False, size="sm")
			trailer_btn_12 = gr.Button("", visible=False, size="sm")
		
		# Selected trailer info display
		selected_trailer_info = gr.Textbox(label="Selected Trailer", interactive=False, value="No trailer selected")
		
		# Editing fields (hidden until trailer is selected)
		with gr.Row():
			seal_input = gr.Textbox(label="Seal Number", placeholder="Enter seal number", visible=False)
			trailer_num_input = gr.Textbox(label="Trailer Number", placeholder="Enter trailer number", visible=False)
		
		with gr.Row():
			update_trailer_btn = gr.Button("Update Trailer Information", variant="secondary", visible=False)
			dispatch_btn = gr.Button("Dispatch Trailer", variant="stop", visible=False)
		
		# Status displays
		trailer_status = gr.Textbox(label="Trailer Update Status", interactive=False, visible=False)
		dispatch_status = gr.Textbox(label="Dispatch Status", interactive=False, visible=False)
		
		# Dispatch confirmation (hidden until trailer is selected)
		dispatch_confirm = gr.Checkbox(label="I confirm I want to dispatch this trailer (PERMANENT ACTION)", value=False, visible=False)

		def refresh_relay_orders():
			"""Refresh the relay order dropdown with current order data"""
			orders, _ = get_available_orders_for_relay()
			return gr.Dropdown(choices=orders)

		def create_relay_from_orders(selected_orders):
			"""Create relay from selected orders loaded from JSON files"""
			if not selected_orders:
				empty_updates = [gr.update(visible=False, value="") for _ in range(12)]
				return "Please select at least one order first.", "", *empty_updates
			
			try:
				ensure_order_system()
				ensure_relay_system()
				
				# Get the actual order data from JSON files
				_, order_data = get_available_orders_for_relay()
				selected_order_data = []
				
				for selected_order_display in selected_orders:
					if selected_order_display in order_data:
						order_info = order_data[selected_order_display]
						selected_order_data.append(order_info)
				
				if not selected_order_data:
					empty_updates = [gr.update(visible=False, value="") for _ in range(12)]
					return "No valid orders found for selection.", "", *empty_updates
				
				# Create relay from the selected orders
				first_order_info = selected_order_data[0]
				metadata = first_order_info['metadata']
				
				# Use confirmed date/day from metadata
				date_part = metadata['confirmed_date']
				day_part = metadata['confirmed_day']
				
				# Create relay using the existing system
				summary, details = create_relay(date_part, day_part)
				
				# Add information about selected orders
				order_info_text = f"\n\nSelected Orders: {selected_order_display}\n"
				order_info_text += f"Date: {date_part} Day {day_part}\n"
				order_info_text += f"Total Orders: {len(first_order_info['orders'])}"
				
				# Get trailer button data and populate buttons
				# Extract orders from selected_order_data
				all_orders = []
				for order_info in selected_order_data:
					all_orders.extend(order_info['orders'])
				locations = create_relay_from_orders_data(all_orders)
				trailer_buttons_data = []
				for loc in locations:
					for trailer in loc.trailers:
						if trailer.dispatched:
							button_text = f"🟢 {loc.name} - Trailer #{trailer.number} (DISPATCHED)"
							button_variant = "secondary"
						else:
							button_text = f"🔴 {loc.name} - Trailer #{trailer.number}"
							button_variant = "primary"
						
						trailer_buttons_data.append({
							'text': button_text,
							'variant': button_variant,
							'location': loc.name,
							'trailer_num': trailer.number,
							'seal': trailer.seal_number,
							'trailer': trailer.trailer_number,
							'dispatched': trailer.dispatched,
							'ld': trailer.ld_number,
							'stacks': trailer.stacks
						})
				
				button_updates = populate_trailer_buttons(trailer_buttons_data)
				
				return summary + order_info_text, details, *button_updates
				
			except Exception as e:
				# Return empty button updates for error case
				empty_updates = [gr.update(visible=False, value="") for _ in range(12)]
				return f"Error creating relay from orders: {str(e)}", "", *empty_updates

		refresh_orders_btn.click(refresh_relay_orders, inputs=None, outputs=[order_select])
		create_btn.click(create_relay_from_orders, inputs=[order_select], outputs=[
			summary_out, details_out, 
			trailer_btn_1, trailer_btn_2, trailer_btn_3, trailer_btn_4, trailer_btn_5, trailer_btn_6,
			trailer_btn_7, trailer_btn_8, trailer_btn_9, trailer_btn_10, trailer_btn_11, trailer_btn_12
		])
		
		# Trailer editing event handlers
		update_trailer_btn.click(
			lambda seal, trailer: update_trailer_from_button(selected_trailer_location, selected_trailer_number, seal, trailer),
			inputs=[seal_input, trailer_num_input], 
			outputs=[trailer_status]
		)
		
		# Dispatch event handler
		dispatch_btn.click(
			lambda confirm: dispatch_trailer_from_button(selected_trailer_location, selected_trailer_number, confirm),
			inputs=[dispatch_confirm], 
			outputs=[dispatch_status]
		)
		
		# Trailer button click handlers
		trailer_buttons = [trailer_btn_1, trailer_btn_2, trailer_btn_3, trailer_btn_4, trailer_btn_5, trailer_btn_6,
		                  trailer_btn_7, trailer_btn_8, trailer_btn_9, trailer_btn_10, trailer_btn_11, trailer_btn_12]
		
		for i, btn in enumerate(trailer_buttons):
			btn.click(
				lambda btn_text, idx=i: on_trailer_button_click_from_text(btn_text, idx),
				inputs=[btn],
				outputs=[selected_trailer_info, seal_input, trailer_num_input, 
				        gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), 
				        gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)]
			)



if __name__ == "__main__":
	demo.launch()


