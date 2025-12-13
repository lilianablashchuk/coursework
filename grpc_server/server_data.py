# server_data.py

from datetime import datetime, timedelta

UNIFIED_TIME = "2025-12-11T20:55:00Z"
DURATION_MINUTES = 20

def add_minutes_to_time(base_time_str, minutes):
    base_date = datetime.fromisoformat(base_time_str.replace('Z', '+00:00'))
    new_date = base_date + timedelta(minutes=minutes)
    return new_date.isoformat().replace('+00:00', 'Z')

lots = [
    { 'id': 1, 'title': "Vintage Pocket Watch", 'startingPrice': 150.0,
      'description': "An exquisite vintage pocket watch in working condition.",
      'creator': "JohnDoe", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 2, 'title': "Antique Brass Telescope", 'startingPrice': 300.0,
      'description': "Brass telescope from the 19th century, perfect for collectors.",
      'creator': "AntiqueSeller", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 3, 'title': "Victorian Jewelry Box", 'startingPrice': 120.0,
      'description': "Elegant Victorian jewelry box made of oak and velvet lining.",
      'creator': "JaneSmith", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 4, 'title': "Retro Typewriter", 'startingPrice': 200.0,
      'description': "Classic retro typewriter, fully functional with original keys.",
      'creator': "TypewriterLover", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 5, 'title': "Old Map of Europe (18th Century)", 'startingPrice': 250.0,
      'description': "Rare map of Europe, 18th century, in good preserved condition.",
      'creator': "MapCollector", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 6, 'title': "Antique Porcelain Vase", 'startingPrice': 180.0,
      'description': "Beautiful porcelain vase from Qing dynasty, hand-painted.",
      'creator': "PorcelainShop", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 7, 'title': "Classic Oil Painting", 'startingPrice': 400.0,
      'description': "Oil painting by a local 19th-century artist, frame included.",
      'creator': "ArtGallery", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 8, 'title': "Antique Compass", 'startingPrice': 90.0,
      'description': "19th-century brass compass, great for collectors.",
      'creator': "NavigatorShop", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 9, 'title': "Vintage Music Box", 'startingPrice': 130.0,
      'description': "Beautiful music box with intricate carvings, still works.",
      'creator': "MusicLover", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 10, 'title': "Old Leather-bound Book", 'startingPrice': 75.0,
      'description': "Rare leather-bound book from the early 20th century.",
      'creator': "BookCollector", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 11, 'title': "Retro Pocket Knife", 'startingPrice': 60.0,
      'description': "Vintage pocket knife with wooden handle, collector's item.",
      'creator': "KnifeStore", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 12, 'title': "Antique Candle Holder", 'startingPrice': 50.0,
      'description': "Brass candle holder, 19th century, decorative piece.",
      'creator': "DecorShop", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 13, 'title': "Vintage Globe", 'startingPrice': 220.0,
      'description': "Old globe from 1950s, stands on wooden base.",
      'creator': "GlobeCollector", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 14, 'title': "Antique Wall Clock", 'startingPrice': 280.0,
      'description': "Wall clock with chimes, 19th century, fully restored.",
      'creator': "ClockMaker", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },

    { 'id': 15, 'title': "Old Silver Cutlery Set", 'startingPrice': 160.0,
      'description': "Complete silver cutlery set, Victorian era, 24 pieces.",
      'creator': "SilverStore", 'createdAt': UNIFIED_TIME,
      'startTime': UNIFIED_TIME, 'durationMinutes': DURATION_MINUTES, 'bids': [] },
]
