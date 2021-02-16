<?php 

namespace restkit;

use Exception;


class QueryParser{
    /**
     * $nameにキーのクエリを取得する
     */
    public static function get($name){
        if(!isset($_GET[$name])){
            throw new Exception($name.' is not exist.');
        }
        return $_GET[$name];
    }
    /**
     * $nameのキーがクエリに存在するかを返す。
     */
    public static function has($name){
        if(!isset($_GET[$name])){
            return false;
        }
        return true;
    }

    /**
     * $nameにキーのクエリを取得する。存在しない場合は$defaultをかえす
     */
    public static function opt($name,$default){
        if(!isset($_GET[$name])){
            return $default;
        }
        return $_GET[$name];
    }
    /***
     * YYYYMMDD文字列をDateTimeとして返します。
     */
    public static function getYYYYMMDD($name){
        //date_default_timezone_set('Asia/Tokyo');
        $s=self::get($name);
        if(!preg_match("/^[0-9]{8}$/",$s)){
            throw new Exception('Invalid YYYYMMDD.');
        }
        return new \DateTimeImmutable($s);
    }
    public static function optYYYYMMDD($name,$default)
    {
        if(!isset($_GET[$name])){
            return $default;
        }
        return self::getYYYYMMDD($name);
                
    }
    public static function getInt($name){
        //date_default_timezone_set('Asia/Tokyo');
        $s=self::get($name);
        if(!preg_match("/^[0-9]+$/",$s)){
            throw new Exception('Invalid Integer.');
        }
        return intval($s);
    }
    public static function optInt($name,$default){
        //date_default_timezone_set('Asia/Tokyo');
        $s=self::opt($name,$default);
        if(!preg_match("/^[0-9]+$/",$s)){
            throw new Exception('Invalid Integer.');
        }
        return intval($s);
    }

}