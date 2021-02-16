<?php
/**
 * NukoPunckでエクスポートしたgenSignedBalanceListを参照するREST-API
 */

require_once('./_libs.php');
use restkit\JsonRestApiBaseclass;
use restkit\QueryParser;
ini_set('display_errors', 1);
ini_set('error_reporting', E_ALL);


/**
 * GET
 * Accountの情報を一件取得する。
 * 
 * Query
 * account
 * Ethereumアカウント
 * notx
 * キーが存在する場合、トランザクションを省略
 */
class AccountInfoApi extends JsonRestApiBaseclass
{
    const CFG_VERSION=APPVERSION.';AccountInfoApi/1.0.0;PHP';
    function __construct($permission=null){
        parent::__construct(self::CFG_VERSION,$permission);
    }
    protected function makeResult()
    {
        $pdo = new PDO(DBPATH);
        try{
            $account=QueryParser::get("account");
            $notx=QueryParser::has("notx");
            $tbl=new SignedBalanceTransactionTable($pdo);
            $a=$tbl->getByAccount($account,$notx);
            if($a===false){
                throw new Exception("Account not found.");
            }
            return $a;
        }catch(\Exception|\Error $e){
            $pdo=null;
            throw $e;
        }
    }
}



try {
    $t=new AccountInfoApi();
    $t->execute();
} catch (Exception $e) {
    http_response_code( 400 ) ;
    print("ERR");

    
}




?>