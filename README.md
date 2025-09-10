# Virtual Relay System

A comprehensive Python OOP system for managing shipping department relay operations across multiple locations, including order management and automated demo functionality.

## Features

### Order Management System
- **Route-Based Orders**: Create orders for specific delivery routes within warehouse locations
- **Product Catalog**: 252+ products with detailed specifications (units per tray, stack height, tray type)
- **Unit Validation**: Automatic validation ensuring units are ordered in multiples of units_per_tray
- **Automatic Calculations**: Tray and stack calculations using ceiling functions for proper shipping
- **Demo Mode**: Simulate orders for all 135 routes with realistic random data

### Location Management
- **Sister Plants**: Tucker, Jamestown, Knoxville, Oxford, Goldsboro, Norfolk, Lynchburg, Villa Rica, Hope Mills
- **Warehouses**: Beckley, Bluefield, Galax, Gastonia, Wilksboro, Hickory, Morganton, Statesville, Spartanburg, Sylva, Anderson, Greenville, Laurens, Asheville, Hendersonville
- **Route System**: 135 delivery routes across 15 warehouse locations

### Relay Configuration
- **Day Selection**: Day 1, Day 2, Day 3, Day 4, Day 6
- **Date Format**: MM/DD/YYYY
- **Tray Input**: Bread trays, bulk trays, cross-dock stacks, inbound trays per location

### Stack Calculations
- **Bread Trays**: 17 trays = 1 stack (remainder counts as 1 stack)
- **Bulk Trays**: 30 trays = 1 stack (remainder counts as 1 stack)
- **Cake Pallets**: 1 cake pallet = 4 stacks (takes up 4 stack spaces)
- **Trailer Capacity**: 98 stacks per trailer (or 94 stacks + 1 cake pallet, etc.)

### Overload Management
- Transfer stacks between locations
- Automatic validation of available stacks
- Track overloads per trailer

### Trailer Management
- Automatic trailer creation based on stack requirements
- Edit stack counts per trailer
- **Live trailer information**: Set trailer numbers (license plates) and seal numbers per location
- Generate random 10-digit LD numbers upon finalization
- **Cake pallet support**: 1 cake pallet = 4 stack spaces

## Usage

### Running the System

#### Direct Access
```bash
# Command Line Interface (Relay System)
python virtual_relay_system.py

# Order Management System (Demo)
python orders.py
```

### Step-by-Step Workflow

#### Order Management System (Demo)
1. **Launch Orders System** - Start the order management demo
2. **View Available Routes** - See all 135 routes across 15 locations
3. **View Products** - Browse 252+ products with specifications
4. **Simulate Orders** - Generate orders for ALL routes automatically
5. **View Results** - See comprehensive order summaries and statistics
6. **Save Orders** - Export order data for relay system integration

#### Relay System Workflow
1. **Set Relay Date** - Choose day (Day 1-4, Day 6) and enter date in MM/DD/YYYY format
2. **Input Location Data** - Select location from list and enter tray/stack counts:
   - Bread trays
   - Bulk trays
   - Cross-dock stacks
   - Inbound trays
   - Cake pallets
3. **Create Trailers** - System automatically calculates required trailers
4. **Add Overloads** (Optional) - Select target trailer, choose source location, enter stack count
5. **Edit Trailer Stacks** (Optional) - Modify stack counts per trailer (max 98)
6. **Finalize Trailers** - Locks all trailer configurations and assigns LD numbers
7. **Set Trailer Information** - Enter trailer numbers (license plates) and seal numbers
8. **Set Trailer Info by Location (Live)** - Update trailer info for all trailers at a specific location
9. **Print Virtual Relay** - Generate comprehensive report

### Data Persistence
- **Save to File**: Export relay data to JSON
- **Load from File**: Import previously saved relay data

## System Architecture

### Core Classes

#### `OrderSystem`
Order management system that handles:
- Route and product management
- Order creation and validation
- Automatic tray/stack calculations
- Demo order simulation
- Data persistence

#### `VirtualRelaySystem`
Main system class that manages all operations:
- Location management
- Trailer creation and management
- Overload tracking
- Data persistence

#### `Product`
Represents a product with:
- Name and product number
- Stack height and tray type
- Units per tray
- Origin plant information

#### `Route`
Represents a delivery route with:
- Route ID (delivery route number)
- Associated warehouse location
- Available products (all products available for every route)

#### `Order`
Represents a complete order with:
- Order ID and route information
- Location and order date
- List of order items
- Total trays and stacks

