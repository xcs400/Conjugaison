<?php
/**
 * Serveur PHP pour l'application d'apprentissage de conjugaison espagnole.
 * Utilise la base commune verbs_data.json et persiste la progression
 * de manière 100% compatible avec la version Python.
 */

// Si le fichier demandé existe sur le disque, on laisse le serveur PHP natif le servir
$uri = $_SERVER['REQUEST_URI'];
$uri = explode('?', $uri)[0]; // Retirer les paramètres GET pour le routage

if (file_exists(__DIR__ . $uri) && !is_dir(__DIR__ . $uri) && $uri !== '/apprentissage.php') {
    return false;
}

// Fichiers de données
$verbs_data_file = __DIR__ . '/verbs_data.json';
$flagged_file = __DIR__ . '/flagged_phrases.json';

// Lire le body JSON une seule fois (php://input ne peut être lu qu'une fois)
$body = null;
if ($_SERVER['REQUEST_METHOD'] === 'POST' || $_SERVER['REQUEST_METHOD'] === 'PUT') {
    $body = json_decode(file_get_contents('php://input'), true);
}

// Résolution dynamique de l'utilisateur actif par paramètre GET/POST ou Cookie (Aline, Pascal, Test)
$active_user = 'Aline';
if (isset($_GET['user'])) {
    $active_user = $_GET['user'];
} elseif (isset($body['user'])) {
    $active_user = $body['user'];
} elseif (isset($_COOKIE['active_user'])) {
    $active_user = $_COOKIE['active_user'];
}
$safe_user = preg_replace('/[^a-zA-Z0-9]/', '', strtolower($active_user));
if (!in_array($safe_user, ['aline', 'pascal', 'camil', 'test'])) {
    $safe_user = 'aline';
}
$stats_file = __DIR__ . '/stats_apprentissage_' . $safe_user . '.json';

// Fonction de nettoyage de clé (accent et espaces), identique à Python
function sanitize_key($raw) {
    if (class_exists('Normalizer')) {
        $normalized = Normalizer::normalize($raw, Normalizer::FORM_D);
    } else {
        // Fallback si l'extension intl n'est pas disponible
        $normalized = strtr(utf8_decode($raw), 
            utf8_decode('àáâãäçèéêëìíîïñòóôõöùúûüýÿÀÁÂÃÄÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ'), 
            'aaaaaceeeeiiiinooooouuuuyyAAAAACEEEEIIIINOOOOOUUUUY');
        $normalized = utf8_encode($normalized);
    }
    // Retirer les marques de combinaison (Mn)
    $no_accents = preg_replace('/\p{Mn}/u', '', $normalized);
    // Remplacer les espaces par des tirets
    $no_spaces = preg_replace('/\s+/', '-', $no_accents);
    // Retirer tout caractère spécial non conforme
    return preg_replace('/[^a-zA-Z0-9_\-]/', '', $no_spaces);
}

// Fonction de chargement de la progression avec migration automatique
function load_progress($stats_file) {
    if (file_exists($stats_file)) {
        $raw = file_get_contents($stats_file);
        $data = json_decode($raw, true);
        if (!$data) return [];
        
        $pronouns_map = [
            "0" => "yo",
            "1" => "tu",
            "2" => "elella",
            "3" => "nosotros",
            "4" => "vosotros",
            "5" => "ellosellas"
        ];
        
        $migrated = [];
        $dirty = false;
        foreach ($data as $k => $v) {
            $sk = sanitize_key($k);
            
            // Check if key ends with __0, __1, etc.
            $parts = explode("__", $sk);
            if (count($parts) >= 2) {
                $last_part = end($parts);
                if (isset($pronouns_map[$last_part])) {
                    $parts[count($parts) - 1] = $pronouns_map[$last_part];
                    $sk = implode("__", $parts);
                    $dirty = true;
                }
            }
            
            if ($sk !== $k) {
                $dirty = true;
            }
            if (isset($migrated[$sk])) {
                $m_succ = isset($migrated[$sk]["success"]) ? $migrated[$sk]["success"] : 0;
                $v_succ = isset($v["success"]) ? $v["success"] : 0;
                $migrated[$sk]["success"] = $m_succ + $v_succ;

                $m_err = isset($migrated[$sk]["error"]) ? $migrated[$sk]["error"] : 0;
                $v_err = isset($v["error"]) ? $v["error"] : 0;
                $migrated[$sk]["error"] = $m_err + $v_err;

                $m_strk = isset($migrated[$sk]["streak"]) ? $migrated[$sk]["streak"] : 0;
                $v_strk = isset($v["streak"]) ? $v["streak"] : 0;
                $migrated[$sk]["streak"] = max($m_strk, $v_strk);

                if (isset($v["lastDate"])) {
                    if (!isset($migrated[$sk]["lastDate"]) || $v["lastDate"] > $migrated[$sk]["lastDate"]) {
                        $migrated[$sk]["lastDate"] = $v["lastDate"];
                        $migrated[$sk]["lastResult"] = isset($v["lastResult"]) ? $v["lastResult"] : null;
                    }
                }
            } else {
                $migrated[$sk] = $v;
            }
        }
        if ($dirty) {
            file_put_contents($stats_file, json_encode($migrated, JSON_UNESCAPED_UNICODE));
        }
        return $migrated;
    }
    return [];
}

