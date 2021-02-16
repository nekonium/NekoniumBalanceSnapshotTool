<?php

class SignedBalanceTransactionTable
{
    private $name;
    private $pdo;
    private $insert_ps;
    function __construct($i_pdo,$i_name="SignedBalanceTransactionTable")
    {
        $this->pdo=$i_pdo;
        $this->name=$i_name;
        $pdo=$this->pdo;
    }
    public function init(){
        throw new Exception("Read only database!");
    }
    public function getAll()
    {
        $pdo=$this->pdo;
        $stmt=$pdo->query('SELECT * FROM '.$this->name);
        try{
            $p=array();
            foreach ($stmt->fetchAll(PDO::FETCH_NUM) as $i){
                $p[$i[0]]=$i[1];
            }
            return $p;
        }finally{
        }
    }
    public function getTotal()
    {
        $pdo=$this->pdo;
        $stmt=$pdo->prepare('SELECT count(id) FROM '.$this->name);
        $r=$stmt->execute();
        if($r===false){
            throw new Exception('');
        }
        $v=$stmt->fetchAll(PDO::FETCH_NUM);
        return $v[0][0];
    }
    /**
     * order "account","amount","amount_nuko"
     */
    public function getList($limit=100,$offset=0,$order="account",$notx=false)
    {
        $pdo=$this->pdo;
        $stmt=null;
        if($notx){
            $stmt=$pdo->prepare('SELECT id,account,amount,amount_nuko FROM '.$this->name. ' ORDER BY '.$order.' LIMIT ?,?');
        }else{
            $stmt=$pdo->prepare('SELECT * FROM '.$this->name. ' ORDER BY '.$order.' LIMIT ?,?');
        }
        $r=$stmt->execute(array($offset,$limit));    
        if($r===false){
            throw new Exception('');
        }
        $v=$stmt->fetchAll(PDO::FETCH_NUM);        
        for($i=0;$i<count($v);$i++){
            $v[$i][0]=(int)($v[$i][0]);
            $v[$i][3]=(double)$v[$i][3];
        }
        return $v;
    }
    public function getByAccount($account,$notx=false)
    {
        $pdo=$this->pdo;
        $stmt=null;
        if($notx){
            $stmt=$pdo->prepare('SELECT id,account,amount,amount_nuko FROM '.$this->name. ' WHERE account=?');
        }else{
            $stmt=$pdo->prepare('SELECT * FROM '.$this->name.' WHERE account=?');
        }
        
        $r=$stmt->execute(array($account));
        if($r===false){
            throw new Exception('');
        }
        $v=$stmt->fetch(PDO::FETCH_NUM);
        if($v!==false){
            $v[0]=(int)($v[0]);
            $v[3]=(double)$v[3];
        }
        return $v;
    }

}

?>