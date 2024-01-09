import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import datetime

class ValidSeasonError(Exception):
    def __init__(self, season):
        self.season = season

    def __str__(self):
        return 'The ' + str(self.season) + ' Season is not within the database ranging from 1970 to the current season. '

class NFLDataScraper:
    def __init__(self):
        self.base_url = "https://www.nfl.com"
        self.current_season = None
        self.current_week = None
        self.current_date = datetime.date.today()
        self.adjusted_start_date = datetime.date(self.current_date.year - 1, 9, 7) if 1 <= self.current_date.month <= 5 else datetime.date(self.current_date.year, 9, 7)
        self.unit_links = {
            "player": {},
            "team": {}
        }
        self.season = None
        print(f"|---| Current Date: {self.current_date}, Adjusted Start Date: {self.adjusted_start_date} |---|")


    def set_current_season_and_week(self):
        if self.current_date > self.adjusted_start_date:
            self.current_season = self.current_date.year - 1
        else:
            self.current_season = int(self.current_date.year)
        self.days_since_season_start = (self.current_date - self.adjusted_start_date).days
        self.current_week = (self.days_since_season_start // 7) + 1
        print(f"Current Season: {self.current_season}, Current Week: {self.current_week}")


    def get_links(self, level):
        if level == "player":
            # Request the raw HTML for player statistics page
            html = requests.get("https://www.nfl.com/stats/player-stats/")
            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(html.content, 'html.parser')
            # Find all list items with class 'd3-o-tabs__list-item'
            li_elements = soup.find_all('li', class_='d3-o-tabs__list-item')
        elif level == "team":
            # Request the raw HTML for team statistics page
            html = requests.get("https://www.nfl.com/stats/team-stats/")
            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(html.content, 'html.parser')
            # Find the unordered list element with class 'd3-o-tabbed-controls-selector__list'
            ul_element = soup.find('ul', class_='d3-o-tabbed-controls-selector__list')
            # Find all list items within the unordered list
            li_elements = ul_element.find_all('li')

        # Initialize a list to store the href values
        href_values = []

        # Iterate through the list items and extract href values from anchor tags
        for li in li_elements:
            a_tag = li.find('a')
            if a_tag:
                href = a_tag['href']
                href_values.append(href)

        # List to store the links
        links = []

        # Loop through href_values and fetch links for each URL
        for href in href_values:
            url = self.base_url + href
            html = requests.get(url)
            soup = BeautifulSoup(html.content, "html.parser")
            # Find all list items with class 'd3-o-tabs__list-item'
            a_elements = soup.find_all('li', class_='d3-o-tabs__list-item')
            # Extract and store links from anchor tags
            links += [self.base_url + element.find('a')['href'] for element in a_elements]

        # Replace "2023" with the value of the season variable we want to scrape
        links = [link.replace('2023', str(self.season)) for link in links]

        return links

    def get_sub_pages(self, unit_links):
        # Create a dictionary to store the category names and their corresponding page links
        sub_pages = {}
        base_url = "https://www.nfl.com"  # Assuming you have a base URL

        for unit, category_links in unit_links.items():
            sub_pages[unit] = {}

            for category, link in category_links.items():
                page_count = 0  # Initialize page count
                current_link = link  # Use the provided link as the starting point
                current_stat = category  # Set the current_stat to the category name

                # Initialize the category's dictionary
                sub_pages[unit][current_stat] = {page_count: current_link}

                # Create an infinite loop to scrape data from multiple pages
                while True:
                    # Request raw HTML for the current page
                    response = requests.get(current_link)

                    # Check if the request was successful
                    if response.status_code == 200:
                        # Create a BeautifulSoup object to parse the HTML
                        soup = BeautifulSoup(response.content, "html.parser")

                        # Find the "Next Page" link
                        next_page_link = soup.find('a', class_='nfl-o-table-pagination__next')

                        if next_page_link:
                            # Extract the 'href' attribute
                            href = next_page_link['href']

                            # Update current_link with the next page's URL
                            current_link = base_url + href
                            page_count += 1  # Increment page count

                            # Add the link to the category's dictionary
                            sub_pages[unit][current_stat][page_count] = current_link
                        else:
                            print(f"No more pages to scrape for {unit} - {current_stat}.")
                            break  # Exit the loop when there are no more pages
                    else:
                        print(f"Error: Unable to fetch data from {current_link} for {unit} - {current_stat}.")
                        break  # Exit the loop on request error

        # Display the collected category pages and their links
        for unit, categories in sub_pages.items():
            for category, pages in categories.items():
                print(f"{unit} - {category} Sub-Pages:")
                for page_num, page_link in pages.items():
                    print(f"Page {page_num}: {page_link}")
        return sub_pages

    def format_links(self, level):
        # Create a dictionary to store the links for each unit and its categories
        unit_links = {}

        if level == "player":
            # Define the URL for the player level
            all_links = self.get_links(level)  # Pass the URL as an argument
            # Create a dictionary to store the links
            team_stats_dict = {}

            for link in all_links:
                # Split the link by "/"
                parts = link.split('/')
                # Get the keys and values
                unit = "individual"  # e.g., individual, offense, defense, special-teams
                category = parts[6]
                url = link
                # Add to the dictionary
                if unit not in team_stats_dict:
                    team_stats_dict[unit] = {}
                team_stats_dict[unit][category] = url

        if level == "team":
            all_links = self.get_links(level)

            # Create a dictionary to store the links
            team_stats_dict = {}

            for link in all_links:
                # Split the link by "/"
                parts = link.split('/')
                # Get the keys and values
                unit = parts[5]  # e.g., offense, defense, special-teams
                category = parts[6]  # e.g., passing, rushing etc.
                url = link
                # Add to the dictionary
                if unit not in team_stats_dict:
                    team_stats_dict[unit] = {}
                team_stats_dict[unit][category] = url

        # Get stat category names and update unit_links
        stat_cols = {}

        for outer_key, inner_dict in team_stats_dict.items():
            inner_keys = list(inner_dict.keys())

            if outer_key in stat_cols:
                stat_cols[outer_key].extend(inner_keys)
            else:
                stat_cols[outer_key] = inner_keys

        # Update unit_links with the fetched links
        unit_links = team_stats_dict
        unit_links = self.get_sub_pages(unit_links)
        return unit_links

    def create_directory_if_not_exists(self, directory_path):
        # Checks if a directory exists at the specified path and creates it if it doesn't.

        if not os.path.exists(directory_path):
            try:
                os.makedirs(directory_path)
                print(f'Directory "{directory_path}" has been created.')
            except OSError as e:
                print(f'Error: Failed to create directory "{directory_path}".')
                print(e)
        else:
            print(f'Directory "{directory_path}" already exists.')

    def scrape_and_process_data(self, unit, category, level, unit_directory_path, unit_links):
        # Scrapes data for a specific category, processes it, and stores it in the appropriate directory.

        # Create a list to store DataFrames for the current category
        category_dfs = []

        # Loop through the sub-pages for the current category
        for page_num, page_url in unit_links[unit][category].items():
            # Request raw HTML for the current page
            response = requests.get(page_url)

            # Check if the request was successful
            if response.status_code == 200:
                # Create a BeautifulSoup object to parse the HTML
                soup = BeautifulSoup(response.content, "html.parser")

                # Find all elements with the class 'd3-o-player-stats--detailed'
                stats = soup.find_all(attrs={"class": f'd3-o-{level}-stats--detailed'})

                # Initialize lists to collect data
                stat_val = []
                stat_col = []

                # Loop through each <tr> element to extract and collect the text from <td> elements
                for row in stats:
                    # This gets the stat names
                    header_cells = row.find_all('th')

                    if len(header_cells) > 0:
                        for cell in header_cells:
                            stat_col.append(cell.get_text(strip=True))

                    # This gets the stats
                    data_cells = row.find_all('td')

                    if len(data_cells) > 0:
                        for cell in data_cells:
                            stat_val.append(cell.get_text(strip=True))

                # Determine the number of columns in each row
                num_columns = len(stat_col) if stat_col else 1  # Use 1 if stat_col is empty

                # Split the list into rows
                rows = [stat_val[i:i + num_columns] for i in range(0, len(stat_val), num_columns)]

                # Create a DataFrame for the current category and page
                df = pd.DataFrame(rows, columns=stat_col)

                # Append the DataFrame to the list for the current category
                category_dfs.append(df)
            else:
                print(f"Error: Unable to fetch data from {page_url} for {category}.")

        # Concatenate dataframes for the current category into one
        if category_dfs:
            merged_df = pd.concat(category_dfs, ignore_index=True)

            # Check if the DataFrame has a "Team" column before attempting to remove the duplicated part
            if 'Team' in merged_df.columns:
                # Remove duplicated part from the "Team" column
                merged_df['Team'] = merged_df['Team'].apply(lambda x: x[:len(x) // 2])

            # Create the directory if it doesn't exist
            self.create_directory_if_not_exists(unit_directory_path)

            # Specify the file path within the unit's directory
            csv_file_path = os.path.join(unit_directory_path, category + '.csv')

            # Export the DataFrame to a CSV file
            merged_df.to_csv(csv_file_path, index=False)  # Set index=False to exclude the index column

            print(f'DataFrame for category "{category}" in unit "{unit}" has been exported to {csv_file_path}')
        else:
            print(f"No data found for category '{category}' in unit '{unit}'")

    def get_stats(self, level):
        # Initiates the data scraping process for player or team statistics.
        self.set_current_season_and_week()

        if not isinstance(self.season, int):
            try:
                self.season = int(self.season)
                print("Converted season to integer.")
            except ValueError:
                print('The season cannot be converted to integer.')
                return
        else:
            self.season = str(self.season)

        if int(self.season) < 1970:
            raise ValidSeasonError(self.season)
        else:
            # Combine the base directory path with the current week for the current season,
            # else store data in 'reg' (regular season) directory
            directory_path = os.path.join('data', str(self.season), level)
            if int(self.season) == self.current_season:
                directory_path = os.path.join(directory_path, f'week{self.current_week}')

            unit_links = self.format_links(level)

            if level == "team":
                for unit, categories in unit_links.items():
                    for category, _ in categories.items():
                        # Create a subdirectory for the current unit
                        unit_directory_path = os.path.join(directory_path, unit)

                        # Call scrape_and_process_data with unit and category
                        self.scrape_and_process_data(unit, category, level, unit_directory_path, unit_links)

            elif level == "player":
                for unit, categories in unit_links.items():
                    for category, _ in categories.items():
                        # Directly use the week1 directory for player-level data
                        unit_directory_path = directory_path

                        # Pass unit and category to the scrape_and_process_data function
                        self.scrape_and_process_data(unit, category, level, unit_directory_path, unit_links)


