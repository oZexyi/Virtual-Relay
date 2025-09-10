import os
import json
import gradio as gr

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




def create_orders_for_date(order_date: str, max_products: int):
	"""Create orders for a specific date"""
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
	dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders()))
	return dates


def get_initial_dates():
	"""Get dates on startup, return empty list if no orders exist yet"""
	try:
		ensure_order_system()
		dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders()))
		return dates
	except:
		return []


def get_order_summary(selected_date: str):
	"""Get detailed summary of orders for a specific date"""
	if not selected_date:
		return "Select a date to view orders"
	
	ensure_order_system()
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


def create_relay(selected_date: str, day_number: str | None):
	if not selected_date:
		return "Please select a date first.", ""
	ensure_order_system()
	ensure_relay_system()

	day_num_int = None
	try:
		day_num_int = int(day_number) if day_number else None
	except Exception:
		day_num_int = None

	locations = relay_system.create_automated_relay(selected_date, day_num_int)
	if not locations:
		return f"No orders found for {selected_date}.", ""

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
				gr.Markdown("**Step 1:** Select a date for your orders")
				order_date_input = gr.Textbox(label="Order Date", placeholder="MM/DD/YYYY (e.g., 12/25/2024)", interactive=True)
				gr.Markdown("**Step 2:** Configure order parameters")
				max_products = gr.Slider(1, 235, value=235, step=1, label="Max products per order")
				simulate_btn = gr.Button("Generate Orders for Selected Date", variant="primary")
				sim_msg = gr.Textbox(label="Order Creation Status", interactive=False)
			
			with gr.Column(scale=1):
				gr.Markdown("### View Existing Orders")
				gr.Markdown("View orders that have already been created:")
				date_dropdown_2 = gr.Dropdown(choices=initial_dates, label="Select Date with Orders", interactive=True)
				order_summary = gr.Textbox(label="Order Summary", lines=8, interactive=False, value="Select a date to view existing orders")
				refresh_orders_btn = gr.Button("Refresh Order List")
		
		simulate_btn.click(create_orders_for_date, inputs=[order_date_input, max_products], outputs=[sim_msg, date_dropdown_2])
		date_dropdown_2.change(lambda date: get_order_summary(date) if date else "Select a date to view orders", inputs=[date_dropdown_2], outputs=[order_summary])
		refresh_orders_btn.click(lambda: (get_dates(), "Select a date to view orders"), outputs=[date_dropdown_2, order_summary])

	with gr.Tab("Relay"):
		gr.Markdown("## Relay Generation")
		gr.Markdown("Create relays from existing orders. Only dates with orders are available for selection.")
		refresh_dates_btn = gr.Button("Refresh Available Dates")
		date_select = gr.Dropdown(choices=initial_dates, label="Select Date with Orders", interactive=True)
		day_input = gr.Textbox(label="Day Number (optional)", placeholder="e.g., 1")
		create_btn = gr.Button("Create Relay", variant="primary")
		summary_out = gr.Textbox(label="Relay Summary", lines=12, value="Create orders first, then select a date with orders to generate relay")
		details_out = gr.Textbox(label="Trailer & Order Details", lines=16)

		refresh_dates_btn.click(get_dates, inputs=None, outputs=[date_select])
		create_btn.click(create_relay, inputs=[date_select, day_input], outputs=[summary_out, details_out])


if __name__ == "__main__":
	demo.launch()


