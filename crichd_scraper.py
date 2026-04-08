
import requests
import re
import logging
import sys

# --- Configuration ---
INITIAL_URL = "https://streamcrichd.com/update/willowcricket.php"
STRICT_REFERRER = "https://streamcrichd.com/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
REQUESTS_TIMEOUT = 15

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

def extract_willow_stream():
    """
    Uses a requests.Session to mimic a browser session, handling cookies
    and headers consistently to bypass anti-scraping measures.
    """
    logging.info("--- Creating a new browser session ---")
    with requests.Session() as session:
        session.headers.update({
            'User-Agent': USER_AGENT,
            'Referer': STRICT_REFERRER
        })

        try:
            logging.info("--- Step 1: Fetching initial page ---")
            initial_response = session.get(INITIAL_URL, timeout=REQUESTS_TIMEOUT)
            initial_response.raise_for_status()
            initial_content = initial_response.text

            logging.info("--- Step 2: Fetching premium.js script ---")
            # Correct, robust regex using back-referencing for quotes.
            premium_js_match = re.search(r'src=(["\'])//executeandship.com/premium.js\1', initial_content)
            if not premium_js_match:
                logging.error("Could not find \'premium.js\' script. Aborting.")
                return None

            premium_js_url = "https:" + "//executeandship.com/premium.js"
            session.get(premium_js_url, timeout=REQUESTS_TIMEOUT).raise_for_status()

            logging.info("--- Step 3: Extracting iframe URL ---")
            # Correct, robust regex using back-referencing for quotes.
            fid_match = re.search(r'fid=(["\'])([^"\']+)\1', initial_content)
            if not fid_match:
                logging.error("Could not find \'fid\' in the initial page. Aborting.")
                return None

            fid = fid_match.group(2)
            iframe_url = f"https://executeandship.com/premiumcr.php?player=desktop&live={fid}"

            logging.info("--- Step 4: Fetching player iframe page ---")
            player_page_response = session.get(iframe_url, timeout=REQUESTS_TIMEOUT)
            player_page_response.raise_for_status()
            player_page_content = player_page_response.text

            logging.info("--- Step 5: Extracting final stream URL ---")
            stream_array_match = re.search(r"return \(\[(.*?)\]\.join", player_page_content, re.DOTALL)
            if not stream_array_match:
                logging.error("Could not find the stream URL array. Aborting.")
                return None

            char_list_str = stream_array_match.group(1)
            char_list = re.findall(r'"([^"]*)"', char_list_str)
            final_url = "".join(char_list).replace("\\/", "/")

            return final_url

        except requests.exceptions.RequestException as e:
            logging.error(f"A network error occurred: {e}")
            return None

if __name__ == "__main__":
    logging.info("--- STARTING WILLOW CRICKET STREAM EXTRACTOR ---")
    stream_url = extract_willow_stream()

    if stream_url:
        logging.info("--- EXTRACTION SUCCESSFUL ---")
        print(f"\nFinal Stream URL:\n{stream_url}\n")
    else:
        logging.error("--- EXTRACTION FAILED ---")
        sys.exit(1)
