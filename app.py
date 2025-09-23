import os
import json
import streamlit as st
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
		return f"Error creating relay: {str(e)}", "", []


def get_trailer_list():
	"""Get list of all trailers for editing"""
	global current_locations
	if not current_locations:
		return []
	
	trailer_list = []
	for location in current_locations:
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
	
	return trailer_list


def get_trailer_info_by_id(trailer_identifier):
	"""Get current seal and trailer numbers for the selected trailer by identifier"""
	global current_locations
	if not current_locations or not trailer_identifier:
		return "No trailer selected", "", ""
	
	try:
		# Parse trailer identifier: "LocationName_TrailerNumber"
		if "_" not in trailer_identifier:
			return "Invalid trailer identifier format", "", ""
		
		location_name, trailer_num_str = trailer_identifier.split("_", 1)
		trailer_num = int(trailer_num_str)
		
		# Find the location and trailer
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
						
						return selected_info, trailer.seal_number, trailer.trailer_number
		
		return f"Trailer #{trailer_num} not found at {location_name}", "", ""
		
	except Exception as e:
		return f"Error selecting trailer: {str(e)}", "", ""


def edit_trailer_info_by_id(trailer_identifier, seal_number, trailer_number):
	"""Edit trailer seal and trailer numbers by identifier"""
	global current_locations
	if not current_locations or not trailer_identifier:
		return "No trailer identifier provided or no locations available."
	
	try:
		# Parse trailer identifier: "LocationName_TrailerNumber"
		if "_" not in trailer_identifier:
			return "Invalid trailer identifier format. Use: LocationName_TrailerNumber"
		
		location_name, trailer_num_str = trailer_identifier.split("_", 1)
		trailer_num = int(trailer_num_str)
		
		# Find the location and trailer
		for location in current_locations:
			if location.name == location_name:
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						if trailer.dispatched:
							return f"❌ Cannot edit Trailer #{trailer_num} at {location_name} - it has been dispatched and is final."
						
						# Update trailer information
						trailer.seal_number = seal_number.strip() if seal_number else ""
						trailer.trailer_number = trailer_number.strip() if trailer_number else ""
						
						return f"✅ Updated Trailer #{trailer_num} at {location_name}: Seal #{trailer.seal_number}, Trailer #{trailer.trailer_number}"
		
		return f"❌ Trailer #{trailer_num} not found at {location_name}."
		
	except Exception as e:
		return f"❌ Error updating trailer: {str(e)}"


def dispatch_trailer_by_id(trailer_identifier, confirm_dispatch):
	"""Dispatch a trailer (finalize it) by identifier"""
	global current_locations
	if not current_locations or not trailer_identifier:
		return "No trailer identifier provided or no locations available."
	
	if not confirm_dispatch:
		return "Dispatch cancelled. Trailer remains active."
	
	try:
		# Parse trailer identifier: "LocationName_TrailerNumber"
		if "_" not in trailer_identifier:
			return "Invalid trailer identifier format. Use: LocationName_TrailerNumber"
		
		location_name, trailer_num_str = trailer_identifier.split("_", 1)
		trailer_num = int(trailer_num_str)
		
		# Find the location and trailer
		for location in current_locations:
			if location.name == location_name:
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						if trailer.dispatched:
							return f"❌ Trailer #{trailer_num} at {location_name} is already dispatched."
						
						# Dispatch the trailer
						trailer.dispatched = True
						trailer.dispatch_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
						
						return f"✅ DISPATCHED: Trailer #{trailer_num} at {location_name} has been finalized and shipped. Seal: {trailer.seal_number}, Trailer: {trailer.trailer_number}"
		
		return f"❌ Trailer #{trailer_num} not found at {location_name}."
		
	except Exception as e:
		return f"❌ Error dispatching trailer: {str(e)}"


def get_trailer_info(location_name, trailer_num):
    """Get trailer information for Streamlit display"""
    global current_locations
    if not current_locations:
        return None
    
    try:
        # Find the trailer
        for location in current_locations:
            if location.name == location_name:
                for trailer in location.trailers:
                    if trailer.number == trailer_num:
                        return trailer
        return None
    except Exception as e:
        print(f"get_trailer_info: Error: {e}")
        return None


