
import re
import requests
import logging
import datetime
import sys
import os
import cloudscraper
from bs4 import BeautifulSoup

# --- Configuration ---
CRICHD_BASE_URL = "https://vf.crichd.tv"
WEB_URL = "https://vf.crichd.tv/web"
OUTPUT_M3U_FILE = "siamscrichd.m3u"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
REQUESTS_TIMEOUT = 30

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    stream=sys.stdout
)

# --- Session Initialization ---
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)
scraper.headers.update({'User-Agent': USER_AGENT})

# --- FID to Channel Name Mapping ---
fid_to_channel = {
    "willowusa": "WILLOW HD", "willowextra": "WILLOW EXTRA", "skysme": "SKY SPORTS MAIN EVENT",
    "skyscricket": "SKY SPORTS CRICKET", "skysact": "SKY SPORTS ACTION", "skysfott": "SKY SPORTS FOOTBALL",
    "skysfor1": "SKY SPORTS F1", "skysare": "SKY SPORTS ARENA", "skysmixx": "SKY SPORTS MIX",
    "skysprem": "SKY SPORTS PREMIER LEAGUE", "skysgol": "SKY SPORTS GOLF", "skyspnews": "SKY SPORTS NEWS",
    "skystennis": "SKY SPORTS TENNIS", "bbtsp1": "TNT SPORTS 1", "bbtsp2": "TNT SPORTS 2",
    "bbtsp3": "TNT SPORTS 3", "bbtespn": "TNT SPORTS 4", "ptvpk": "PTV SPORTS", "asportshd": "A SPORTS HD",
    "sonysixind": "SONY SIX", "ten1hd": "SONY TEN 1", "sonyespnind": "SONY TEN 3", "tenspk": "TEN SPORTS",
    "star1in": "STAR SPORTS 1 HINDI", "star2in": "STAR SPORTS 2", "geosp": "GEO SUPER", "wwe": "WWE NETWORK",
    "premieruk": "PREMIER SPORTS 1", "laligauk": "LALIGA TV", "eurosp1": "EUROSPORT 1", "eurosp2": "EUROSPORT 2",
    "espnusa": "ESPN", "espn2": "ESPN 2", "supercricket": "SUPERSPORT CRICKET", "fox501": "FOX CRICKET",
    "hdchnl6": "SUPERSPORT VARIETY 1", "hdchnl7": "SUPERSPORT VARIETY 2", "hdchnl8": "SUPERSPORT VARIETY 3",
    "hdchnl9": "SUPERSPORT VARIETY 4", "hdchnl10": "TNT SPORTS 5", "hdchnl11": "TNT SPORTS 6",
    "hdchnl12": "TNT SPORTS 7", "hdchnl13": "TNT SPORTS 8", "hdchnl14": "TNT SPORTS 9",
    "hdchnl15": "TNT SPORTS 10", "espn22": "DIRECT SPORTS SP", "espn1hd": "CHANNEL 17",
    "hdchnl18": "CRICKET HD 18", "hdchnl19": "PPV", "hdchnl20": "SKY BOX OFFICE", "mls786": "HIGH HD 3",
    "hubpremier1": "HUB PREMIER 1", "hubpremier2": "HUB PREMIER 2", "hubpremier3": "HUB PREMIER 3",
    "hubpremier4": "HUB PREMIER 4", "hubpremier5": "HUB PREMIER 5",
}

