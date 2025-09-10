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

def ensure_order_system(products_path: str | None = None, routes_path: str | None = None) -> str:
	global order_system
	# If specific files provided, (re)create using those; else create default
	if products_path and routes_path:
		# Create a fresh instance pointing to uploaded files
		order_system = OrderSystem(products_file=products_path, routes_file=routes_path)
		return f"Loaded catalog: {len(order_system.products)} products, {len(order_system.routes)} routes."
	if order_system is None:
		order_system = OrderSystem()
	return f"Catalog ready: {len(order_system.products)} products, {len(order_system.routes)} routes."


def ensure_relay_system() -> None:
	global relay_system
	if relay_system is None:
		relay_system = RelaySystem()
	# Keep relay_system's order_system in sync with global order_system
	if order_system is not None:
		relay_system.order_system = order_system


def upload_catalog(products_file, routes_file):
	"""Accept products.json and routes.json uploads and initialize the catalog."""
	if not products_file or not routes_file:
		# Use default files if no uploads provided - reinitialize with default paths
		global order_system, relay_system
		try:
			order_system = OrderSystem()  # This will use default products.json and routes.json
			relay_system = RelaySystem()
			relay_system.order_system = order_system
			dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders())) if order_system else []
			return f"System ready: {len(order_system.products)} products, {len(order_system.routes)} routes (Using default files)", dates
		except Exception as e:
			return f"Error loading default files: {str(e)}", []

	# Save to working directory to be file-backed for OrderSystem
	products_path = os.path.join(os.getcwd(), "products.json")
	routes_path = os.path.join(os.getcwd(), "routes.json")

	with open(products_path, "wb") as pf:
		pf.write(products_file.read())
	with open(routes_path, "wb") as rf:
		rf.write(routes_file.read())

	msg = ensure_order_system(products_path, routes_path)
	ensure_relay_system()
	# Build dates list
	dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders())) if order_system else []
	return f"{msg} (Using uploaded files)", dates


def simulate_orders(max_products: int):
	if max_products is None or max_products <= 0:
		max_products = len(order_system.products) if order_system else 100  # Use all products
	msg = ensure_order_system()
	ensure_relay_system()
	orders = order_system.simulate_random_orders(max_products)
	dates = sorted(set(o.order_date.split(" ")[0] for o in orders))
	return f"{msg}\nCreated {len(orders)} demo orders with up to {max_products} products per route.", dates


def upload_orders(orders_json_file):
	if orders_json_file is None:
		return "Please upload an orders_*.json file exported from the system.", []
	ensure_order_system()
	ensure_relay_system()
	path = os.path.join(os.getcwd(), "uploaded_orders.json")
	with open(path, "wb") as f:
		f.write(orders_json_file.read())
	ok = order_system.load_orders_from_file(path)
	dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders()))
	return ("Loaded orders successfully." if ok else "Failed to load orders."), dates


def get_dates():
	ensure_order_system()
	dates = sorted(set(o.order_date.split(" ")[0] for o in order_system.get_all_orders()))
	return dates


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

	# Build detailed order info
	details_lines = ["== ORDER DETAILS =="]
	for loc in relay_system.locations:
		details_lines.append(f"\n-- {loc.name} --")
		for o in loc.orders:
			details_lines.append(f"Order {o.order_id}  Route {o.route_id}  Trays={o.total_trays}  Stacks={o.total_stacks}")
			for it in o.items:
				details_lines.append(f"  - {it.product_name}: units={it.units_ordered}, trays={it.trays_needed}, stacks={it.stacks_needed}")

	return "\n".join(summary_lines), "\n".join(details_lines)


with gr.Blocks(title="Virtual Relay System") as demo:
	gr.Markdown("# Virtual Relay System — Shipping Dashboard (HF Spaces)")
	
	# Initialize systems on startup
	initial_status = initialize_systems()
	
	with gr.Tab("Catalog"):
		gr.Markdown("System is ready with default products and routes. Upload custom files if needed.")
		catalog_msg = gr.Textbox(label="Status", value=initial_status, interactive=False)
		date_dropdown_1 = gr.Dropdown(choices=[], label="Available Dates", interactive=False)
		
		# Optional file uploads
		products_file = gr.File(label="Upload custom products.json (optional)", file_types=[".json"])
		routes_file = gr.File(label="Upload custom routes.json (optional)", file_types=[".json"])
		load_btn = gr.Button("Load Custom Catalog")
		load_btn.click(upload_catalog, inputs=[products_file, routes_file], outputs=[catalog_msg, date_dropdown_1])

	with gr.Tab("Orders"):
		gr.Markdown("Simulate demo orders for all routes and locations, or upload an exported orders_*.json file.")
		max_products = gr.Slider(1, 100, value=50, step=1, label="Max products per order (demo)")
		simulate_btn = gr.Button("Simulate Orders for All Routes")
		sim_msg = gr.Textbox(label="Status", interactive=False)
		date_dropdown_2 = gr.Dropdown(choices=[], label="Available Dates", interactive=True)
		simulate_btn.click(simulate_orders, inputs=[max_products], outputs=[sim_msg, date_dropdown_2])

		orders_upload = gr.File(label="Upload orders_*.json", file_types=[".json"])
		upload_btn = gr.Button("Load Orders File")
		upload_msg = gr.Textbox(label="Status", interactive=False)
		date_dropdown_3 = gr.Dropdown(choices=[], label="Available Dates", interactive=True)
		upload_btn.click(upload_orders, inputs=[orders_upload], outputs=[upload_msg, date_dropdown_3])

	with gr.Tab("Relay"):
		gr.Markdown("Select a date, optionally enter a day number, and generate the relay.")
		refresh_dates_btn = gr.Button("Refresh Dates")
		date_select = gr.Dropdown(choices=[], label="Date", interactive=True)
		day_input = gr.Textbox(label="Day Number (optional)", placeholder="e.g., 1")
		create_btn = gr.Button("Create Relay")
		summary_out = gr.Textbox(label="Relay Summary", lines=12)
		details_out = gr.Textbox(label="Order Details", lines=16)

		refresh_dates_btn.click(get_dates, inputs=None, outputs=[date_select])
		create_btn.click(create_relay, inputs=[date_select, day_input], outputs=[summary_out, details_out])


if __name__ == "__main__":
	demo.launch()


