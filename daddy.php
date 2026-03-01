<?php

// --- Configuration ---
define('CHANNEL_KEY', 'premium603');
define('CHANNEL_SALT', 'a6fa2445e156106c');
define('FINGERPRINT', '1920x1080en-US');

// --- Proxy Logic ---
if (isset($_GET['resource'])) {

    // --- Authentication Functions ---
    function compute_pow_nonce($path, $timestamp) {
        $hmac_hash = hash_hmac('sha256', CHANNEL_KEY, CHANNEL_SALT);
        for ($nonce = 0; $nonce < 100000; $nonce++) {
            $message = $hmac_hash . CHANNEL_KEY . $path . $timestamp . $nonce;
            if (hexdec(substr(md5($message), 0, 4)) < 4096) return $nonce;
        }
        return 99999;
    }

    function generate_auth_token($path, $timestamp) {
        $message = CHANNEL_KEY . '|' . $path . '|' . $timestamp . '|' . FINGERPRINT;
        return substr(hash_hmac('sha256', $message, CHANNEL_SALT), 0, 16);
    }

    $resource_path = $_GET['resource'];
    $is_key_request = strpos($resource_path, 'key/') === 0;

    if ($is_key_request) {
        $full_url = 'https://chevy.soyspace.cyou/' . $resource_path;
        $auth_path = '/' . $resource_path;
    } else {
        $lookup_url = 'https://chevy.vovlacosa.sbs/server_lookup?channel_id=' . CHANNEL_KEY;
        $server_details_json = @file_get_contents($lookup_url, false, stream_context_create(["ssl"=>["verify_peer"=>false, "verify_peer_name"=>false]]));
        if ($server_details_json === FALSE) { http_response_code(503); exit("Error: Could not contact server lookup."); }
        $server_details = json_decode($server_details_json, true);
        $server_key = $server_details['server_key'];
        $full_url = "https://chevy.adsfadfds.cfd/proxy/{$server_key}/" . CHANNEL_KEY . "/{$resource_path}";
        $auth_path = $resource_path;
    }

    $timestamp = time();
    $nonce = compute_pow_nonce($auth_path, $timestamp);
    $auth_token = generate_auth_token($auth_path, $timestamp);

    if ($is_key_request) {
        $headers = ['X-Key-Timestamp: '.$timestamp, 'X-Key-Nonce: '.$nonce, 'X-Key-Token: '.$auth_token, 'X-Fingerprint: '.FINGERPRINT, 'X-Country-Code: US'];
    } else {
        $headers = ['X-Timestamp: '.$timestamp, 'X-Nonce: '.$nonce, 'X-Auth-Token: '.$auth_token, 'X-Fingerprint: '.FINGERPRINT, 'X-Country-Code: US'];
    }

    $ch = curl_init($full_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_USERAGENT, $_SERVER['HTTP_USER_AGENT'] ?? 'Mozilla/5.0');
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);

    $content = curl_exec($ch);
    if ($content === false) { http_response_code(502); exit("cURL Error: " . curl_error($ch)); }
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $content_type = curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
    curl_close($ch);

    if ($http_code != 200) { http_response_code($http_code); exit("Upstream error: {$http_code}"); }

    // *** FIX: Check for .m3u8 extension instead of .css ***
    if (pathinfo($resource_path, PATHINFO_EXTENSION) === 'm3u8') {
        $content = preg_replace_callback(
            '/(#EXT-X-KEY:.*?URI=")([^"]+)(")/m',
            fn($m) => $m[1] . 'daddy.php?resource=' . ltrim(parse_url($m[2], PHP_URL_PATH), '/') . $m[3],
            $content
        );
        $content_type = 'application/vnd.apple.mpegurl';
    }

    header('Content-Type: ' . $content_type);
    echo $content;
    exit;
}

// --- HTML Player Page with Logs and Info ---
?>
<!DOCTYPE html>
<html>
<head>
    <title>Daddy Player</title>
    <meta charset="utf-8">
    <style>
        body, html { margin: 0; padding: 0; height: 100%; font-family: monospace; background-color: #181818; color: #eee; }
        #player-container { width: 70%; height: 100%; float: left; }
        #info-container { width: 30%; height: 100%; float: right; background-color: #222; overflow-y: auto; }
        #player { width: 100%; height: 100%; }
        .info-box { padding: 15px; border-bottom: 1px solid #444; }
        h3 { margin: 0 0 10px 0; color: #0f0; }
        #stream-url { word-wrap: break-word; font-size: 12px; }
        #logs { font-size: 11px; white-space: pre-wrap; word-wrap: break-word; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.8/dist/hls.min.js"></script>
</head>
<body>
    <div id="player-container">
        <video id="player" controls></video>
    </div>
    <div id="info-container">
        <div class="info-box">
            <h3>Stream URL</h3>
            <div id="stream-url"></div>
        </div>
        <div class="info-box">
            <h3>Live Logs</h3>
            <div id="logs"></div>
        </div>
    </div>

    <script>
        const video = document.getElementById('player');
        const logsContainer = document.getElementById('logs');
        const urlContainer = document.getElementById('stream-url');
        
        // *** FIX: Request mono.m3u8 for the video stream ***
        const streamUrl = 'daddy.php?resource=mono.m3u8';

        urlContainer.textContent = streamUrl;

        function log(type, data) {
            const time = new Date().toLocaleTimeString();
            logsContainer.innerHTML = `[${time}] [${type}] ${JSON.stringify(data)}\n` + logsContainer.innerHTML;
        }

        if (Hls.isSupported()) {
            const hls = new Hls({ debug: true });
            hls.loadSource(streamUrl);
            hls.attachMedia(video);
            
            hls.on(Hls.Events.MANIFEST_PARSED, (e,d) => {
                log('Manifest Parsed', `Qualities: ${d.levels.map(l => l.height+'p').join(', ')}`)
                video.play();
            });
            hls.on(Hls.Events.FRAG_LOADING, (e,d) => log('Fragment Loading', d.frag.url));
            hls.on(Hls.Events.ERROR, (e,d) => {
                if (d.fatal) {
                    log('FATAL ERROR', d.details);
                    console.error('Fatal HLS Error:', d);
                }
            });

        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = streamUrl;
        } else {
            log('Fatal Error', 'HLS not supported');
        }
    </script>
</body>
</html>
