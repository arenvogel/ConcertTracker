from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "docs"
CACHE_DIR = ROOT / ".cache"

TZ = "America/New_York"

HORIZON_DAYS = 180

# Most venues — including the IMP clubs — are fully indexed by Ticketmaster.
# Black Cat is independent and not on Ticketmaster, so it has its own scraper.
TICKETMASTER_VENUES = [
    ("Jiffy Lube Live", "KovZpZAEk6JA"),
    ("Wolf Trap", "KovZpZAEetJA"),   # Filene Center (main amphitheater)
    ("Wolf Trap", "ZFr9jZea1F"),     # The Barns at Wolf Trap
    ("Capital One Arena", "KovZpaKuJe"),
    ("Nationals Park", "KovZpZA1J67A"),
    ("Northwest Stadium", "KovZpZAJ6kEA"),
    ("9:30 Club", "KovZpZA7knFA"),
    ("The Anthem", "KovZ917A3Y7"),
    ("Merriweather Post Pavilion", "KovZpZA1JkvA"),
    ("Lincoln Theatre", "KovZpZAFk6EA"),
    ("The Atlantis", "KovZ917AinI"),
]
