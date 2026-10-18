"""Seed multi-city restaurant records into data/processed/restaurants.parquet.

Expands coverage beyond Bangalore to include:
- Mumbai
- New Delhi
- Hyderabad
- Chennai
- Pune
- Kolkata
"""

import os
import pandas as pd
import numpy as np

PROCESSED_PATH = "data/processed/restaurants.parquet"

# Curated venues across Indian metropolitan hubs
MULTI_CITY_RESTAURANTS = [
    # ── Mumbai ──────────────────────────────────────────────────────────
    {
        "name": "The Bombay Canteen",
        "city": "mumbai",
        "location": "lower parel",
        "cuisines": "Modern Indian, Regional Indian, Cocktails",
        "rating": 4.7,
        "votes": 2850,
        "cost": 2200.0,
        "rest_type": "Casual Dining, Bar",
        "dish_liked": "Eggs Kejriwal, Canto Mutton, Cocktails, Gulab Nut",
    },
    {
        "name": "Bastian Bandra",
        "city": "mumbai",
        "location": "bandra west",
        "cuisines": "Seafood, Continental, Asian, Desserts",
        "rating": 4.6,
        "votes": 1940,
        "cost": 3000.0,
        "rest_type": "Fine Dining, Lounge",
        "dish_liked": "Lobster Roll, Butter Garlic Crab, Pull-me-up Cake",
    },
    {
        "name": "Trishna",
        "city": "mumbai",
        "location": "fort",
        "cuisines": "Seafood, Mangalorean, North Indian",
        "rating": 4.8,
        "votes": 3120,
        "cost": 2500.0,
        "rest_type": "Casual Dining",
        "dish_liked": "Butter Garlic Crab, Koliwada Prawns, Neer Dosa",
    },
    {
        "name": "Britannia & Co. Restaurant",
        "city": "mumbai",
        "location": "fort",
        "cuisines": "Parsi, Iranian",
        "rating": 4.5,
        "votes": 2400,
        "cost": 900.0,
        "rest_type": "Heritage Cafe",
        "dish_liked": "Berry Pulao, Sali Boti, Caramel Custard, Dhansak",
    },
    {
        "name": "Pizza By The Bay",
        "city": "mumbai",
        "location": "marine drive",
        "cuisines": "Italian, Pizza, Desserts",
        "rating": 4.4,
        "votes": 1780,
        "cost": 1800.0,
        "rest_type": "Casual Dining, Pizzeria",
        "dish_liked": "Bombay Herb Pizza, Garlic Bread, Tiramisu",
    },
    {
        "name": "Prithvi Cafe",
        "city": "mumbai",
        "location": "juhu",
        "cuisines": "Cafe, Fast Food, Beverages, Desserts",
        "rating": 4.6,
        "votes": 3900,
        "cost": 500.0,
        "rest_type": "Open Air Cafe",
        "dish_liked": "Irish Shake, Parathas, Sulemani Chai, Waffles",
    },
    {
        "name": "Gajalee",
        "city": "mumbai",
        "location": "vile parle",
        "cuisines": "Seafood, Maharashtrian, Malvani",
        "rating": 4.5,
        "votes": 1650,
        "cost": 1600.0,
        "rest_type": "Casual Dining",
        "dish_liked": "Tandoori Crab, Bombay Duck Fry, Sol Kadhi",
    },
    {
        "name": "Subko Coffee Roasters",
        "city": "mumbai",
        "location": "bandra west",
        "cuisines": "Cafe, Bakery, Coffee, Artisanal Breads",
        "rating": 4.7,
        "votes": 1420,
        "cost": 750.0,
        "rest_type": "Artisanal Cafe",
        "dish_liked": "Flat White, Almond Croissant, Podi Toast",
    },
    {
        "name": "O Pedro",
        "city": "mumbai",
        "location": "bkc",
        "cuisines": "Goan, Portuguese, Seafood, Cocktails",
        "rating": 4.6,
        "votes": 1560,
        "cost": 2400.0,
        "rest_type": "Bar & Kitchen",
        "dish_liked": "Poee, Choriz Chilli Fry, Seafood Rice, Pasteis de Nata",
    },
    {
        "name": "Sardar Pav Bhaji",
        "city": "mumbai",
        "location": "tardeo",
        "cuisines": "Street Food, Fast Food",
        "rating": 4.2,
        "votes": 4200,
        "cost": 350.0,
        "rest_type": "Street Food Outlet",
        "dish_liked": "Butter Pav Bhaji, Cheese Pav Bhaji",
    },

    # ── New Delhi ───────────────────────────────────────────────────────
    {
        "name": "Indian Accent",
        "city": "new delhi",
        "location": "lodhi road",
        "cuisines": "Modern Indian, Fine Dining",
        "rating": 4.9,
        "votes": 3400,
        "cost": 5000.0,
        "rest_type": "Fine Dining",
        "dish_liked": "Duck Khurchan, Blue Cheese Naan, Meetha Achaar Ribs",
    },
    {
        "name": "Bukhara - ITC Maurya",
        "city": "new delhi",
        "location": "chanakyapuri",
        "cuisines": "North Indian, Mughlai, Kebabs",
        "rating": 4.8,
        "votes": 3800,
        "cost": 6500.0,
        "rest_type": "Luxury Dining",
        "dish_liked": "Dal Bukhara, Sikandari Raan, Murgh Malai Kabab, Naan Bukhara",
    },
    {
        "name": "Karim's",
        "city": "new delhi",
        "location": "chandni chowk",
        "cuisines": "Mughlai, North Indian, Kebabs, Biryani",
        "rating": 4.4,
        "votes": 4900,
        "cost": 800.0,
        "rest_type": "Heritage Restaurant",
        "dish_liked": "Mutton Burra, Nihari, Kheer, Sheermal, Mutton Korma",
    },
    {
        "name": "Saravana Bhavan",
        "city": "new delhi",
        "location": "connaught place",
        "cuisines": "South Indian, Pure Veg",
        "rating": 4.5,
        "votes": 3200,
        "cost": 500.0,
        "rest_type": "Casual Dining",
        "dish_liked": "Ghee Roast Dosa, Filter Coffee, Thali, Mini Idli",
    },
    {
        "name": "Town Hall",
        "city": "new delhi",
        "location": "khan market",
        "cuisines": "Asian, Japanese, Sushi, Continental",
        "rating": 4.6,
        "votes": 1850,
        "cost": 2500.0,
        "rest_type": "Fine Dining, Bar",
        "dish_liked": "Dragon Roll, Dim Sum, Cocktails, Pork Belly",
    },
    {
        "name": "Diggin",
        "city": "new delhi",
        "location": "anand lok",
        "cuisines": "Italian, Cafe, Pizza, Continental",
        "rating": 4.4,
        "votes": 2600,
        "cost": 1400.0,
        "rest_type": "Garden Cafe",
        "dish_liked": "Zucchini Fries, Ravioli, Ferrero Rocher Shake, Pizza",
    },
    {
        "name": "Gulati Restaurant",
        "city": "new delhi",
        "location": "pandara road",
        "cuisines": "North Indian, Mughlai, Biryani",
        "rating": 4.7,
        "votes": 3600,
        "cost": 1700.0,
        "rest_type": "Casual Dining",
        "dish_liked": "Butter Chicken, Dal Makhani, Kakori Kebab, Garlic Naan",
    },
    {
        "name": "Social",
        "city": "new delhi",
        "location": "hauz khas",
        "cuisines": "Continental, North Indian, Fast Food, Cocktails",
        "rating": 4.3,
        "votes": 2900,
        "cost": 1600.0,
        "rest_type": "Lounge, Bar",
        "dish_liked": "LIIT, Momos, Butter Chicken Biryani, Death Wings",
    },
    {
        "name": "Cyber Hub Social",
        "city": "new delhi",
        "location": "gurgaon cyber hub",
        "cuisines": "North Indian, Asian, Bar Food, Cocktails",
        "rating": 4.4,
        "votes": 2200,
        "cost": 1600.0,
        "rest_type": "Bar & Casual Dining",
        "dish_liked": "Chilli Chicken, Cocktails, Poutine, Biryani",
    },

    # ── Hyderabad ───────────────────────────────────────────────────────
    {
        "name": "Paradise Biryani",
        "city": "hyderabad",
        "location": "secunderabad",
        "cuisines": "Biryani, Hyderabadi, Mughlai, North Indian",
        "rating": 4.3,
        "votes": 6100,
        "cost": 900.0,
        "rest_type": "Casual Dining",
        "dish_liked": "Mutton Biryani, Double Ka Meetha, Chicken 65",
    },
    {
        "name": "Bawarchi",
        "city": "hyderabad",
        "location": "rtc x roads",
        "cuisines": "Biryani, Hyderabadi, North Indian",
        "rating": 4.5,
        "votes": 7500,
        "cost": 700.0,
        "rest_type": "Casual Dining",
        "dish_liked": "Special Chicken Biryani, Mutton Dum Biryani, Boti Kebab",
    },
    {
        "name": "Flechazo",
        "city": "hyderabad",
        "location": "madhapur",
        "cuisines": "Mediterranean, Asian, North Indian, Buffet",
        "rating": 4.6,
        "votes": 2700,
        "cost": 1500.0,
        "rest_type": "Buffet, Casual Dining",
        "dish_liked": "Liquid Nitrogen Ice Cream, Shawarma, Dim Sum, Thin Crust Pizza",
    },
    {
        "name": "Farzi Cafe",
        "city": "hyderabad",
        "location": "jubilee hills",
        "cuisines": "Modern Indian, Continental, Cocktails",
        "rating": 4.5,
        "votes": 2100,
        "cost": 2000.0,
        "rest_type": "Modern Bistro",
        "dish_liked": "Dal Chawal Arancini, Cocktails, Paratha Tacos",
    },
    {
        "name": "Chutneys",
        "city": "hyderabad",
        "location": "banjara hills",
        "cuisines": "South Indian, Andhra, Pure Veg",
        "rating": 4.4,
        "votes": 3400,
        "cost": 650.0,
        "rest_type": "Vegetarian Dining",
        "dish_liked": "Babai Hotel Idli, Guntur Idli, MLA Pesarattu, Six Chutneys",
    },
    {
        "name": "Olive Bistro & Bar",
        "city": "hyderabad",
        "location": "jubilee hills",
        "cuisines": "Mediterranean, European, Italian, Pizza",
        "rating": 4.6,
        "votes": 1950,
        "cost": 2500.0,
        "rest_type": "Lakeside Bistro",
        "dish_liked": "Woodfired Pizza, Sangria, Tiramisu, Risotto",
    },
    {
        "name": "Rayalaseema Ruchulu",
        "city": "hyderabad",
        "location": "hitec city",
        "cuisines": "Andhra, Rayalaseema, South Indian, Biryani",
        "rating": 4.3,
        "votes": 1820,
        "cost": 900.0,
        "rest_type": "Casual Dining",
        "dish_liked": "Ragi Sankati, Natu Kodi Pulusu, Gongura Mutton",
    },

    # ── Chennai ─────────────────────────────────────────────────────────
    {
        "name": "Murugan Idli Shop",
        "city": "chennai",
        "location": "t. nagar",
        "cuisines": "South Indian, Street Food, Pure Veg",
        "rating": 4.6,
        "votes": 4800,
        "cost": 300.0,
        "rest_type": "Heritage Eatery",
        "dish_liked": "Podi Idli, Onion Uthappam, Jigarthanda, Ghee Dosa",
    },
    {
        "name": "Annalakshmi Restaurant",
        "city": "chennai",
        "location": "egmore",
        "cuisines": "South Indian, North Indian, Pure Veg, Thali",
        "rating": 4.7,
        "votes": 1600,
        "cost": 1200.0,
        "rest_type": "Cultural Dining",
        "dish_liked": "Traditional Thali, Elaneer Payasam, Curd Vadai",
    },
    {
        "name": "Dakshin - Crowne Plaza",
        "city": "chennai",
        "location": "alwarpet",
        "cuisines": "South Indian, Chettinad, Kerala, Andhra, Seafood",
        "rating": 4.8,
        "votes": 1400,
        "cost": 3500.0,
        "rest_type": "Luxury Dining",
        "dish_liked": "Appam with Stew, Meen Kozhambu, Iyer Thali, Filter Coffee",
    },
    {
        "name": "Amethyst Cafe",
        "city": "chennai",
        "location": "royapettah",
        "cuisines": "Cafe, Continental, Italian, Desserts",
        "rating": 4.5,
        "votes": 2200,
        "cost": 1200.0,
        "rest_type": "Garden Courtyard Cafe",
        "dish_liked": "Quiche, Wild Mushroom Pasta, Fresh Juices, Cheesecakes",
    },
    {
        "name": "Dindigul Thalappakatti",
        "city": "chennai",
        "location": "nungambakkam",
        "cuisines": "Biryani, South Indian, Chettinad",
        "rating": 4.3,
        "votes": 3100,
        "cost": 800.0,
        "rest_type": "Casual Dining",
        "dish_liked": "Thalappakatti Mutton Biryani, Black Pepper Chicken, Kola Urundai",
    },
    {
        "name": "The Marina",
        "city": "chennai",
        "location": "nungambakkam",
        "cuisines": "Seafood, Chettinad, Continental",
        "rating": 4.6,
        "votes": 1750,
        "cost": 2000.0,
        "rest_type": "Seafood Specialty",
        "dish_liked": "Tawa Fried Fish, Crab Roast, Prawn Ghee Roast, Squid Fry",
    },

    # ── Pune ────────────────────────────────────────────────────────────
    {
        "name": "German Bakery",
        "city": "pune",
        "location": "koregaon park",
        "cuisines": "Cafe, Bakery, Italian, Continental, Desserts",
        "rating": 4.4,
        "votes": 3600,
        "cost": 900.0,
        "rest_type": "Iconic Cafe",
        "dish_liked": "Apple Crumble, Kheema Pav, Mango Cheesecake, Cold Coffee",
    },
    {
        "name": "Vaishali",
        "city": "pune",
        "location": "fc road",
        "cuisines": "South Indian, Fast Food, Street Food, Pure Veg",
        "rating": 4.6,
        "votes": 5200,
        "cost": 450.0,
        "rest_type": "Heritage Eatery",
        "dish_liked": "Mysore Cheese Dosa, Sev Potato Dahi Puri, Filter Coffee",
    },
    {
        "name": "Malaka Spice",
        "city": "pune",
        "location": "koregaon park",
        "cuisines": "Southeast Asian, Thai, Vietnamese, Malaysian",
        "rating": 4.7,
        "votes": 2900,
        "cost": 2200.0,
        "rest_type": "Casual Dining, Art Cafe",
        "dish_liked": "Top Hats, Murtabak, Tom Yum Soup, Kari Kapitan",
    },
    {
        "name": "George Restaurant",
        "city": "pune",
        "location": "camp",
        "cuisines": "Biryani, Mughlai, North Indian, Parsi",
        "rating": 4.3,
        "votes": 2800,
        "cost": 900.0,
        "rest_type": "Heritage Dining",
        "dish_liked": "Mutton Biryani, Caramel Custard, Chicken Tikka",
    },
    {
        "name": "Effingut Brewerkz",
        "city": "pune",
        "location": "baner",
        "cuisines": "Finger Food, Continental, North Indian, Craft Beer",
        "rating": 4.6,
        "votes": 2100,
        "cost": 2000.0,
        "rest_type": "Microbrewery, Pub",
        "dish_liked": "Craft Beers, Apple Cider, Nachos, Chicken Wings",
    },

    # ── Kolkata ─────────────────────────────────────────────────────────
    {
        "name": "Peter Cat",
        "city": "kolkata",
        "location": "park street",
        "cuisines": "Continental, North Indian, Mughlai, Sizzlers",
        "rating": 4.8,
        "votes": 6800,
        "cost": 1500.0,
        "rest_type": "Heritage Dining",
        "dish_liked": "Chello Kebab, Mixed Sizzler, Irish Coffee, Roast Mutton",
    },
    {
        "name": "Flurys",
        "city": "kolkata",
        "location": "park street",
        "cuisines": "Bakery, Desserts, Cafe, European",
        "rating": 4.5,
        "votes": 4200,
        "cost": 850.0,
        "rest_type": "Historic Tea Room",
        "dish_liked": "English Breakfast, Rum Ball, Baba Cake, Darjeeling Tea",
    },
    {
        "name": "Arsalan",
        "city": "kolkata",
        "location": "park circus",
        "cuisines": "Kolkata Biryani, Mughlai, North Indian, Kebabs",
        "rating": 4.6,
        "votes": 5900,
        "cost": 900.0,
        "rest_type": "Casual Dining",
        "dish_liked": "Special Mutton Biryani, Arsalan Special Kebab, Firni, Chaap",
    },
    {
        "name": "6 Ballygunge Place",
        "city": "kolkata",
        "location": "ballygunge",
        "cuisines": "Bengali, Traditional Seafood",
        "rating": 4.7,
        "votes": 3100,
        "cost": 1400.0,
        "rest_type": "Heritage Bengali Dining",
        "dish_liked": "Daab Chingri, Kosha Mangsho, Luchi, Bhetki Paturi, Mishti Doi",
    },
    {
        "name": "Kewpie's",
        "city": "kolkata",
        "location": "elgin road",
        "cuisines": "Bengali, Home-style Dining",
        "rating": 4.4,
        "votes": 1200,
        "cost": 1100.0,
        "rest_type": "Family Dining",
        "dish_liked": "Mahabhoj Thali, Chitol Macher Muitha, Ilish Bhapa",
    },
]


