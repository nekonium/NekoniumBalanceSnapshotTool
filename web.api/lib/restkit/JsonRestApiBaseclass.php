<?php 

namespace restkit;
require_once(dirname(__FILE__).'/RequestHandler.php');

/**
 * JSONを返すRESTAPIのテンプレートとなるAbstractクラス。
 * 定型のResult形式で返す。
 * #execute関数で結果を返す。
 * #makeResult関数にJsonを構成するオブジェクトを返す関数を実装する。
 */
abstract class JsonRestApiBaseclass extends RequestHandler
{
    protected $version;
    /**
     * checkPermission関数でチェックするアクセス元ホスト名の配列を渡す。
     * @param string $permission
     */
    function __construct($version,$permission=null)
    {
        parent::__construct('application/json',$permission);
        $this->version=$version;
    }
    public function execute()
    {
        try{
            parent::execute();
            header('Access-Control-Allow-Origin:*');
            $result=$this->makeResult();
            $r=array(
                'version'=>$this->version,
                'success'=>true,
                'timestamp'=>time()*1000,
                'result'=>$result);
        } catch (\Exception|\Error $e) {
            $r=array(
                'version'=>$this->version,
                "success"=>false,
                "error"=>$e->getMessage(),
                'message'=>$e->getTraceAsString()
            );
        }
        return print(self::jsonEncode(isset($_GET['i']),$r));
    }
    /** 継承先でresultに設定するJSONを返すオブジェクトを構築してください。*/
    abstract protected function makeResult();
}

?>