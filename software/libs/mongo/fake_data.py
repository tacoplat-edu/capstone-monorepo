import os
import random
import math
from datetime import datetime, timedelta
import pymongo

# --- Configuration ---
MONGO_URI = os.getenv("MONGO_URI", None)
DB_NAME = os.getenv("MONGO_DB", "plantbox")

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]

def clean_database():
    """Optional: Wipes existing data to start fresh."""
    print("🧹 Cleaning old data...")
    db.devices.delete_many({})
    db.telemetry.delete_many({})
    db.notifications.delete_many({})

def create_mock_device():
    print("🌱 Creating device: PlantBox-492 (My Basil)...")
    
    device_data = {
        "hardware_id": "PlantBox-492",
        "display_name": "My Basil",
        "owner_id": "user_123", # Mock user ID
        "light_schedule": {
            "start": "06:00:00",
            "end": "18:00:00"
        },
        "targets": {
            "air_temp": {"min": 18.0, "max": 26.0},
            "humidity": {"min": 40.0, "max": 70.0},
            "water_level": {"min": 50.0, "max": 100.0}
        },
        "camera": {
            "enabled": True,
            "stream_url": "http://placeholder-video-stream"
        },
        # Set last_seen to now so it appears "Online"
        "last_seen": datetime.utcnow(),
        "is_online": True,
        "updated_at": datetime.utcnow()
    }
    
    db.devices.update_one(
        {"hardware_id": "PlantBox-492"},
        {"$set": device_data},
        upsert=True
    )

def generate_telemetry_history():
    print("📈 Generating 24 hours of sensor history...")
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    current_time = start_time
    
    records = []
    
    while current_time <= end_time:
        # --- Simulate Realistic Data Curves ---
        
        # 1. Light: High during the day (06:00-18:00), 0 at night
        hour = current_time.hour
        if 6 <= hour < 18:
            # Peak at noon
            light_pct = 85 + random.uniform(-5, 5)
        else:
            light_pct = 0
            
        # 2. Temperature: Cooler at night, warmer in day
        # Sine wave based on hour + some noise
        base_temp = 22
        temp_fluctuation = 3 * math.sin((hour - 9) * math.pi / 12) 
        air_temp = base_temp + temp_fluctuation + random.uniform(-0.5, 0.5)
        
        # 3. Water Level: Slowly decreasing over 24 hours
        # Starts at 85%, drops by 0.2% per hour
        hours_passed = (current_time - start_time).total_seconds() / 3600
        water_level = 85.0 - (hours_passed * 0.2)
        
        # 4. Humidity: Inverse to temperature usually
        humidity = 60 - temp_fluctuation + random.uniform(-2, 2)

        record = {
            "device_id": "PlantBox-492",
            "received_at": current_time,
            "captured_at": current_time,
            "metadata": {
                "profile_active": "basil"
            },
            "sensors": {
                "air_temp_c": round(air_temp, 1),
                "humidity_pct": round(humidity, 1),
                "light_intensity_pct": round(light_pct, 1),
                "water_level_pct": round(water_level, 1),
                "nutrient_a_pct": 92.0, # Static for now
                "flow_rate_lpm": 1.0
            }
        }
        records.append(record)
        
        # Increment by 10 minutes
        current_time += timedelta(minutes=10)
        
    if records:
        db.telemetry.insert_many(records)
        print(f"✅ Inserted {len(records)} telemetry records.")

if __name__ == "__main__":
    clean_database() # Comment this out if you want to keep old data
    create_mock_device()
    generate_telemetry_history()
    print("🚀 Done! Your database is seeded.")