
import re
import subprocess
import logging
import datetime

# Fallback for ZoneInfo for older Python versions
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# --- Configuration ---
CRICHD_BASE_URL = "https://crichd.com.co"
PLAYER_DOMAIN_PATTERN = r"https://(?:player\.)?dadocric\.st/player\.php"
PLAYERADO_EMBED_URL = "https://playerado.top/embed2.php"
ATPLAY_URL = "https://player0003.com/atplay.php"
OUTPUT_M3U_FILE = "siamscrichd.m3u"
EPG_URL = "https://github.com/epgshare01/share/raw/master/epg_ripper_ALL_SOURCES1.xml.gz"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_command(command):
    """Runs a shell command and returns its stdout."""
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        logging.error(f"Command failed: {command}\nStderr: {result.stderr.strip()}")
    return result.stdout

def is_stream_valid(stream_url, referrer):
    """Checks if a stream URL is valid by fetching it and checking for #EXTM3U."""
    logging.info(f"Validating stream: {stream_url}")
    command = f'curl -L --connect-timeout 10 -m 15 --referer "{referrer}" "{stream_url}"'
    content = run_command(command)
    if content and content.strip().startswith("#EXTM3U") and "404 Not Found" not in content:
        logging.info("Stream is valid.")
        return True
    else:
        logging.warning(f"Stream is invalid or expired.")
        return False

def get_channel_links():
    """Fetches all channel links from the CricHD homepage."""
    logging.info(f"Fetching channel links from {CRICHD_BASE_URL}")
    main_page_content = run_command(f"curl -L {CRICHD_BASE_URL}")
    if not main_page_content:
        logging.error("Failed to fetch CricHD homepage")
        return []
    pattern = r'<li class="has-sub"><a href="(' + re.escape(CRICHD_BASE_URL) + r'/channels/[^"]+)"'
    channel_links = re.findall(pattern, main_page_content)
    logging.info(f"Found {len(channel_links)} channel links")
    return channel_links

def get_stream_link(channel_url):
    """Extracts the stream link and related info from a channel page."""
    logging.info(f"Processing channel: {channel_url}")
    channel_page_content = run_command(f"curl -L {channel_url}")
    if not channel_page_content:
        return None, None, None

    pattern_string = r"<a[^>]+href=['"](" + PLAYER_DOMAIN_PATTERN + r"\?[^'"]*?id=[^'"]+)['"]"
    player_link_match = re.search(pattern_string, channel_page_content)
    if not player_link_match:
        logging.warning(f"Player link not found on {channel_url}")
        return None, None, None

    player_link = player_link_match.group(1)
    player_id = player_link.split("id=")[1].split("&")[0] # a bit more robust
    playerado_url = f"{PLAYERADO_EMBED_URL}?id={player_id}"
    
    embed_page_content = run_command(f"curl -L '{playerado_url}'")
    if not embed_page_content:
        return None, None, None

    fid_match = re.search(r'fid\s*=\s*"([^"]+)"', embed_page_content)
    if not fid_match:
        logging.warning(f"Could not find 'fid' on {playerado_url}")
        return None, None, None
    fid = fid_match.group(1)
    
    atplay_url_params = f"?v={fid}" # Simplified, other params seem unnecessary for link structure
    atplay_url = f"{ATPLAY_URL}{atplay_url_params}"
    
    logging.info(f"Fetching atplay page: {atplay_url}")
    atplay_page_content = run_command(f"curl -iL --user-agent \"Mozilla/5.0\" --referer \"https://playerado.top/\" '{atplay_url}'")
    if not atplay_page_content:
        return None, None, None

    # Find the variables for md5, expires, and s
    try:
        md5 = re.search(r'var\s+md5\s*=\s*"(.*?)"', atplay_page_content).group(1)
        expires = re.search(r'var\s+expires\s*=\s*"(.*?)"', atplay_page_content).group(1)
        s_val = re.search(r'var\s+s\s*=\s*"(.*?)"', atplay_page_content).group(1)
        
        # Find the base URL construction
        base_url_parts = re.findall(r"'([^']*)'", re.search(r"var\s+url\s*=\s*([^;]+);", atplay_page_content).group(1))
        base_url = "".join(base_url_parts)
    except AttributeError:
        logging.warning(f"Could not extract all stream parameters from {atplay_url}")
        return None, None, None

    stream_path = f"/hls/{fid}.m3u8"
    final_stream_link = f"{base_url}{stream_path}?md5={md5}&expires={expires}&ch={fid}&s={s_val}"
    
    channel_name = "Unknown Channel"
    channel_name_match = re.search(r'<title>(.*?)</title>', channel_page_content)
    if channel_name_match:
        channel_name = channel_name_match.group(1).split(" Live Streaming")[0]

    logging.info(f"Extracted stream for {channel_name}")
    return channel_name, final_stream_link, "https://player0003.com/"


if __name__ == "__main__":
    channel_links = get_channel_links()
    
    valid_channels = []
    for link in channel_links:
        name, stream, referrer = get_stream_link(link)
        if name and stream and referrer:
            if is_stream_valid(stream, referrer):
                valid_channels.append((name, stream, referrer))
            else:
                logging.info(f"Skipping invalid or expired channel: {name}")

    total_channels = len(valid_channels)
    
    if ZoneInfo:
        dhaka_tz = ZoneInfo('Asia/Dhaka')
        update_time = datetime.datetime.now(dhaka_tz).strftime('%Y-%m-%d %I:%M:%S %p')
    else: # Fallback for older python
        update_time = datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p') + " UTC"

    with open(OUTPUT_M3U_FILE, "w", encoding='utf-8') as f:
        f.write(f'#EXTM3U x-tvg-url="{EPG_URL}"\n')
        f.write(f'# Made by Siam3310\n')
        f.write(f'# Last updated: {update_time} (Bangladesh/Dhaka)\n')
        f.write(f'# Total channels: {total_channels}\n\n')
        for name, stream, referrer in valid_channels:
            f.write(f'#EXTINF:-1 tvg-name="{name}",{name}\n')
            f.write(f"#EXTVLCOPT:http-referrer={referrer}\n")
            f.write(f"{stream}\n")
    
    logging.info(f"Playlist '{OUTPUT_M3U_FILE}' created successfully with {total_channels} valid channels.")
