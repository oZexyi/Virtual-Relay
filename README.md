# Virtual Relay System
## Overview
The Virtual Relay System is a software solution designed to digitally simulate the paper-based relay in shipping operations at Flowers Foods. This project is part of my hands-on development for a Software Engineering degree and aims to streamline logistical decision-making using real-time inputs.
## Purpose
At Flowers, trailers are loaded with stacks of bread and bulk products based on orders received from routes. Currently, this process is manually managed with a paper relay. This project replaces that with a dynamic, live system capable of: 
- Calculating stack counts per location
- Estimating required trailers based on real-time orders
- Factoring in cake pallets (for Day 1 and Day 4)
- Tracking bread trays, bulk trays, cross-dock trays, and inbounds

## Features
- **Day and Date Selection:**
Input the operational day (1, 2, 4, 5, 6) and the relay date for reporting.

- **Order System:**
Order units for each route. The system will automatically generate a relay system to fill the orders.

- **Automated Calculations:**
  - 17 bread trays = 1 stack
  - 30 bulk trays = 1 stack
  - 1 cake pallet = 4 stacks (distribution only)
  - 98 stacks per trailer (including cake-stack equivalents)
  Short stacks are rounded up to the next full stack.

- **Real-Time Trailer Distribution Logic**
The system calculates the number of trailers required per location.

## Stack & Logic
- Written in **Python 3**
- Logic modularized into separate files for clarity ('main.py', 'relay_logic.py', etc.)
- Uses 'math.ceil()' to handle rounding of stacks values

## Future Plans
- Written in React.js JavaScript and Spring Boot Java
- Add a **live dashboard** tab to track:
  - Active trailers
  - Stack status (e.g., tagged but not scanned)
- Integrate a financials tab for deeper insights into "buying" and "selling."
- Long-term: explore interfacing with systems like PCData or S4 (SAP replacement).
- Integrate a tray debt tab to track tray allocation between sister plants.


## Author
Zackary Holston
Shipping Associate | Software Engineering Student
[LinkedIn](https://www.linkedin.com/in/zackary-holston-602404375/)
