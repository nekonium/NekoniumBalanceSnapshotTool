<?php
ini_set('display_errors', 1);
ini_set('error_reporting', E_ALL);
require_once("../lib/db.php");

header('Content-Type: text/plain');
$pdo = new PDO('sqlite:./sbl.transaction.sqlite3');

$db=new SignedBalanceTransactionTable($pdo);
print_r($db->getTotal());
print_r($db->getList(10,0,"account",true));
print_r($db->getByAccount("0x62A87d9716b5826063d98294688ec76F774034d6"));