def get_page_content(url, referrer=None):
    """Fetches content for a given URL using the cloudscraper session."""
    logging.debug(f"Fetching URL: {url} with referrer: {referrer}")
    try:
        response = scraper.get(url, headers={'Referer': referrer} if referrer else {}, timeout=REQUESTS_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

def get_fids_and_referrers():
    """Scrapes all channel pages from dedicated lists to collect FIDs and referrers."""
    logging.info("--- Step 1: Finding all channel pages and collecting FIDs/referrers ---")
    main_page_content = get_page_content(WEB_URL)
    if not main_page_content:
        logging.critical("Failed to fetch main web page. Exiting.")
        return []

    soup = BeautifulSoup(main_page_content, 'html.parser')
    unique_links = set()
    for panel_id in ['primary-menu', 'channels']:
        panel = soup.find('div', id=panel_id)
        if panel:
            for a in panel.find_all('a', href=True):
                href = a['href']
                if CRICHD_BASE_URL in href and "live-stream" in href:
                    unique_links.add(href)
    
    logging.info(f"Found {len(unique_links)} unique channel pages to process.")

    collected_fids = {}
    for link in sorted(list(unique_links)):
        logging.info(f"Processing page: {link}")
        channel_page_content = get_page_content(link, referrer=WEB_URL)
        if not channel_page_content: continue

        intermediary_matches = re.findall(r'src=\\\"(//streamcrichd\.com/update/([^\"]+))\\\"', channel_page_content)
        for full_path, php_file in set(intermediary_matches):
            intermediary_url = f"https:{full_path}"
            intermediary_content = get_page_content(intermediary_url, referrer=link)
            if not intermediary_content: continue

            fid_match = re.search(r'fid\s*=\s*["\']([^"\']+)["\']', intermediary_content)
            if fid_match:
                fid = fid_match.group(1)
                if fid not in collected_fids:
                    clean_name = fid_to_channel.get(fid, fid.upper()) # Use mapping, fallback to FID
                    logging.info(f"SUCCESS: Found fid: '{fid}' ({clean_name})")
                    collected_fids[fid] = {'name': clean_name, 'fid': fid, 'referrer': intermediary_url}
    
    logging.info(f"--- Finished Step 1: Collected info for {len(collected_fids)} unique FIDs. ---")
    return list(collected_fids.values())

def get_stream_from_fid(fid_info):
    """Uses the collected fid and referrer to get the final m3u8 stream URL."""
    fid = fid_info['fid']
    name = fid_info['name']
    final_referrer = fid_info['referrer']

    logging.info(f"--- Step 2: Extracting stream for fid: '{fid}' ({name}) ---")
    player_url = f"https://executeandship.com/premiumcr.php?player=desktop&live={fid}"
    player_page_content = get_page_content(player_url, referrer=final_referrer)

    if not player_page_content:
        logging.error(f"Failed to fetch final player page for fid: {fid}")
        return None

    stream_array_match = re.search(r"return \(\[(.*?)\]\.join", player_page_content, re.DOTALL)
    if not stream_array_match:
        logging.error(f"Could not find the stream URL array for fid: {fid}.")
        return None

    char_list_str = stream_array_match.group(1)
    char_list = re.findall(r'"([^"]*)"', char_list_str)
    final_url = "".join(char_list).replace("\\/", "/")

    if "m3u8" in final_url:
        logging.info(f"SUCCESS: Extracted stream for '{name}'")
        return final_url
    else:
        logging.warning(f"Extracted URL for '{name}' may not be a valid m3u8 stream.")
        return None

if __name__ == "__main__":
    logging.info("--- STARTING CRICHD STREAM GETTER ---")
    fids_info = get_fids_and_referrers()
    all_streams = []
    if fids_info:
        for fid_info in fids_info:
            stream_url = get_stream_from_fid(fid_info)
            if stream_url:
                all_streams.append((fid_info['name'], stream_url))

    logging.info("--- SCRAPE COMPLETE ---")
    total_streams = len(all_streams)
    logging.info(f"Total streams successfully extracted: {total_streams}")

    if total_streams == 0:
        logging.warning("No streams were found. The M3U file will be empty.")

    logging.info(f"Writing {total_streams} streams to {OUTPUT_M3U_FILE}")
    try:
        with open(OUTPUT_M3U_FILE, "w", encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            # Sort by channel name for a clean list
            for name, stream_url in sorted(all_streams, key=lambda x: x[0]):
                f.write(f'#EXTINF:-1,{name}\n')
                f.write(f"{stream_url}\n")
        logging.info("M3U file written successfully.")
    except Exception as e:
        logging.critical("Failed to write the M3U file.", exc_info=True)
        sys.exit(1)

    logging.info("--- SCRIPT EXECUTION FINISHED ---")