def seed():
    if not os.path.exists(PROCESSED_PATH):
        raise FileNotFoundError(f"{PROCESSED_PATH} not found.")

    existing_df = pd.read_parquet(PROCESSED_PATH)
    print(f"Loaded existing dataset: {len(existing_df)} rows. Cities: {existing_df['city'].unique().tolist()}")

    new_rows = []
    for r in MULTI_CITY_RESTAURANTS:
        cost = float(r["cost"])
        budget_tier = "Low" if cost < 600 else ("Medium" if cost <= 1800 else "High")
        cuisines_list = [c.strip().lower() for c in r["cuisines"].split(",") if c.strip()]
        pop_score = float(r["rating"] * np.log1p(r["votes"]))

        new_rows.append({
            "url": f"https://www.zomato.com/{r['city']}/{r['name'].lower().replace(' ', '-')}",
            "address": f"{r['location'].title()}, {r['city'].title()}",
            "name": r["name"],
            "online_order": "Yes",
            "book_table": "Yes" if r["cost"] > 1500 else "No",
            "rating_raw": f"{r['rating']}/5",
            "votes": int(r["votes"]),
            "phone": "+91 98765 43210",
            "location": r["location"].lower(),
            "rest_type": r.get("rest_type", "Casual Dining"),
            "dish_liked": r.get("dish_liked", "Signature Chef Specials"),
            "cuisines": r["cuisines"],
            "cost_raw": str(int(r["cost"])),
            "reviews_list": f"[('Rated 5.0', 'Exceptional food and hospitality in {r['location'].title()}, {r['city'].title()}!')]",
            "menu_item": "[]",
            "listed_in(type)": "Dine-out",
            "neighborhood": r["location"].lower(),
            "city": r["city"].lower(),
            "rating": float(r["rating"]),
            "cost": cost,
            "budget_tier": budget_tier,
            "cuisines_list": cuisines_list,
            "popularity_score": pop_score,
        })

    seed_df = pd.DataFrame(new_rows)

    # Remove any existing duplicates if re-run
    combined_df = pd.concat([existing_df, seed_df], ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=["name", "city", "location"])

    # Normalise cuisines_list ensuring clean python lists
    combined_df["cuisines_list"] = combined_df["cuisines_list"].apply(
        lambda x: [str(c).strip().lower() for c in x] if hasattr(x, "__iter__") and not isinstance(x, str) else []
    )

    combined_df.to_parquet(PROCESSED_PATH, index=False)
    print(f"\nSuccessfully seeded! Total rows: {len(combined_df)}")
    print(f"Distinct cities now: {sorted(combined_df['city'].unique().tolist())}")


if __name__ == "__main__":
    seed()
