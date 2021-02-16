
<?php
require_once '../_libs.php';

require_once("../lib/db.php");
header('Content-Type: text/plain');
$mk=Markets::getInstance()->getByMarketName("BitflyerLightning_FX_BTC_JPY");
$sm=$mk->srcDbPath();
$pdo = new PDO('sqlite:'.$sm);
$pdo->beginTransaction();        
$tbl=new OhlcvExDb($pdo,'ohlcvex');


$time_start = microtime(true);
for($i=0;$i<10;$i++){
    $stmt = $pdo->prepare("SELECT MAX(tid),MIN(tid) FROM ohlcvex_tid");
    $stmt->execute();    
}
$time = microtime(true) - $time_start;
echo "{$time} 秒\n";


$time_start = microtime(true);
for($i=0;$i<10;$i++){
    $stmt = $pdo->prepare("SELECT MAX(tid) FROM ohlcvex_tid UNION SELECT MIN(tid) FROM ohlcvex_tid");
    $stmt->execute();    
}
$time = microtime(true) - $time_start;
echo "{$time} 秒\n";