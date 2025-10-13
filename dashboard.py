"""
Dashboard System
Main dashboard for the Virtual Relay System with department management.

Features:
- Department-based navigation
- System status monitoring
- Interactive department launching
- System information display
"""

import os
import sys
from typing import Optional
from datetime import datetime

# Add the current directory to the path
sys.path.append(os.path.dirname(__file__))

# Import the relay and order systems
from relay_logic import RelaySystem
from orders import OrderSystem


# ============================================================================
# DEPARTMENT CLASSES
# ============================================================================

class Department:
    """Base class for all departments."""

    def __init__(self, name: str, description: str):
        """
        Initialize a department.
        
        Args:
            name: Department name
            description: Department description
        """
        self.name = name
        self.description = description
        self.is_available = True

    def display_info(self):
        """Display department information."""
        status = "🟢 Available" if self.is_available else "🔴 Unavailable"
        print(f"  {self.name}: {self.description} - {status}")

    def launch(self):
        """Launch the department - to be overridden by subclasses."""
        print(f"Launching {self.name} department...")
        print("This department is not yet implemented.")


class ShippingDepartment(Department):
    """Shipping department with access to relay and order systems."""

    def __init__(self):
        """Initialize the shipping department."""
        super().__init__(
            name="Shipping",
            description="Virtual Relay System & Order Management"
        )
        self.relay_system = None
        self.order_system = None

    def launch(self):
        """Launch the shipping department."""
        print(f"\n{'='*80}")
        print(f"SHIPPING DEPARTMENT - VIRTUAL RELAY SYSTEM")
        print(f"{'='*80}")

        while True:
            print("\n" + "="*60)
            print("SHIPPING DEPARTMENT MENU")
            print("="*60)
            print("1. Virtual Relay System (Automated)")
            print("2. Order Management System")
            print("3. System Status & Information")
            print("4. Return to Main Dashboard")
            print("="*60)

            choice = input("Enter your choice (1-4): ").strip()

            if choice == "1":
                self._launch_relay_system()
            elif choice == "2":
                self._launch_order_system()
            elif choice == "3":
                self._display_system_status()
            elif choice == "4":
                print("Returning to main dashboard...")
                break
            else:
                print("Invalid choice. Please select 1-4.")

    def _launch_relay_system(self):
        """Launch the virtual relay system."""
        print(f"\n{'='*60}")
        print("VIRTUAL RELAY SYSTEM")
        print("="*60)

        if not self.relay_system:
            self.relay_system = RelaySystem()

        self.relay_system.interactive_menu()

    def _launch_order_system(self):
        """Launch the order management system."""
        print(f"\n{'='*60}")
        print("ORDER MANAGEMENT SYSTEM")
        print("="*60)

        if not self.order_system:
            self.order_system = OrderSystem()

        self.order_system.main()

    def _display_system_status(self):
        """Display system status and information."""
        print(f"\n{'='*80}")
        print("SHIPPING DEPARTMENT - SYSTEM STATUS")
        print(f"{'='*80}")

        # Check if systems are initialized
        relay_status = "🟢 Initialized" if self.relay_system else "⚪ Not Initialized"
        order_status = "🟢 Initialized" if self.order_system else "⚪ Not Initialized"

        print(f"Virtual Relay System: {relay_status}")
        print(f"Order Management System: {order_status}")

        # Display available data files
        print(f"\nData Files:")
        data_dir = os.path.dirname(__file__)

        files_to_check = ['products.json', 'routes.json']
        for filename in files_to_check:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                print(f"  ✅ {filename} - Available")
            else:
                print(f"  ❌ {filename} - Missing")

        # Check for order files
        order_files = [f for f in os.listdir(data_dir) if f.startswith('orders_') and f.endswith('.json')]
        if order_files:
            print(f"\nOrder Files ({len(order_files)}):")
            for order_file in sorted(order_files)[-5:]:  # Show last 5 order files
                print(f"  📄 {order_file}")
        else:
            print(f"\nOrder Files: None found")

        print(f"\nSystem Information:")
        print(f"  Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Python Version: {sys.version.split()[0]}")
        print(f"  Working Directory: {os.getcwd()}")


