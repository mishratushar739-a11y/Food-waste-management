"""
generate_sample_data.py
------------------------
Generates 4 sample CSV files matching the schema used in the
Food Management SQL project, so you can test the Streamlit app
and MySQL load scripts immediately -- even before your real
CSVs are ready.

Run:  python generate_sample_data.py
Output: providers_data.csv, receivers_data.csv,
        food_listings_data.csv, claims_data.csv
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

CITIES = [
    "Richardfort", "Lake Jessica", "New Michael", "Port Sarah",
    "East Amanda", "West Jennifer", "South Robert", "North David",
    "Lake Christopher", "Jameschester"
]

PROVIDER_TYPES = ["Restaurant", "Grocery Store", "Supermarket", "Catering Service", "Bakery"]
RECEIVER_TYPES = ["NGO", "Shelter", "Individual", "Community Center", "Food Bank"]
FOOD_TYPES = ["Vegetarian", "Non-Vegetarian", "Vegan"]
MEAL_TYPES = ["Breakfast", "Lunch", "Dinner", "Snacks"]
CLAIM_STATUS = ["Completed", "Pending", "Cancelled"]

FOOD_NAMES = [
    "Rice", "Bread", "Pasta", "Vegetable Curry", "Chicken Curry",
    "Salad", "Soup", "Sandwiches", "Fruits Basket", "Milk Packets",
    "Dal", "Chapati", "Biryani", "Pizza Slices", "Canned Beans",
    "Cereal Boxes", "Eggs", "Paneer Tikka", "Noodles", "Cookies"
]

FIRST_NAMES = ["John", "Sarah", "Michael", "Emily", "David", "Jessica",
               "Robert", "Amanda", "James", "Christopher", "Lisa", "Mark"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
              "Miller", "Davis", "Rodriguez", "Martinez"]
ORG_SUFFIX = ["Foundation", "Relief Center", "Community Kitchen", "Outreach",
              "Food Bank", "Shelter Home", "Trust", "Mission"]


def random_name(is_org=False):
    if is_org:
        return f"{random.choice(LAST_NAMES)} {random.choice(ORG_SUFFIX)}"
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_phone():
    return f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"


def random_date(start_days_ago=0, end_days_ahead=30):
    base = datetime.now()
    delta_days = random.randint(-start_days_ago, end_days_ahead)
    return (base + timedelta(days=delta_days)).strftime("%Y-%m-%d")


def random_timestamp():
    base = datetime.now() - timedelta(days=random.randint(0, 60))
    base = base.replace(hour=random.randint(7, 21), minute=random.randint(0, 59), second=0)
    return base.strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------
# 1. Providers
# ------------------------------------------------------------
N_PROVIDERS = 40
providers = []
for pid in range(1, N_PROVIDERS + 1):
    ptype = random.choice(PROVIDER_TYPES)
    providers.append({
        "provider_id": pid,
        "name": f"{random_name(is_org=True)} {ptype}",
        "type": ptype,
        "address": f"{random.randint(1,999)} Main St",
        "city": random.choice(CITIES),
        "contact": random_phone()
    })

with open("providers_data.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(providers[0].keys()))
    writer.writeheader()
    writer.writerows(providers)

# ------------------------------------------------------------
# 2. Receivers
# ------------------------------------------------------------
N_RECEIVERS = 35
receivers = []
for rid in range(1, N_RECEIVERS + 1):
    rtype = random.choice(RECEIVER_TYPES)
    receivers.append({
        "receiver_id": rid,
        "name": random_name(is_org=(rtype != "Individual")),
        "type": rtype,
        "city": random.choice(CITIES),
        "contact": random_phone()
    })

with open("receivers_data.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(receivers[0].keys()))
    writer.writeheader()
    writer.writerows(receivers)

# ------------------------------------------------------------
# 3. Food Listings
# ------------------------------------------------------------
N_LISTINGS = 150
listings = []
for fid in range(1, N_LISTINGS + 1):
    provider = random.choice(providers)
    listings.append({
        "food_id": fid,
        "food_name": random.choice(FOOD_NAMES),
        "quantity": random.randint(5, 200),
        "expiry_date": random_date(start_days_ago=0, end_days_ahead=14),
        "provider_id": provider["provider_id"],
        "provider_type": provider["type"],
        "location": provider["city"],
        "food_type": random.choice(FOOD_TYPES),
        "meal_type": random.choice(MEAL_TYPES)
    })

with open("food_listings_data.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(listings[0].keys()))
    writer.writeheader()
    writer.writerows(listings)

# ------------------------------------------------------------
# 4. Claims
# ------------------------------------------------------------
N_CLAIMS = 220
claims = []
for cid in range(1, N_CLAIMS + 1):
    food = random.choice(listings)
    receiver = random.choice(receivers)
    claims.append({
        "claim_id": cid,
        "food_id": food["food_id"],
        "receiver_id": receiver["receiver_id"],
        "status": random.choices(CLAIM_STATUS, weights=[0.6, 0.25, 0.15])[0],
        "timestamp": random_timestamp()
    })

with open("claims_data.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(claims[0].keys()))
    writer.writeheader()
    writer.writerows(claims)

print("Sample data generated:")
print(f"  providers_data.csv      -> {len(providers)} rows")
print(f"  receivers_data.csv      -> {len(receivers)} rows")
print(f"  food_listings_data.csv  -> {len(listings)} rows")
print(f"  claims_data.csv         -> {len(claims)} rows")
