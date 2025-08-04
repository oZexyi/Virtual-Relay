from math import ceil
import random

# Trailer with its associated info (stack count, overload info, etc.)
class Trailer:
    def __init__(self, number, stacks, overload_from=None):
        self.number = number
        self.stacks = stacks
        self.overload_from = overload_from
        self.ld_number = random.randint(100000000, 999999999)
        self.trailer_number = ""
        self.seal_number = ""
# Shipping location and stack/tray calculations
class Location:
    def __init__(self, name, bread_trays, bulk_trays, cake_pallets):
        self.name = name
        self.bread_trays = bread_trays
        self.bulk_trays = bulk_trays
        self.cake_pallets = cake_pallets
        self.total_bread_stacks = ceil(bread_trays / 17)
        self.total_bulk_stacks = ceil(bulk_trays / 30)
        self.total_stacks = self.total_bread_stacks + self.total_bulk_stacks
        self.trailers = []
    # Assign trailers based on stack count and cake pallets
    def assign_trailers(self):
        stacks_remaining = self.total_stacks + (self.cake_pallets * 4)
        trailer_number = 1
        while stacks_remaining > 0:
            count = min(stacks_remaining, 98)
            self.trailers.append(Trailer(trailer_number, count))
            stacks_remaining -= count
            trailer_number += 1
    # Placeholder for FirstFleet tray information
    def finalize_trailers(self):
        for trailer in self.trailers:
            trailer.bread_trays = None
            trailer.bulk_trays = None
    # Display relay information
    def display_relay(self):
        for trailer in self.trailers:
            # If trailer has an overload, output overload info
            overload_text = f"- Overload [{trailer.overload_from[0]} {trailer.overload_from[1]} stacks]" if trailer overload from else ""
            # Print trailer details (LD number, stack count)
            print(f"{self.name}:\nLD {trailer.ld_number} - Trailer #{trailer.number}: {trailer.stacks} stacks {overload_text}")
            # Print empty input fields for trailer number and seal number
            print(f" Trailer #: [ {trailer.trailer_number} ] Seal #: [ {trailer.seal_number} ]")
