from math import ceil
LOCATIONS = [
  "Tucker", "Jamestown", "Knoxville", "Oxford", "Goldsboro", "Norfolk", "Lynchburg", "Villa Rica", "Hope Mills", #Sister Plant's
  "Beckley", "Bluefield", "Galax", "Gastonia", "Wilksboro", "Hickory", "Morganton", "Statesville", "Spartanburg", "Syvla", "Anderson", "Greenville", "Laurens", "Asheville", "Hendersonville"
]
def get_user_input():
  day = input("Enter relay day (1, 2, 4, 5, 6): ")
  date = input("Enter relay date (MM/DD/YYYY): ")

  for location in LOCATIONS:
    print(f"\n--- [location] ---")
    bread = int(input("Bread tray count: "))
    bulk = int(input("Bulk tray count: "))
    cross_dock = int(input("Cross-dock tray count: "))
    inbound = int(input("Inbound tray count: "))
    cake_pallets = 0
    if day in ["1", "4"]:
      cake_pallets = int(input("Cake pallet count: "))

  data[location] = {
    "bread": bread,
    "bulk": bulk,
    "cross_dock": cross_dock,
    "inbound": inbound,
    "cake_pallets": cake_pallets
  }
return day, date, data

def calculate_stacks_and_trailers(data):
  bread_stacks = ceil(counts["bread"] / 17)
  bulk_stacks = ceil(counts["bulk"] / 30)
  total_stacks = bread_stacks + bulk_stacks

trailer_distribution_stacks = total_stacks + (counts["cake_pallets"] * 4)
num_trailers = ceil(trailer_distribution_stacks / 98)
result[location] = {
  "bread_stacks": bread_stacks,
  "bulk_stacks": bulk_stacks,
  "total_stacks": total_stacks,
  "cake_stack_equiv": counts["cake_palles"] *4,
  "stacks_for_distribution": trailer_distribution_stacks,
  "num_trailers": num_trailers
  }
  return result
def print_results(day, date, result):
  print(f"\nRelay for Day {day} on {date}")
  for location, info in result.items():
    print(f"/n{location}:")
    print(f" Bread stacks: {info["bread_stacks"]}")
    print(f" Bulk stacks: {info["bulk_stacks"]}")
    print(f" Total stacks (not including cake): {info["total_stacks"]}")
    print(f" Cake stack equivalent (4 per pallet): {info["cake_stack_equiv"]}")
    print(f" Stacks for trailer distribution: {info["stacks_for_distribution"]}")
    print(f" Trailers required: {info["num_trailers"]}")