#### `OrderItem`
Represents individual items in an order with:
- Product information
- Units ordered (validated as multiples of units_per_tray)
- Calculated trays and stacks needed

#### `Location`
Represents a shipping location with:
- Name and type (Sister Plant/Warehouse)
- Tray and stack counts
- Calculated total stacks

#### `Trailer`
Represents a shipping trailer with:
- Trailer ID and location
- Stack count and capacity
- LD number, trailer number, seal number
- Overload information

#### `Overload`
Tracks overload operations:
- Source and destination locations
- Stack count
- Associated trailer

### Key Methods

#### Order System Methods
- `load_data()`: Load products and routes from JSON files
- `get_available_routes()`: Get all available delivery routes
- `get_products_for_route()`: Get products available for a specific route
- `calculate_order_quantities()`: Calculate trays and stacks from units
- `create_order()`: Create a new order with validation
- `simulate_random_orders()`: Generate demo orders for all routes
- `print_system_stats()`: Display comprehensive system statistics

#### Relay System Methods
- `set_relay_date()`: Configure day and date
- `input_location_data()`: Enter tray/stack counts
- `create_trailers()`: Generate trailers based on requirements
- `add_overload()`: Transfer stacks between locations
- `edit_trailer_stacks()`: Modify trailer capacity
- `finalize_trailers()`: Lock configuration and assign LD numbers
- `print_virtual_relay()`: Generate comprehensive report

## Business Rules

### Order Management Rules
1. **Unit Validation**: Units must be ordered in multiples of units_per_tray for each product
2. **Tray Calculations**: `ceil(units / units_per_tray)` for tray requirements
3. **Stack Calculations**: `ceil(trays / stack_height)` for stack requirements
4. **Route Assignment**: All products are available for every route
5. **Order Structure**: Each order is tied to a specific route and location

### Relay System Rules
1. **Stack Calculations**:
   - Bread: 17 trays = 1 stack (remainder = 1 stack)
   - Bulk: 30 trays = 1 stack (remainder = 1 stack)
   - Cake Pallets: 1 cake pallet = 4 stack spaces

2. **Trailer Capacity**: Maximum 98 stacks per trailer (or equivalent with cake pallets)

3. **Overload Validation**: Cannot overload more stacks than available at the source

4. **Finalization**: Must finalize before printing the relay report

5. **LD Numbers**: Random 10-digit numbers assigned upon finalization

6. **Live Updates**: Trailer information can be updated at any time per location

## File Structure

```
VirtualRelaySystem/
├── virtual_relay_system.py    # Main relay system file (CLI)
├── orders.py                  # Order management system (Demo)
├── demo.py                    # Demo script
├── install.bat                # Windows setup script
├── requirements.txt           # Dependencies
├── README.md                  # This documentation
├── products.json              # Product catalog (252+ products)
├── routes.json                # Route definitions (135 routes)
└── *.json                     # Saved relay/order data files
```

## Example Usage

### Order Management System
```python
# Create order system instance
order_system = OrderSystem()

# Simulate orders for all routes
orders = order_system.simulate_random_orders(max_products_per_order=3)

# View system statistics
order_system.print_system_stats()

# Save orders for the relay system
order_system.save_orders_to_file("demo_orders.json")
```

### Relay System
```python
# Create system instance
system = VirtualRelaySystem()

# Set relay date
system.set_relay_date(DayType.DAY_1, "12/15/2024")

# Input location data
system.input_location_data("Tucker", 100, 150, 10, 5, 2)  # Added cake pallets

# Create trailers
system.create_trailers()

# Add overload
system.add_overload("Tucker", "Beckley", 20, "Beckley_Trailer_1")

# Finalize and print
system.finalize_trailers()
system.print_virtual_relay()
```

## Requirements

- Python 3.7+
- Standard library modules: `random`, `json`, `datetime`, `typing`, `dataclasses`, `enum`, `math`

## Error Handling

The system includes comprehensive error handling for:
- Invalid date formats
- Non-existent locations/routes
- Insufficient stacks for overloads
- Invalid trailer selections
- Stack count validation
- Unit validation (must be multiples of units_per_tray)
- Product availability checking
- Route existence validation

## Data Validation

### Order System Validation
- Unit validation (must be multiples of units_per_tray)
- Product existence checking
- Route availability validation
- Order structure validation

### Relay System Validation
- Date format validation (MM/DD/YYYY)
- Stack count limits (max 98 per trailer)
- Overload availability checking
- Location existence validation 


## Author
Zackary Holston
Shipping Associate | Software Engineering Student
[LinkedIn](https://www.linkedin.com/in/zackary-holston-602404375/)

