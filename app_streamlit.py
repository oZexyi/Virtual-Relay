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
    """Clean up old order files to prevent duplicates"""
    try:
        import glob
        import os
        
        # Get all order files
        order_files = glob.glob("orders_*.json")
        
        # Delete all existing order files
        for file in order_files:
            try:
                os.remove(file)
                print(f"Deleted old order file: {file}")
            except Exception as e:
                print(f"Error deleting {file}: {e}")
        
        print(f"Cleaned up {len(order_files)} old order files")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Initialize systems
initialize_systems()

# Streamlit app
st.set_page_config(page_title="Virtual Relay System", layout="wide")

st.title("🚛 Virtual Relay System")
st.markdown("---")

# Sidebar for system status
with st.sidebar:
    st.header("System Status")
    if order_system and relay_system:
        st.success("✅ Systems Initialized")
        st.write(f"Products: {len(order_system.products)}")
        st.write(f"Routes: {len(order_system.routes)}")
    else:
        st.error("❌ Systems Not Initialized")

# Main content
tab1, tab2 = st.tabs(["📋 Orders", "🚛 Relay"])

with tab1:
    st.header("Order Management")
    
    # Date and day selection
    col1, col2 = st.columns(2)
    
    with col1:
        selected_date = st.date_input("Select Date", value=datetime.now().date())
    
    with col2:
        day_number = st.selectbox("Select Day", options=list(range(1, 8)), index=0)
    
    # Create orders button
    if st.button("Create Orders", type="primary"):
        with st.spinner("Creating orders..."):
            try:
                # Create orders
                orders = order_system.simulate_random_orders(
                    date=selected_date.strftime("%m/%d/%Y"),
                    day_number=day_number
                )
                
                # Save orders
                filename = f"orders_{selected_date.strftime('%m-%d-%Y')}_Day{day_number}.json"
                order_system.save_orders_to_file(orders, filename)
                
                st.success(f"✅ Created {len(orders)} orders and saved to {filename}")
                
            except Exception as e:
                st.error(f"❌ Error creating orders: {str(e)}")

with tab2:
    st.header("Relay System")
    
    # Get available orders
    try:
        import glob
        order_files = glob.glob("orders_*.json")
        
        if order_files:
            # Show available order files
            selected_file = st.selectbox("Select Order File", options=order_files)
            
            if st.button("Create Relay", type="primary"):
                with st.spinner("Creating relay..."):
                    try:
                        # Load orders
                        with open(selected_file, 'r') as f:
                            data = json.load(f)
                        
                        orders = [Order.from_dict(order_data) for order_data in data['orders']]
                        
                        # Create relay
                        relay_system.create_relay_from_orders(orders)
                        
                        # Display relay
                        st.success("✅ Relay created successfully!")
                        
                        # Show locations
                        for location in relay_system.locations:
                            with st.expander(f"📍 {location.name} - {len(location.trailers)} trailers"):
                                for i, trailer in enumerate(location.trailers):
                                    col1, col2, col3 = st.columns([2, 1, 1])
                                    
                                    with col1:
                                        st.write(f"Trailer #{i+1}: {trailer.stacks} stacks")
                                    
                                    with col2:
                                        if st.button(f"Edit", key=f"edit_{location.name}_{i}"):
                                            st.session_state[f"editing_{location.name}_{i}"] = True
                                    
                                    with col3:
                                        if st.button(f"Dispatch", key=f"dispatch_{location.name}_{i}"):
                                            trailer.dispatched = True
                                            trailer.dispatch_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            st.success(f"✅ Trailer #{i+1} dispatched!")
                                    
                                    # Edit form
                                    if st.session_state.get(f"editing_{location.name}_{i}", False):
                                        with st.form(f"form_{location.name}_{i}"):
                                            trailer_num = st.text_input("Trailer Number", value=trailer.trailer_number or "")
                                            seal_num = st.text_input("Seal Number", value=trailer.seal_number or "")
                                            
                                            if st.form_submit_button("Save"):
                                                trailer.trailer_number = trailer_num
                                                trailer.seal_number = seal_num
                                                st.session_state[f"editing_{location.name}_{i}"] = False
                                                st.success("✅ Trailer updated!")
                                                st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error creating relay: {str(e)}")
        else:
            st.warning("⚠️ No order files found. Create orders first.")
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("Virtual Relay System v2.0.0")