// Helper pour récupérer l'aide de terminaison
function get_hint($hints, $mode, $tense, $pronoun_idx) {
    if (isset($hints[$mode][$tense][$pronoun_idx])) {
        return $hints[$mode][$tense][$pronoun_idx];
    }
    return "";
}

// Enrichir le verbe avec les aides dynamiques
function build_cards($verb_db, $hints, $verb_name) {
    if (!isset($verb_db[$verb_name])) {
        return [];
    }
    $verb = $verb_db[$verb_name];
    $result = [];
    foreach ($verb as $mode => $tenses) {
        $result[$mode] = [];
        foreach ($tenses as $tense => $cards) {
            $enriched = [];
            foreach ($cards as $i => $card) {
                $c = $card;
                if (!isset($c["hint"])) {
                    $c["hint"] = get_hint($hints, $mode, $tense, $i);
                }
                $enriched[] = $c;
            }
            $result[$mode][$tense] = $enriched;
        }
    }
    return $result;
}

// Load list of flagged phrase IDs to ignore
function load_flagged_phrases($flagged_file) {
    if (file_exists($flagged_file)) {
        $raw = file_get_contents($flagged_file);
        $data = json_decode($raw, true);
        if (is_array($data)) {
            return $data;
        }
    }
    return [];
}

// Save list of flagged phrase IDs
function save_flagged_phrases($flagged_file, $flagged_list) {
    file_put_contents($flagged_file, json_encode($flagged_list, JSON_UNESCAPED_UNICODE));
}

// Charger la base de données de verbes commune
if (!file_exists($verbs_data_file)) {
    header('HTTP/1.1 500 Internal Server Error');
    header('Content-Type: text/plain; charset=utf-8');
    echo "Fichier verbs_data.json manquant. Veuillez générer la base de données.";
    exit;
}
$verbs_data_content = file_get_contents($verbs_data_file);
$verbs_data = json_decode($verbs_data_content, true);
if ($verbs_data === null) {
    header('HTTP/1.1 500 Internal Server Error');
    header('Content-Type: text/plain; charset=utf-8');
    echo "Erreur de syntaxe JSON dans verbs_data.json : " . json_last_error_msg();
    exit;
}
$verb_db = isset($verbs_data['verbs_db']) ? $verbs_data['verbs_db'] : [];
$hints = isset($verbs_data['hints']) ? $verbs_data['hints'] : [];

// --- Routage de l'API ---

$action = isset($_GET['action']) ? $_GET['action'] : '';

