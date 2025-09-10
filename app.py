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
	"""Get available orders from comprehensive JSON files for relay selection"""
	try:
		
		# Look for comprehensive order JSON files in the current directory
		import os
		import glob
		
		# First try to find consolidated order files
		consolidated_files = glob.glob("all_orders_*.json")
		confirmed_files = glob.glob("confirmed_orders_*.json")
		order_files = glob.glob("orders_*.json")
		
		
		formatted_orders = []
		order_data = {}
		
		# Process consolidated order files first (most preferred)
		for file_path in consolidated_files:
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
					
					# Format for display with consolidation info
					order_display = f"{order_id} - {confirmed_date} Day {confirmed_day} - {location} [CONSOLIDATED]"
					formatted_orders.append(order_display)
					order_data[order_display] = {
						'order': order,
						'confirmation': confirmation,
						'metadata': metadata
					}
					
			except Exception as e:
				print(f"Error reading consolidated order file {file_path}: {e}")
				continue
		
		# Process confirmed order files second (fallback)
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


def load_orders_from_json_files(selected_date: str, day_number: int = None):
	"""Load orders from JSON files for a specific date and day"""
	try:
		import glob
		
		print(f"DEBUG: load_orders_from_json_files called with date='{selected_date}', day={day_number}")
		
		# Look for consolidated order files first
		consolidated_files = glob.glob("all_orders_*.json")
		confirmed_files = glob.glob("confirmed_orders_*.json")
		order_files = glob.glob("orders_*.json")
		
		
		# Process consolidated order files first (most preferred)
		for file_path in consolidated_files:
			try:
				with open(file_path, 'r') as f:
					file_data = json.load(f)
				
				# Get confirmed date from metadata
				metadata = file_data.get('metadata', {})
				confirmed_date = metadata.get('confirmed_date', '')
				confirmed_day = metadata.get('confirmed_day', '1')
				
				print(f"DEBUG: File metadata - confirmed_date: '{confirmed_date}', confirmed_day: '{confirmed_day}'")
				
				# Check if this file matches our search criteria
				if confirmed_date == selected_date:
					if day_number is None or str(day_number) == str(confirmed_day):
						print(f"DEBUG: Found matching file: {file_path}")
						orders = file_data.get('orders', [])
						print(f"DEBUG: Returning {len(orders)} orders from consolidated file")
						return orders
					else:
						print(f"DEBUG: Date matches but day doesn't - file day: {confirmed_day}, search day: {day_number}")
				else:
					print(f"DEBUG: Date doesn't match - file date: '{confirmed_date}', search date: '{selected_date}'")
					
			except Exception as e:
				print(f"Error reading consolidated order file {file_path}: {e}")
				continue
		
		# Process confirmed order files second (fallback)
		for file_path in confirmed_files:
			try:
				print(f"DEBUG: Reading confirmed file: {file_path}")
				with open(file_path, 'r') as f:
					file_data = json.load(f)
				
				# Get confirmed date from metadata
				metadata = file_data.get('metadata', {})
				confirmed_date = metadata.get('confirmed_date', '')
				confirmed_day = metadata.get('confirmed_day', '1')
				
				print(f"DEBUG: File metadata - confirmed_date: '{confirmed_date}', confirmed_day: '{confirmed_day}'")
				
				# Check if this file matches our search criteria
				if confirmed_date == selected_date:
					if day_number is None or str(day_number) == str(confirmed_day):
						print(f"DEBUG: Found matching file: {file_path}")
						orders = file_data.get('orders', [])
						print(f"DEBUG: Returning {len(orders)} orders from confirmed file")
						return orders
					else:
						print(f"DEBUG: Date matches but day doesn't - file day: {confirmed_day}, search day: {day_number}")
				else:
					print(f"DEBUG: Date doesn't match - file date: '{confirmed_date}', search date: '{selected_date}'")
					
			except Exception as e:
				print(f"Error reading confirmed order file {file_path}: {e}")
				continue
		
		print(f"DEBUG: No matching orders found in JSON files")
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
			
			# Create location with calculated totals
			location = Location(location_name, bread_trays=total_trays, bulk_trays=0, cake_pallets=0)
			location.total_stacks = total_stacks  # Override with calculated stacks
			
			# Assign trailers based on stack count
			location.assign_trailers()
			
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
		# Clean up any existing files for this date/day combination before saving
		cleanup_old_order_files()
		
		# Convert date to filename format (MM-DD-YYYY)
		filename_date = date_str.replace("/", "-")
		filename = f"all_orders_{filename_date}_Day{day_num}.json"
		
		# Check if file already exists - if so, don't create a duplicate
		if os.path.exists(filename):
			print(f"File {filename} already exists. Skipping creation to prevent duplicates.")
			return
		
		# Load current confirmation state
		confirmation_data = load_confirmation_state()
		
		# Convert all orders to JSON-serializable format
		orders_data = []
		total_products = 0
		total_trays = 0
		total_stacks = 0
		unique_locations = set()
		unique_routes = set()
		
		for i, order in enumerate(orders):
			
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
				total_products += 1
			
			orders_data.append(order_dict)
			total_trays += order.total_trays
			total_stacks += order.total_stacks
			unique_locations.add(order.location)
			unique_routes.add(order.route_id)
		
		
		# Create comprehensive data structure
		comprehensive_data = {
			"confirmation": confirmation_data,
			"orders": orders_data,
			"metadata": {
				"total_orders": len(orders),
				"total_products": total_products,
				"total_trays": total_trays,
				"total_stacks": total_stacks,
				"unique_locations": len(unique_locations),
				"unique_routes": len(unique_routes),
				"confirmed_date": date_str,
				"confirmed_day": day_num,
				"generation_timestamp": datetime.now().isoformat(),
				"ready_for_relay": True,
				"file_type": "consolidated_orders"
			}
		}
		
		
		# Save to single JSON file
		with open(filename, 'w') as f:
			json.dump(comprehensive_data, f, indent=2)
		
		print(f"Saved {len(orders)} orders with {total_products} total products to single file: {filename}")
		print(f"Coverage: {len(unique_locations)} locations, {len(unique_routes)} routes")
		
		# Debug: Check if file was actually created
		if os.path.exists(filename):
			file_size = os.path.getsize(filename)
		
		# Debug: Count all JSON files in directory
		import glob
		all_json_files = glob.glob("*.json")
		consolidated_files = glob.glob("all_orders_*.json")
		confirmed_files = glob.glob("confirmed_orders_*.json")
		order_files = glob.glob("orders_*.json")
		state_files = glob.glob("selection_state.json")
		
		
		# Show ALL JSON files for debugging
		
	except Exception as e:
		print(f"Error saving consolidated orders: {e}")


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
				order_info_text = f"\n\nSelected Orders ({len(selected_order_data)}):\n"
				for order_data in selected_order_data:
					order = order_data['order']
					order_info_text += f"- {order['order_id']}: {order['location']} ({order['total_trays']} trays, {order['total_stacks']} stacks)\n"
				
				# Add confirmation information
				if confirmation_info and confirmation_info.get('confirmed'):
					confirmation_msg = f"\nConfirmation Data: {confirmation_info['selected_date']} Day {confirmation_info['selected_day']} (Confirmed at {confirmation_info['timestamp']})"
				else:
					confirmation_msg = "\nNote: Using legacy order data (no confirmation available)"
				
				# Add JSON file information
				json_info = f"\nOrders loaded from comprehensive JSON files with confirmation data for relay generation"
				
				return summary + order_info_text + confirmation_msg + json_info, details
				
			except Exception as e:
				return f"Error creating relay from orders: {str(e)}", ""

		refresh_orders_btn.click(refresh_relay_orders, inputs=None, outputs=[order_select])
		create_btn.click(create_relay_from_orders, inputs=[order_select], outputs=[summary_out, details_out])



if __name__ == "__main__":
	demo.launch()


