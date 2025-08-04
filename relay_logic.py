LOCATIONS = [
    "Tucker", "Jamestown", "Knoxville", "Oxford", "Goldsboro", "Norfolk",
    "Lynchburg", "Villa Rica", "Hope Mills", "Beckley", "Bluefield", "Galax",
    "Gastonia", "Wilksboro", "Hickory", "Morganton", "Statesville",
    "Spartanburg", "Syvla", "Anderson", "Greenville", "Laurens",
    "Asheville", "Hendersonville"
class Location:
    def __int__(self, name, bread_trays, bulk_trays, cake_pallets):
        self.name = name
        self.bread_trays = bread_trays
        self.bulk_trays = bulk_trays
        self.cake_pallets = cake_pallets
        self.total_stacks = 0
        self.trailers = []
    def calculate_total_stacks(self):
        bread_stacks = -(-self.bread_trays // 17)
        bulk_stacks = -(-self.bulk_trays // 30)
        self.total_stacks = bread_stacks + bulk_stacks
        return self.total_stacks
    def assign_trailers(self):
        total_for_distribution = self.total_stacks + (self.cake_pallets * 4)
        stacks_remaining = total_for_distribution
        trailer_number = 1
        while stacks_remaining > 0:
            stacks = min(stacks_remaining, 98)
            self.trailers.append((f"{self.name} #{trailer_number}", stacks))
            stacks_remaining -= stacks
            trailer_number += 1