def update_trailer_from_button(location_name, trailer_num, seal_number, trailer_number):
	"""Update trailer information from button click"""
	global current_locations
	if not current_locations:
		return "No locations available"
	
	try:
		# Find the trailer
		for location in current_locations:
			if location.name == location_name:
				for trailer in location.trailers:
					if trailer.number == trailer_num:
						if trailer.dispatched:
							return f"❌ Cannot edit Trailer #{trailer_num} at {location_name} - it has been dispatched and is final."
						
						# Update trailer information
						trailer.seal_number = seal_number.strip() if seal_number else ""
						trailer.trailer_number = trailer_number.strip() if trailer_number else ""
						
						return f"✅ Updated Trailer #{trailer_num} at {location_name}: Seal #{trailer.seal_number}, Trailer #{trailer.trailer_number}"
		
		return f"❌ Trailer #{trailer_num} not found at {location_name}."
		
	except Exception as e:
		return f"❌ Error updating trailer: {str(e)}"


def dispatch_trailer_from_button(location_name, trailer_num, confirm_dispatch):
	"""Dispatch trailer from button click"""
	global current_locations
	if not current_locations:
		return "No locations available"
	
	if not confirm_dispatch:
		return "Dispatch cancelled. Trailer remains active."
	
	try:
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
						
						return f"✅ DISPATCHED: Trailer #{trailer_num} at {location_name} has been finalized and shipped. Seal: {trailer.seal_number}, Trailer: {trailer.trailer_number}"
		
		return f"❌ Trailer #{trailer_num} not found at {location_name}."
		
	except Exception as e:
		return f"❌ Error dispatching trailer: {str(e)}"


def create_interactive_relay_display(locations):
	"""Create interactive relay display with clickable trailer buttons organized by location"""
	global current_locations
	current_locations = locations
	
	# Create HTML for interactive relay display
	html_content = "<div style='font-family: monospace; line-height: 1.6;'>"
	html_content += "<h3>🚛 INTERACTIVE RELAY DISPLAY</h3>"
	html_content += "<p><strong>Click any trailer button to edit its information</strong></p>"
	
	for location in locations:
		html_content += f"<div style='margin: 20px 0; padding: 15px; border: 2px solid #ddd; border-radius: 8px;'>"
		html_content += f"<h4 style='margin: 0 0 10px 0; color: #333;'>{location.name}</h4>"
		html_content += f"<p style='margin: 5px 0; color: #666;'>Total: {location.total_stacks} stacks, {len(location.trailers)} trailers</p>"
		
		# Create trailer buttons for this location
		for trailer in location.trailers:
			# Determine button styling based on dispatch status
			if trailer.dispatched:
				button_color = "#28a745"  # Green for dispatched
				button_text = f"🟢 Trailer #{trailer.number} (DISPATCHED)"
				status_text = "DISPATCHED"
			else:
				button_color = "#dc3545"  # Red for active
				button_text = f"🔴 Trailer #{trailer.number}"
				status_text = "Active"
			
			# Create trailer display with identifier
			trailer_id = f"{location.name}_{trailer.number}"
			html_content += f"""
			<div style='margin: 8px 0; display: inline-block; margin-right: 15px; padding: 10px; 
				border: 2px solid {button_color}; border-radius: 6px; background-color: #f8f9fa;'>
				<div style='background-color: {button_color}; color: white; padding: 6px 10px; 
					border-radius: 4px; font-weight: bold; text-align: center; margin-bottom: 5px;'>
					{button_text}
				</div>
				<div style='font-size: 12px; color: #666; margin: 2px 0;'>
					<strong>ID:</strong> {trailer_id}
				</div>
				<div style='font-size: 12px; color: #666; margin: 2px 0;'>
					<strong>LD:</strong> {trailer.ld_number} | <strong>Stacks:</strong> {trailer.stacks} | <strong>Status:</strong> {status_text}
				</div>
				<div style='font-size: 11px; color: #888; margin-top: 4px; font-style: italic;'>
					Type "{trailer_id}" below to edit
				</div>
			</div>
			"""
		
		html_content += "</div>"
	
	html_content += "</div>"
	
	# Add JavaScript for trailer selection
	html_content += """
	<script>
	function selectTrailer(location, trailerNum) {
		// This will be handled by Gradio's JavaScript integration
		console.log('Selected trailer:', location, trailerNum);
		// Trigger Gradio event
		window.dispatchEvent(new CustomEvent('trailer_selected', {
			detail: { location: location, trailerNum: trailerNum }
		}));
	}
	</script>
	"""
	
	return html_content


