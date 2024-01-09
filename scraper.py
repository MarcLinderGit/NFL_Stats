from functions import NFLDataScraper

# Create an instance of the NFLDataScraper class
scraper = NFLDataScraper()

# Set the season before calling get_stats
scraper.season = 2023

# Check current season and week
scraper.set_current_season_and_week()

# Call the get_stats method with the season argument
scraper.get_stats(level = "player")
scraper.get_stats(level = "team")

# Scrape current season data for both player and team levels
for level in ["player", "team"]:
    scraper.get_stats(level, season="2023")

# Get historic data for previous seasons
historic_seasons = [str(year) for year in range(1970, scraper.current_season - 1)]
for season in historic_seasons:
    for level in ["player", "team"]:
        scraper.get_stats(level, season)
