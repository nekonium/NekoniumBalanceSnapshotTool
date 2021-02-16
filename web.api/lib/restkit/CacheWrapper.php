<?php 

namespace restkit;
require_once(dirname(__FILE__).'/RequestHandler.php');

abstract class CacheWrapper extends RequestHandler
{
    /**
     * checkPermission関数でチェックするアクセス元ホスト名の配列を渡す。
     * @param string $permission
     */
    function __construct($content_type,$hash,$permission=null,$cache_path=null)
    {
        parent::__construct($content_type,$permission);
        $this->hash=$hash;
        $this->cache_path=$cache_path;
    }
    /**
     * URLに合致するコンテンツを取得します。
     */
    public function curlGetTextContent($url){
        $option = [
            CURLOPT_RETURNTRANSFER => true, //文字列として返す
            CURLOPT_TIMEOUT        => 3, // タイムアウト時間
        ];
        $ch = curl_init($url);
        curl_setopt_array($ch, $option);
        $text    = curl_exec($ch);
        $info    = curl_getinfo($ch);
        $errorNo = curl_errno($ch);
        // OK以外はエラーなので空白配列を返す
        if ($errorNo !== CURLE_OK) {
            throw new \Exception("Curl error ${errorNo}");
        }
    
        // 200以外のステータスコードは失敗とみなし空配列を返す
        if ($info['http_code'] !== 200) {
            throw new \Exception("Curl error Status=".$info['http_code']);
        }
        return $text;       
    }

    public function execute()
    {
        parent::execute();
        $filename=$this->cache_path.$this->hash.'.cache';
        //hash文字列に合致するファイルを探す。
        if(file_exists($filename)){
            //何もしない
        }else{
            file_put_contents($filename,$this->makeContent(),LOCK_EX);
        }
        $content = file_get_contents($filename);
        print($content);
    }
    /** 
     * 継承先でresultに設定するJSONを返すオブジェクトを構築してください。
     * 失敗したらexception
     */
    abstract protected function makeContent();
}
