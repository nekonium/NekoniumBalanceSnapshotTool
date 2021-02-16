<?php 

namespace restkit;

use Exception;

abstract class RequestHandler
{
    private $content_type;
    private $permission;
    /**
     * checkPermission関数でチェックするアクセス元ホスト名の配列を渡す。
     * @param string $permission
     */
    function __construct($content_type='*/*',$permission=null){
        $this->permission=$permission;
        $this->content_type=$content_type;
    }
    private function checkPermission(){
        //空の値ならなにもしない。
        if(!isset($this->permission)){
            return;
        }
        if(!in_array($_SERVER['REMOTE_ADDR'],$this->permission)){
            throw new Exception("Permission denied.");
        }
    }
    public function execute()
    {
        header('Content-Type: '.$this->content_type);
        $this->checkPermission();
    }
    /**
     * オブジェクトをJSONエンコードします。
     */
    protected static function jsonEncode($indent=false,$src)
    {
        $serialize_precision = ini_get('serialize_precision');
        $flag=JSON_UNESCAPED_SLASHES;
        if($indent){
            $flag|=JSON_PRETTY_PRINT;
        }
        try{
            ini_set('serialize_precision', '-1');
            return json_encode($src,$flag);
        }finally{
            ini_set('serialize_precision', $serialize_precision);
        }            
    }

}

?>