// 1. API: Liste des verbes et progression globale
if ($action === 'data' || $uri === '/api/data') {
    $payload = [
        "verbs" => array_keys($verb_db),
        "progress" => load_progress($stats_file)
    ];
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
    header('Pragma: no-cache');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

// 2. API: Récupérer un verbe enrichi
if ($action === 'verb' || strpos($uri, '/api/verb/') === 0) {
    $verb_name = ($action === 'verb') ? (isset($_GET['name']) ? $_GET['name'] : '') : substr($uri, 10);
    $cards = build_cards($verb_db, $hints, $verb_name);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($cards, JSON_UNESCAPED_UNICODE);
    exit;
}

// 3. API: Enregistrer un vote (POST)
if ($action === 'vote' || ($uri === '/api/vote' && $_SERVER['REQUEST_METHOD'] === 'POST')) {
    if (!isset($body['id']) || !isset($body['vote'])) {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(["status" => "error", "message" => "Champs requis manquants."]);
        exit;
    }
    
    $key = $body['id'];
    $vote = $body['vote']; // 'success', 'error' ou 'reset'
    
    $progress = load_progress($stats_file);
    
    if ($vote === 'reset') {
        $entry = [
            "success" => 0, 
            "error" => 0, 
            "streak" => 0, 
            "lastDate" => null, 
            "lastResult" => null
        ];
    } else {
        $entry = isset($progress[$key]) ? $progress[$key] : [
            "success" => 0, 
            "error" => 0, 
            "streak" => 0, 
            "lastDate" => null, 
            "lastResult" => null
        ];
        $entry[$vote] = (isset($entry[$vote]) ? $entry[$vote] : 0) + 1;
        $entry["lastDate"] = gmdate('Y-m-d\TH:i:s\Z');
        $entry["lastResult"] = $vote;
        
        if ($vote === 'success') {
            $entry["streak"] = (isset($entry["streak"]) ? $entry["streak"] : 0) + 1;
        } else {
            $entry["streak"] = 0;
        }
    }
    
    $progress[$key] = $entry;
    file_put_contents($stats_file, json_encode($progress, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($entry, JSON_UNESCAPED_UNICODE);
    exit;
}

// 4. API: Réinitialisation générale (POST)
if ($action === 'reset_all' || ($uri === '/api/reset' && $_SERVER['REQUEST_METHOD'] === 'POST')) {
    file_put_contents($stats_file, json_encode([], JSON_UNESCAPED_UNICODE));
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(["status" => "ok"], JSON_UNESCAPED_UNICODE);
    exit;
}

// 4b. API: Reset series of day (POST)
if ($action === 'reset_day_series' || ($uri === '/api/reset_day_series' && $_SERVER['REQUEST_METHOD'] === 'POST')) {
    $progress = load_progress($stats_file);
    $today_str = gmdate('Y-m-d');
    
    // Remove all entries from today
    foreach ($progress as $k => $v) {
        if (isset($v["lastDate"]) && substr($v["lastDate"], 0, 10) === $today_str) {
            unset($progress[$k]);
        }
    }
    
    file_put_contents($stats_file, json_encode($progress, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(["status" => "ok"], JSON_UNESCAPED_UNICODE);
    exit;
}

// 5. API: Get flagged phrases list (GET)
if ($uri === '/flagged_phrases.json' || strpos($uri, '/flagged_phrases.json') === 0) {
    $flagged_list = load_flagged_phrases($flagged_file);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
    header('Pragma: no-cache');
    echo json_encode($flagged_list, JSON_UNESCAPED_UNICODE);
    exit;
}

// 6. API: Flag a phrase (POST)
if ($action === 'flag' || ($uri === '/api/flag' && $_SERVER['REQUEST_METHOD'] === 'POST')) {
    $phrase_id = isset($body['id']) ? $body['id'] : null;
    if ($phrase_id) {
        $flagged_list = load_flagged_phrases($flagged_file);
        if (!in_array($phrase_id, $flagged_list)) {
            $flagged_list[] = $phrase_id;
            save_flagged_phrases($flagged_file, $flagged_list);
        }
    }
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(["status" => "ok"], JSON_UNESCAPED_UNICODE);
    exit;
}

// 7. Accueil (Servir index.html)
if ($uri === '/' || $uri === '/index.php' || $uri === '/index.html' || strpos($uri, '/apprentissage.php') === 0) {
    header('Content-Type: text/html; charset=utf-8');
    readfile(__DIR__ . '/index.html');
    exit;
}

// Si la route n'est pas gérée, on renvoie une 404
header('HTTP/1.1 404 Not Found');
echo "Page non trouvée.";
exit;
