<?php
/**
 * NukoPunckでエクスポートしたgenSignedBalanceListを参照するREST-API
 * URLパラメータ
 * limit 返却行数の最大値
 * order 返却値の並び順
 * [account,amount]
 * page ページ番号
        page:int
    notx トランザクションを省略する場合
戻り値
    {
        version:str,
        created_date:str,
        list:[
            [account,amount,amount_nuko,tx]
        ]

    }
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
 * limit
 * Ethereumアカウント
 * notx
 * キーが存在する場合、トランザクションを省略
 */
class AccountInfoApi extends JsonRestApiBaseclass
{
    const CFG_VERSION=APPVERSION.';AccountListApi/1.0.0;PHP';
    function __construct($permission=null){
        parent::__construct(self::CFG_VERSION,$permission);
    }
    protected function makeResult()
    {
        $pdo = new PDO(DBPATH);
        try{
            $tbl=new SignedBalanceTransactionTable($pdo);
            $total=$tbl->getTotal();

            $limit=QueryParser::optInt("limit",10);
            $limit=max(0,min($limit,500));

            $pages=(int)(($total+$limit-1)/$limit);


            $page=QueryParser::optInt("page",0);
            $page=max(0,min($pages-1,$page));
            $order=QueryParser::opt("order","account");
            if(!in_array($order,array("account","id","amount","amount_nuko"))){
                throw new Exception("Invalid order key.");
            }
            $notx=QueryParser::has("notx");
            $a=$tbl->getList($limit,$page*$limit,$order,$notx);
            return array(
                "pages"=>array(
                    "total"=>$pages,
                    "page"=>$page,
                ),
                "total"=>$total,               
                "list"=>$a);
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