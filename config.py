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
    # Added 2026-11-08 from a DC-area (30 mi) Discovery API sweep.
    # Some venues have two Ticketmaster IDs; both are listed.
    ("The Fillmore Silver Spring", "KovZpZA6tFlA"),
    ("Echostage", "KovZpZAadt7A"),
    ("Howard Theatre", "rZ7HnEZ17aM4f"),
    ("Howard Theatre", "ZFr9jZaaeF"),
    ("Union Stage", "Z7r9jZadfE"),
    ("Union Stage", "KovZ917AQjV"),
    ("Warner Theatre", "KovZpZAJv7aA"),
    ("DAR Constitution Hall", "KovZpaKdYe"),
    ("Lisner Auditorium", "KovZpZAa1eEA"),
    ("Songbyrd Music House", "Z7r9jZadAG"),
    ("DC9", "rZ7HnEZ17OeAV"),
    ("DC9", "Z7r9jZae0p"),
    ("Pearl Street Warehouse", "Z7r9jZadJt"),
    ("Blues Alley", "Z7r9jZa7Yu"),
    ("The Birchmere", "KovZpa3rme"),
    ("Capital One Hall", "KovZ917AJ17"),
    ("The Vault at Capital One Hall", "KovZ917ARno"),
    ("The Theater at MGM National Harbor", "KovZ917A5LV"),
    ("EagleBank Arena", "KovZpZAE76EA"),
    ("Jammin Java", "Z7r9jZaetR"),
    ("State Theatre", "ZFr9jZ76A6"),
    ("Strathmore", "ZFr9jZ71Fe"),
]