def on_trailer_button_click_from_text(button_text, button_index):
	"""Handle trailer button click from button text"""
	global current_locations, selected_trailer_location, selected_trailer_number
	
	if not button_text or not current_locations:
		return "No trailer selected", "", "", "", "", "", "", "", ""
	
	try:
		# Parse button text to extract location and trailer number
		# Format: "🔴/🟢 Location - Trailer #X (DISPATCHED)" or "🔴/🟢 Location - Trailer #X"
		parts = button_text.split(" - ")
		if len(parts) < 2:
			return "Invalid button format", "", "", "", "", "", "", "", ""
		
		# Remove color emoji from location name
		location_name = parts[0].split(" ", 1)[-1]  # Remove emoji and keep location name
		trailer_part = parts[1]
		
		# Extract trailer number from "Trailer #X"
		trailer_num = int(trailer_part.split("#")[1].split(" ")[0])
		
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
						
						# Return values for all outputs
						return (
							selected_info,  # selected_trailer_info
							trailer.seal_number,  # seal_input
							trailer.trailer_number,  # trailer_num_input
							"",  # seal_input (duplicate for visibility)
							"",  # trailer_num_input (duplicate for visibility)
							"",  # update_trailer_btn (duplicate for visibility)
							"",  # dispatch_btn (duplicate for visibility)
							"",  # trailer_status (duplicate for visibility)
							""   # dispatch_confirm (duplicate for visibility)
						)
		
		return f"Trailer #{trailer_num} not found at {location_name}", "", "", "", "", "", "", "", ""
		
	except Exception as e:
		return f"Error selecting trailer: {str(e)}", "", "", "", "", "", "", "", ""


def get_available_days_for_orders_streamlit(selected_date):
    """Get available days for orders for Streamlit"""
    if selected_date:
        return get_available_days_for_date(selected_date)
    else:
        return []


def get_available_days_for_date_streamlit(selected_date):
    """Get available days for a selected date for Streamlit"""
    if selected_date:
        return get_available_days_for_date(selected_date)
    else:
        return []


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


# Streamlit app configuration
st.set_page_config(
    page_title="Virtual Relay System",
    page_icon="🚛",
    layout="wide"
)

# Configure Streamlit for Render deployment
import os
if os.getenv("RENDER"):
    # Running on Render - configure for production
    st.config.set_option("server.port", int(os.getenv("PORT", 10000)))
    st.config.set_option("server.address", "0.0.0.0")
    st.config.set_option("server.headless", True)
    st.config.set_option("browser.gatherUsageStats", False)

# Initialize session state with proper error handling
def initialize_session_state():
    """Initialize session state safely"""
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
    """Initialize systems for Streamlit"""
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

# Initialize session state first
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

# Debug information
st.sidebar.markdown("---")
st.sidebar.markdown("**Debug Info**")
st.sidebar.write(f"Session state keys: {list(st.session_state.keys())}")

# Initialize systems immediately
try:
    if not initialize_streamlit_systems():
        st.error("Failed to initialize systems. Please refresh the page.")
        st.stop()
except Exception as e:
    st.error(f"Critical error initializing systems: {str(e)}")
    st.stop()

# Check if systems are available before showing UI
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
        - **Products**: 235+ unique items
				- **Routes**: 15 delivery routes
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
            result = manual_cleanup_order_files()
            st.info(result)

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
        
        # Max products
        max_products = st.number_input(
            "Max Products per Route",
            min_value=1,
            max_value=235,
            value=3,
            help="Maximum number of products per route"
        )
    
    with col2:
        st.subheader("Actions")
        
        if st.button("Get Today's Date"):
            today_date = get_north_carolina_date_for_orders()
            st.session_state.today_date = today_date
            st.rerun()
        
        if st.button("Generate Orders", type="primary"):
            if order_date and order_day:
                try:
                    # Validate date format
                    datetime.strptime(order_date, "%m/%d/%Y")
                    
                    # Create orders
                    orders = st.session_state.order_system.simulate_random_orders(
                        max_products, order_date, int(order_day)
                    )
                    
                    st.success(f"✅ Created {len(orders)} orders for {order_date} Day {order_day}")
                    
                    # Show summary
                    location_summary = {}
                    for order in orders:
                        if order.location not in location_summary:
                            location_summary[order.location] = {'orders': 0, 'trays': 0, 'stacks': 0}
                        location_summary[order.location]['orders'] += 1
                        location_summary[order.location]['trays'] += order.total_trays
                        location_summary[order.location]['stacks'] += order.total_stacks
                    
                    st.subheader("Order Summary by Location")
                    for location, stats in sorted(location_summary.items()):
                        st.write(f"**{location}**: {stats['orders']} orders, {stats['trays']} trays, {stats['stacks']} stacks")
                    
                except ValueError:
                    st.error("Invalid date format. Please use MM/DD/YYYY format.")
                except Exception as e:
                    st.error(f"Error creating orders: {str(e)}")
            else:
                st.error("Please enter a date and select a day.")
    
    # Display existing orders
    st.subheader("Existing Orders")
    all_orders = st.session_state.order_system.get_all_orders()
    
    if all_orders:
        st.write(f"Total Orders: {len(all_orders)}")
        
        # Group by date
        orders_by_date = {}
        for order in all_orders:
            date_part = order.order_date.split(" ")[0]
            if date_part not in orders_by_date:
                orders_by_date[date_part] = []
            orders_by_date[date_part].append(order)
        
        for date, orders in sorted(orders_by_date.items()):
            with st.expander(f"Orders for {date} ({len(orders)} orders)"):
                for order in orders:
                    st.write(f"**{order.order_id}**: Route {order.route_id} - {order.location} ({order.total_stacks} stacks)")
    else:
        st.info("No orders created yet.")
        
