<?php

// Channel constants
define('CHANNEL_KEY', 'premium603');
define('CHANNEL_SALT', 'a6fa2445e156106c');
define('FINGERPRINT', '1920x1080en-US'); // Hardcoded fingerprint
define('BASE_URL', 'https://chevy.vovlacosa.sbs/proxy/top1/cdn/' . CHANNEL_KEY . '/');

// --- Authentication Logic ---

function compute_pow_nonce($path, $timestamp) {
    $hmac_hash = hash_hmac('sha256', CHANNEL_KEY, CHANNEL_SALT);
    for ($nonce = 0; $nonce < 100000; $nonce++) {
        $message = "{$hmac_hash}" . CHANNEL_KEY . "{$path}{$timestamp}{$nonce}";
        $md5_hash = md5($message);
        if (hexdec(substr($md5_hash, 0, 4)) < 4096) {
            return $nonce;
        }
    }
    return 99999; // Fallback nonce
}

function generate_auth_token($path, $timestamp) {
    $message = CHANNEL_KEY . "|{$path}|{$timestamp}|" . FINGERPRINT;
    $hash = hash_hmac('sha256', $message, CHANNEL_SALT);
    return substr($hash, 0, 16); // The token is the first 16 chars of the hash
}

// --- Link Generation Logic ---

// The target resource
$resource = 'mono.m3u8';
$auth_path = $resource;

// Generate auth values
$timestamp = time();
$nonce = compute_pow_nonce($auth_path, $timestamp);
$auth_token = generate_auth_token($auth_path, $timestamp);

// The full URL to fetch
$full_url = BASE_URL . $resource;

// The headers to send
$headers = [
    'X-Timestamp' => $timestamp,
    'X-Nonce' => $nonce,
    'X-Auth-Token' => $auth_token,
    'X-Fingerprint' => FINGERPRINT,
    'X-Country-Code' => 'US'
];

// --- HTML Page to display the link and headers ---
?>
<!DOCTYPE html>
<html>
<head>
    <title>Live Link Fetcher</title>
    <style>
        body { font-family: sans-serif; }
        .container { padding: 20px; }
        h1, h2 { color: #333; }
        .code-block {
            background-color: #f5f5f5;
            padding: 15px;
            border: 1px solid #ccc;
            border-radius: 5px;
            white-space: pre-wrap;
            word-wrap: break-word;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Live Stream Fetch Details</h1>

        <p>The server requires custom authentication headers for every request. Here are the dynamically generated details to fetch the main playlist:</p>

        <h2>Fetch URL</h2>
        <div class="code-block"><?php echo htmlspecialchars($full_url); ?></div>

        <h2>Required HTTP Headers</h2>
        <div class="code-block"><?php
        foreach ($headers as $key => $value) {
            echo htmlspecialchars($key) . ": " . htmlspecialchars($value) . "<br>";
        }
        ?></div>

        <h2>Example cURL Command</h2>
        <p>You can use this command in your terminal to verify:</p>
        <div class="code-block"><?php
            $curl_command = "curl -v -L ";
            foreach ($headers as $key => $value) {
                $curl_command .= "-H '" . htmlspecialchars($key, ENT_QUOTES) . ": " . htmlspecialchars($value, ENT_QUOTES) . "' ";
            }
            $curl_command .= "'" . htmlspecialchars($full_url, ENT_QUOTES) . "'";
            echo $curl_command;
        ?></div>
    </div>
</body>
</html>