class SanitationDepartment(Department):
    """Sanitation department - placeholder for future implementation."""

    def __init__(self):
        """Initialize the sanitation department."""
        super().__init__(
            name="Sanitation",
            description="Sanitation Management & Scheduling"
        )
        self.is_available = False  # Not yet implemented

    def launch(self):
        """Launch the sanitation department."""
        print(f"\n{'='*80}")
        print(f"SANITATION DEPARTMENT")
        print(f"{'='*80}")
        print("🚧 This department is currently under development.")
        print("Future features will include:")
        print("  • Sanitation scheduling")
        print("  • Equipment tracking")
        print("  • Compliance monitoring")
        print("  • Cleaning protocols")
        print("\nPlease check back in a future update!")

        input("\nPress Enter to return to main dashboard...")


class ProductionDepartment(Department):
    """Production department - placeholder for future implementation."""

    def __init__(self):
        """Initialize the production department."""
        super().__init__(
            name="Production",
            description="Production Planning & Management"
        )
        self.is_available = False  # Not yet implemented

    def launch(self):
        """Launch the production department."""
        print(f"\n{'='*80}")
        print(f"PRODUCTION DEPARTMENT")
        print(f"{'='*80}")
        print("🚧 This department is currently under development.")
        print("Future features will include:")
        print("  • Production scheduling")
        print("  • Inventory management")
        print("  • Quality control")
        print("  • Equipment monitoring")
        print("  • Batch tracking")
        print("\nPlease check back in a future update!")

        input("\nPress Enter to return to main dashboard...")


# ============================================================================
# MAIN DASHBOARD
# ============================================================================

class MainDashboard:
    """Main dashboard for the Virtual Relay System."""

    def __init__(self):
        """Initialize the main dashboard."""
        self.departments = {
            "1": ShippingDepartment(),
            "2": SanitationDepartment(),
            "3": ProductionDepartment()
        }
        self.system_name = "Virtual Relay System"
        self.version = "2.0.0"

    def display_header(self):
        """Display the main dashboard header."""
        print(f"\n{'='*80}")
        print(f"🏭 {self.system_name.upper()} - MAIN DASHBOARD")
        print(f"{'='*80}")
        print(f"Version: {self.version}")
        print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

    def display_departments(self):
        """Display all available departments."""
        print(f"\n📋 AVAILABLE DEPARTMENTS:")
        print(f"{'='*50}")

        for key, department in self.departments.items():
            print(f"{key}. ", end="")
            department.display_info()

        print(f"{'='*50}")

    def display_system_info(self):
        """Display system information."""
        print(f"\n{'='*80}")
        print(f"SYSTEM INFORMATION")
        print(f"{'='*80}")

        print(f"System Name: {self.system_name}")
        print(f"Version: {self.version}")
        print(f"Python Version: {sys.version.split()[0]}")
        print(f"Working Directory: {os.getcwd()}")

        # Check system components
        print(f"\nSystem Components:")
        relay_path = os.path.join(os.path.dirname(__file__), 'relay_logic.py')
        orders_path = os.path.join(os.path.dirname(__file__), 'orders.py')

        print(f"  Relay Logic: {'✅ Available' if os.path.exists(relay_path) else '❌ Missing'}")
        print(f"  Order System: {'✅ Available' if os.path.exists(orders_path) else '❌ Missing'}")

        # Check data files
        data_dir = os.path.dirname(__file__)
        print(f"\nData Files:")
        for filename in ['products.json', 'routes.json']:
            filepath = os.path.join(data_dir, filename)
            print(f"  {filename}: {'✅ Available' if os.path.exists(filepath) else '❌ Missing'}")

        print(f"{'='*80}")

    def run(self):
        """Run the main dashboard."""
        while True:
            self.display_header()
            self.display_departments()

            print(f"\n📊 ADDITIONAL OPTIONS:")
            print(f"{'='*30}")
            print(f"4. System Information")
            print(f"5. Exit")
            print(f"{'='*30}")

            choice = input(f"\nSelect a department or option (1-5): ").strip()

            if choice in self.departments:
                department = self.departments[choice]
                if department.is_available:
                    department.launch()
                else:
                    print(f"\n❌ {department.name} department is not yet available.")
                    input("Press Enter to continue...")

            elif choice == "4":
                self.display_system_info()
                input("\nPress Enter to return to main dashboard...")

            elif choice == "5":
                print(f"\n{'='*80}")
                print(f"👋 Thank you for using {self.system_name}!")
                print(f"Goodbye!")
                print(f"{'='*80}")
                break

            else:
                print(f"\n❌ Invalid choice. Please select 1-5.")
                input("Press Enter to continue...")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to run the dashboard."""
    try:
        dashboard = MainDashboard()
        dashboard.run()
    except KeyboardInterrupt:
        print(f"\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your system configuration and try again.")


if __name__ == "__main__":
    main()