elif page == "Relay Management":
    st.header("Relay Management")
    
    # Get available orders
    all_orders = st.session_state.order_system.get_all_orders()
    
    if not all_orders:
        st.warning("No orders available. Please create orders first.")
    else:
        # Group orders by date
        orders_by_date = {}
        for order in all_orders:
            date_part = order.order_date.split(" ")[0]
            if date_part not in orders_by_date:
                orders_by_date[date_part] = []
            orders_by_date[date_part].append(order)
        
        st.subheader("Create Relay from Orders")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Date selection
            selected_date = st.selectbox(
                "Select Date",
                options=sorted(orders_by_date.keys()),
                help="Select the date for relay creation"
            )
            
            if selected_date:
                orders_for_date = orders_by_date[selected_date]
                
                # Day selection
                days = set()
                for order in orders_for_date:
                    if "Day" in order.order_date:
                        day_part = order.order_date.split("Day ")[1].split(" ")[0]
                        days.add(day_part)
                
                if days:
                    selected_day = st.selectbox(
                        "Select Day",
                        options=sorted(days),
                        help="Select the day for relay creation"
                    )
                else:
                    selected_day = "1"
        
        with col2:
            st.subheader("Actions")
            
            if st.button("Create Relay", type="primary"):
                if selected_date:
                    try:
                        # Create relay
                        locations = st.session_state.relay_system.create_automated_relay(
                            selected_date, int(selected_day) if selected_day else None
                        )
                        
                        if locations:
                            st.session_state.current_locations = locations
                            st.success(f"✅ Created relay with {len(locations)} locations")
                            
                            # Display relay summary
                            st.subheader("Relay Summary")
                            
                            total_trailers = 0
                            total_stacks = 0
                            
                            for location in locations:
                                total_trailers += len(location.trailers)
                                total_stacks += location.total_stacks
                                
                                with st.expander(f"{location.name} ({len(location.trailers)} trailers, {location.total_stacks} stacks)"):
                                    for trailer in location.trailers:
                                        status = "🟢 Dispatched" if trailer.dispatched else "🔴 Active"
                                        st.write(f"**Trailer #{trailer.number}**: {trailer.stacks} stacks - {status}")
                                        st.write(f"  LD: {trailer.ld_number}")
                                        if trailer.trailer_number:
                                            st.write(f"  Trailer #: {trailer.trailer_number}")
                                        if trailer.seal_number:
                                            st.write(f"  Seal #: {trailer.seal_number}")
                            
                            st.metric("Total Trailers", total_trailers)
                            st.metric("Total Stacks", total_stacks)
                        else:
                            st.error("Failed to create relay.")
                    except Exception as e:
                        st.error(f"Error creating relay: {str(e)}")
                else:
                    st.error("Please select a date.")
        
            # Display existing relay
            if st.session_state.current_locations:
                st.subheader("Current Relay")
                for location in st.session_state.current_locations:
                    with st.expander(f"{location.name} - {len(location.trailers)} trailers"):
                        for trailer in location.trailers:
                            status = "🟢 Dispatched" if trailer.dispatched else "🔴 Active"
                            st.write(f"**Trailer #{trailer.number}**: {trailer.stacks} stacks - {status}")

# Main execution
if __name__ == "__main__":
    # This will run the Streamlit app
    # The app will be executed by the Streamlit server when run with 'streamlit run app.py'
    pass


