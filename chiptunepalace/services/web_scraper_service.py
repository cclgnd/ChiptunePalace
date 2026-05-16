import requests
from urllib.parse import quote
from PySide6.QtCore import QThread, Signal
from chiptunepalace.services.track_service import TrackService

class ScraperThread(QThread):
    """
    Background thread for executing scraping tasks without blocking the UI.
    """
    finished = Signal(object) # Can emit list of results or other objects
    error = Signal(str)

    def __init__(self, task_fn, *args, **kwargs):
        super().__init__()
        self.task_fn = task_fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            results = self.task_fn(*self.args, **self.kwargs)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class WebScraperService:
    """
    Handles the adaptive scraping of music metadata from external sources.
    """
    def __init__(self):
        self.session = requests.Session()
        self.libretro_base = "https://raw.githubusercontent.com/libretro-thumbnails"
        # Mapping common names to Libretro names
        self.system_map = {
            "SNES": "Nintendo - Super Nintendo Entertainment System",
            "NES": "Nintendo - Nintendo Entertainment System",
            "GENESIS": "Sega - Mega Drive - Genesis",
            "GAMEBOY": "Nintendo - Game Boy",
            "GB": "Nintendo - Game Boy",
            "GBA": "Nintendo - Game Boy Advance",
            "MASTERSYSTEM": "Sega - Master System - Mark III",
            "PCENGINE": "NEC - PC Engine - TurboGrafx 16",
            "PLAYSTATION": "Sony - PlayStation"
        }

    def get_consoles(self) -> list:
        """
        Fetches the list of popular consoles from VGMRips.
        """
        import requests
        import re
        from bs4 import BeautifulSoup
        
        url = "https://vgmrips.net/packs/systems"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            consoles = []
            # 1. Fetch VGMRips Consoles
            import re
            for a in soup.find_all('a', href=re.compile(r'/packs/system/')):
                name = a.text.strip()
                href = a.get('href')
                if name and not name.isdigit() and "PACKS" not in name.upper():
                    if not href.startswith('http'):
                        href = "https://vgmrips.net" + href
                    consoles.append({"name": name, "url": href})

            # De-duplicate
            unique_consoles = []
            seen = set()
            for c in consoles:
                if c['name'] not in seen:
                    unique_consoles.append(c)
                    seen.add(c['name'])

            # 2. Add some ModArchive "Genres" to catalog
            unique_consoles.append({"name": "MODARCHIVE: CHIPTUNE", "url": "https://modarchive.org/index.php?request=view_genres&query=14"})
            unique_consoles.append({"name": "MODARCHIVE: DEMO", "url": "https://modarchive.org/index.php?request=view_genres&query=18"})
            unique_consoles.append({"name": "MODARCHIVE: KEYGEN", "url": "https://modarchive.org/index.php?request=view_genres&query=57"})

            return unique_consoles[:60]
        except Exception as e:
            print(f"Catalog Scraper Error: {e}")
            return []

    def get_packs_by_console(self, console_url: str) -> list:
        """
        Fetches all music packs for a specific console or genre.
        Supports both VGMRips and ModArchive URLs.
        """
        if "modarchive.org" in console_url:
            return self._search_modarchive_by_url(console_url)
        return self._get_vgmrips_packs(console_url)

    def _get_vgmrips_packs(self, console_url: str) -> list:
        import requests
        from bs4 import BeautifulSoup
        
        try:
            response = requests.get(console_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for h2 in soup.find_all('h2'):
                links = h2.find_all('a')
                if len(links) >= 2:
                    title = links[0].text
                    zip_url = links[-1].get('href')
                    if zip_url.endswith('.zip'):
                        if not zip_url.startswith('http'):
                            zip_url = "https://vgmrips.net" + zip_url
                        results.append({"title": title, "url": zip_url, "source": "VGMRips"})
            return results
        except Exception as e:
            print(f"Pack Scraper Error: {e}")
            return []

    def _search_modarchive_by_url(self, url: str) -> list:
        import requests
        from bs4 import BeautifulSoup
        import re
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for a in soup.find_all('a', href=re.compile(r'moduleid=\d+')):
                href = a.get('href')
                if 'downloads.php' in href:
                    title_link = a.find_next('a', class_='standard-link')
                    title = title_link.text.strip() if title_link else "Unknown Module"
                    
                    if not href.startswith('http'):
                        href = "https://api.modarchive.org/" + href.split('/')[-1] if 'api' not in href else "https://api.modarchive.org/" + href
                    
                    results.append({
                        "title": title,
                        "url": href,
                        "source": "ModArchive"
                    })
            return results
        except Exception as e:
            print(f"ModArchive Pack Scraper Error: {e}")
            return []

    def get_tracks_in_pack(self, pack_url: str) -> list:
        """
        Fetches individual track names from a pack's detail page.
        Currently supports VGMRips.
        """
        import requests
        from bs4 import BeautifulSoup
        if "vgmrips.net" not in pack_url:
            return [] # ModArchive modules are single tracks already
            
        try:
            response = requests.get(pack_url.replace('.zip', ''), timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            tracks = []
            # On VGMRips, tracks are usually in a table or list
            for td in soup.find_all('td', class_='title'):
                name = td.text.strip()
                if name:
                    tracks.append({"title": name})
            return tracks
        except Exception as e:
            print(f"Track Scraper Error: {e}")
            return []

    def get_artwork(self, console_name: str, game_name: str) -> dict:
        """
        Attempts to find cover art and screenshot from Libretro Thumbnails.
        """
        system = self.system_map.get(console_name.upper(), console_name)
        # Libretro uses special characters encoding (e.g. # -> %23)
        safe_game = quote(game_name)
        
        urls = {
            "boxart": f"{self.libretro_base}/{system}/master/Named_Boxarts/{safe_game}.png",
            "screenshot": f"{self.libretro_base}/{system}/master/Named_Snaps/{safe_game}.png"
        }
        return urls

    def search_online(self, query: str) -> list:
        """
        Searches multiple online repositories and returns a combined list of results.
        """
        results = []
        
        # 1. Search VGMRips
        try:
            results.extend(self._search_vgmrips(query))
        except Exception as e:
            print(f"VGMRips Search Error: {e}")
            
        # 2. Search ModArchive
        try:
            results.extend(self._search_modarchive(query))
        except Exception as e:
            print(f"ModArchive Search Error: {e}")
            
        # 3. Search Project 2612
        try:
            results.extend(self._search_project2612(query))
        except Exception as e:
            print(f"Project 2612 Search Error: {e}")
            
        return results

    def _search_project2612(self, query: str) -> list:
        import requests
        from bs4 import BeautifulSoup
        url = f"http://project2612.org/search.php?query={query}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        # Project 2612 search results are usually in a table
        for a in soup.find_all('a', href=lambda x: x and 'details.php?id=' in x):
            title = a.text.strip()
            detail_url = "http://project2612.org/" + a.get('href')
            # Extract ID to build download link (usually download.php?id=...)
            import re
            match = re.search(r'id=(\d+)', detail_url)
            if match:
                track_id = match.group(1)
                zip_url = f"http://project2612.org/download.php?id={track_id}"
                results.append({
                    "title": title,
                    "url": zip_url,
                    "artist": "Sega Genesis",
                    "source": "Project2612"
                })
        return results

    def _search_vgmrips(self, query: str) -> list:
        import requests
        from bs4 import BeautifulSoup
        
        url = f"https://vgmrips.net/packs/search?q={query}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for h2 in soup.find_all('h2'):
            links = h2.find_all('a')
            if len(links) >= 2:
                title = links[0].text
                zip_url = links[-1].get('href')
                if zip_url.endswith('.zip'):
                    if not zip_url.startswith('http'):
                        zip_url = "https://vgmrips.net" + zip_url
                        
                    results.append({
                        "title": title,
                        "url": zip_url,
                        "artist": "Various",
                        "source": "VGMRips"
                    })
        return results

    def _search_modarchive(self, query: str) -> list:
        import requests
        from bs4 import BeautifulSoup
        
        # ModArchive search URL
        url = f"https://modarchive.org/index.php?request=search&query={query}&submit=Find&search_type=filename_or_songtitle"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        # Results are typically in <tr> elements within a table
        # We look for links to downloads.php?moduleid=...
        import re
        for a in soup.find_all('a', href=re.compile(r'moduleid=\d+')):
            href = a.get('href')
            if 'downloads.php' in href:
                title_link = a.find_next('a', class_='standard-link')
                if title_link:
                    title = title_link.text.strip()
                else:
                    title = a.get('title', 'Unknown Module')
                
                # Normalize URL
                if not href.startswith('http'):
                    href = "https://api.modarchive.org/" + href.split('/')[-1] if 'api' not in href else "https://api.modarchive.org/" + href
                
                results.append({
                    "title": title,
                    "url": href,
                    "artist": "Module Artist",
                    "source": "ModArchive"
                })
        return results[:20] # Limit results

    def discover_music_sources(self):
        """
        Identifies potential reliable sources for music metadata.
        """
        return ["VGMdb", "ModArchive", "Project2612"]

    def scrape_metadata_for_file(self, file_path: str) -> dict:
        """
        Attempts to find metadata for a given chiptune file by filename or tags.
        Uses regex patterns to extract Artist and Title.
        """
        import os
        import re
        filename = os.path.basename(file_path)
        name_no_ext = os.path.splitext(filename)[0]
        
        # Patterns to try
        patterns = [
            r'^(?P<artist>.+?)\s*-\s*(?P<title>.+)$',      # Artist - Title
            r'^(?P<title>.+?)\s*\((?P<artist>.+)\)$',    # Title (Artist)
            r'^(?P<artist>.+?)\s*-\s*(?P<album>.+?)\s*-\s*(?P<title>.+)$', # Artist - Album - Title
        ]
        
        metadata = {
            "title": name_no_ext,
            "artist": "Unknown Artist",
            "album": "Unknown Album",
            "genre": "Chiptune"
        }
        
        for p in patterns:
            match = re.match(p, name_no_ext)
            if match:
                res = match.groupdict()
                metadata.update(res)
                break
                
        print(f"AdaptiveScraper: Parsed {filename} -> {metadata['artist']} - {metadata['title']}")
        return metadata

    def scrape_artist_info(self, artist_name: str, source: str) -> dict:
        print(f"Scraping {artist_name} from {source}...")
        # Placeholder for API calls
        return {
            "tracks": [],
            "genres": ["Chiptune"],
            "metadata_source": source
        }

    def integrate_metadata(self, file_path: str, scraped_data: dict):
        """
        Updates the database with scraped info.
        """
        # Implementation would call track_service.update_track or similar
        print(f"Integrating metadata for {file_path}")
        return True
