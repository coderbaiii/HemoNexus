"""
HEMONEXAS Distance Calculation Engine
Implements the Haversine formula for spherical great-circle distance
and travel time estimations without external paid APIs.
"""
import math

def calculate_distance_km(donor_lat, donor_lon, patient_lat, patient_lon):
    """
    Calculate the great-circle distance between two geographic coordinates
    on Earth in kilometers using the Haversine formula.
    
    Formula:
      a = sin²(Δφ/2) + cos(φ1) * cos(φ2) * sin²(Δλ/2)
      c = 2 * atan2(√a, √(1−a))
      d = R * c
    where:
      φ is latitude, λ is longitude, R is Earth's mean radius (6371.0 km).
    
    Returns:
      float: Distance in kilometers rounded to 2 decimal places, or None if coordinates are missing/invalid.
    """
    if None in (donor_lat, donor_lon, patient_lat, patient_lon):
        return None
        
    try:
        lat1 = float(donor_lat)
        lon1 = float(donor_lon)
        lat2 = float(patient_lat)
        lon2 = float(patient_lon)
    except (ValueError, TypeError):
        return None
        
    # Validate coordinate boundaries
    if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
        return None
    if not (-180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0):
        return None

    R = 6371.0  # Earth's radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
         
    # Guard against precision errors causing a > 1.0
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(R * c, 2)

def estimate_travel_time_minutes(distance_km, average_speed_kmh=30.0):
    """
    Estimates travel duration in minutes based on distance and average urban travel speed.
    
    IMPORTANT:
    This is clearly labeled as an estimated travel time for routing priority,
    not real-time GPS traffic routing.
    
    Returns:
      float: Estimated travel duration in minutes rounded to 1 decimal place.
    """
    if distance_km is None or distance_km < 0:
        return None
    if average_speed_kmh <= 0:
        average_speed_kmh = 30.0
        
    hours = distance_km / float(average_speed_kmh)
    minutes = hours * 60.0
    return round(minutes, 1)
