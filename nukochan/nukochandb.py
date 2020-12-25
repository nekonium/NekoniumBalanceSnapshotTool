#%%
from enum import Enum
import os,sys
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
from libs import SqliteDb
import math
def toBlobUint(n):
    """uintをバイナリに変換
    """
    if n==0:
        return int.to_bytes(n,1,byteorder="big",signed=False)
    else:
        return int.to_bytes(n,int(1+math.log2(n)//8),byteorder="big",signed=False)

def fromBlobUint(n):
    """バイナリ文字列をuintへ変換
    """
    return int.from_bytes(n,byteorder="big",signed=False)

class NukoChanDb(SqliteDb):
    def __init__(self,path,isolation_level_='EXCLUSIVE',autocommit=True):
        super().__init__(path,isolation_level_,autocommit)

class BlockTable:
    _db:NukoChanDb
    def __init__(self,db:NukoChanDb,table_name="BlockTable"):
        self._db=db
        self.table_name=table_name
        pass
    def initTable(self):
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS {0}
            (`number` integer,gasUsed blob,miner integer,timestamp integer
            ,primary key(`number`))""".format(self.table_name))
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS {0}_IDX ON
            {0}(`number`,`miner`
            )""".format(self.table_name))
        return
    def select(self,sql:str,params:list):
        """{0}にテーブルを設定します。
        """
        return self._db.select(sql.format(self.table_name),params)
    def addBlocks(self,number_gasUsed_miner_timestamp_list:list):
        """ブロックを追加
        """
        d=[(i[0],toBlobUint(i[1]),i[2],i[3],)for i in number_gasUsed_miner_timestamp_list]
        self._db.executemany("INSERT INTO {0} (`number`,gasUsed,miner,timestamp)VALUES(?,?,?,?)".format(self.table_name),d)
    def addBlock(self,number:int,gasUsed:int,miner:int,timestamp:int):
        """ブロックを追加
        """
        try:
            self._db.execute("INSERT INTO {0} (`number`,gasUsed,miner,timestamp)VALUES(?,?,?,?)".format(self.table_name),[number,toBlobUint(gasUsed),miner,timestamp])
        except:
            print(number,gasUsed,miner,timestamp)
            print(type(number),type(gasUsed),type(miner),type(timestamp))
            raise
    def getLatest(self):
        return self._db.selectOne("SELECT max(`number`) FROM {0};".format(self.table_name))[0]
class UncleBlockTable:
    _db:NukoChanDb
    def __init__(self,db:NukoChanDb,table_name="UncleBlockTable"):
        self._db=db
        self.table_name=table_name
        pass
    def initTable(self):
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS {0}
            (id integer,`number` integer,pos integer,`uncleNumber` integer,gasUsed blob,miner integer,timestamp integer
            ,primary key(`id`),unique(`number`,pos))""".format(self.table_name))
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS {0}_IDX ON
            {0}(`number`,`miner`)""".format(self.table_name))
        return
    def select(self,sql:str,params:list):
        """{0}にテーブルを設定します。
        """
        return self._db.select(sql.format(self.table_name),params)
    def addBlocks(self,number_pos_uncleNumber_gasUsed_miner_timestamp_list:list):
        """ブロックを追加
        """
        d=[(i[0],i[1],i[2],toBlobUint(i[3]),i[4],i[5],)for i in number_pos_uncleNumber_gasUsed_miner_timestamp_list]
        self._db.executemany("INSERT INTO {0} (`number`,pos,uncleNumber,gasUsed,miner,timestamp)VALUES(?,?,?,?,?,?)".format(self.table_name),d)

    def addBlock(self,number:int,pos:int,uncleNumber:int,gasUsed:int,miner:int,timestamp:int):
        """ブロックを追加
        """
        try:
            self._db.execute("INSERT INTO {0} (`number`,pos,uncleNumber,gasUsed,miner,timestamp)VALUES(?,?,?,?,?,?)".format(self.table_name),[number,pos,uncleNumber,toBlobUint(gasUsed),miner,timestamp])
        except:
            raise



class AccountTable:
    class FoundIn(Enum):
        """AccountTableのアカウントの検出理由を示すの列挙値
        """
        GENESIS=1
        MINING=2
        TX_TO=3
        TX_FROM=4
        CONTRACT=5
        @staticmethod
        def toEnum(n:int):
            return [
                None,
                AccountTable.FoundIn.GENESIS,
                AccountTable.FoundIn.MINING,
                AccountTable.FoundIn.TX_TO,
                AccountTable.FoundIn.TX_FROM,
                AccountTable.FoundIn.CONTRACT][n]    
    _db:NukoChanDb
    def __init__(self,db:NukoChanDb,table_name="AccountTable"):
        self._db=db
        self.table_name=table_name
        pass
    def initTable(self):
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS {0}
            (id integer,account text,foundat integer,foundin integer
            ,primary key(id),unique(account))""".format(self.table_name))
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS {0}_IDX ON
            {0}(`account`
            )""".format(self.table_name))
        return
    def select(self,sql:str,params:list):
        """{0}にテーブルを設定します。
        """
        return self._db.select(sql.format(self.table_name),params)
    def getId(self,account):
        """アカウント文字列からIDを得る
        """
        return self._db.selectOne("SELECT id FROM {0} WHERE account=?;".format(self.table_name),[account])[0]
    def appendAccount(self,account:str,foundat:int,foundin:FoundIn):
        """追記登録。存在する場合は無視。
        """
        try:
            r=self._db.selectOne("SELECT id FROM {0} WHERE account=?;".format(self.table_name),[account])
            if r is None:
                self._db.execute("INSERT INTO {0} (account,foundat,foundin)VALUES(?,?,?)".format(self.table_name),[account,foundat,foundin.value])
            return
        except:
            print(account,foundat,foundin)
            print(type(account),type(foundat),type(foundin))
            raise
    def selectActiveAccounts(self,number:int):
        """ブロック番号numberの時点で存在するアカウントを全て列挙する
        """
        return [
            (i[0],i[1],i[2],AccountTable.FoundIn.toEnum(i[3]))
            for i in self._db.select("SELECT * FROM {0} WHERE foundat<=?;".format(self.table_name),[number])
        ]
class TransactionTable:
    _db:NukoChanDb
    def __init__(self,db:NukoChanDb,table_name="TransactionTable"):
        self._db=db
        self.table_name=table_name
        pass
    def initTable(self):
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS {0}
            (id integer,blockNumber integer,`from` integer,`to` integer,gas blob,gasPrice blob,value blob,gasUsed blob,cumulativeGasUsed blob
            ,primary key(id))""".format(self.table_name))
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS {0}_IDX ON
            {0}(`blockNumber`,`from`,`to`
            )""".format(self.table_name))            
        return
    def select(self,sql:str,params:list):
        """{0}にテーブルを設定します。
        """
        return self._db.select(sql.format(self.table_name),params)
    def addTransactions(self,blockNumber_from_to_gas_gasPrice_gasUsed_value_cumulativeGasUsed:list):
        d=[(i[0],i[1],i[2],toBlobUint(i[3]),toBlobUint(i[4]),toBlobUint(i[5]),toBlobUint(i[6]),toBlobUint(i[7]))for i in blockNumber_from_to_gas_gasPrice_gasUsed_value_cumulativeGasUsed]
        self._db.executemany("INSERT INTO {0} (blockNumber,`from`,`to`,gas,gasPrice,value,gasUsed,cumulativeGasUsed)VALUES(?,?,?,?,?,?,?,?)".format(self.table_name),d)
        return
    def addTransaction(self,blockNumber:int,from_:int,to_:int,gas:int,gasPrice:int,value:int,gasUsed:int,cumulativeGasUsed:int):
        """トランザクションを追記する。
        """
        self._db.execute("INSERT INTO {0} (blockNumber,`from`,`to`,gas,gasPrice,value,gasUsed,cumulativeGasUsed)VALUES(?,?,?,?,?,?,?,?)".format(self.table_name),[blockNumber,from_,to_,toBlobUint(gas),toBlobUint(gasPrice),toBlobUint(gasUsed),toBlobUint(value),value/1000000000000000000])
        return

class ContractTable:
    _db:NukoChanDb
    def __init__(self,db:NukoChanDb,table_name="ContractTable"):
        self._db=db
        self.table_name=table_name
        pass
    def initTable(self):
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS {0}
            (id integer,blockNumber integer,contract integer,`from` integer
            ,primary key(id),unique(contract))""".format(self.table_name))
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS {0}_IDX ON
            {0}(`blockNumber`,`contract`,`from`
            )""".format(self.table_name))           
        return
    def add(self,blockNumber:int,contract:int,from_:int):
        """トランザクションを追記する。
        """
        self._db.execute("INSERT INTO {0} (blockNumber,contract,`from`)VALUES(?,?,?)".format(self.table_name),[blockNumber,contract,from_])
        return
    def addContracts(self,blockNumber_contract_from:list):
        d=[(i[0],i[1],i[2])for i in blockNumber_contract_from]
        self._db.executemany("INSERT INTO {0} (blockNumber,`contract`,`from`)VALUES(?,?,?)".format(self.table_name),d)
        return

class BalanceSnapshotTable:
    _db:NukoChanDb
    def __init__(self,db:NukoChanDb,table_name="BalanceSnapshotTable"):
        self._db=db
        self.table_name=table_name
        pass
    def initTable(self):
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS {0}
            (id integer,blockNumber integer,account integer,`balance` blob,`fbalance` real
            ,primary key(id),unique(blockNumber,account))""".format(self.table_name))
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS {0}_IDX ON
            {0}(`blockNumber`,`account`
            )""".format(self.table_name))           
        return
    def add(self,blockNumber:int,account:int,balance:int):
        """トランザクションを追記する。
        """
        self._db.execute("INSERT INTO {0} (blockNumber,account,`balance`,`fbalance`)VALUES(?,?,?,?)".format(self.table_name),[blockNumber,contract,toBlobUint(balance),float(balance/1000000000000000000)])
        return
    def adds(self,blockNumber_account_balance:list):
        d=[(i[0],i[1],toBlobUint(i[2]),float(i[2]/1000000000000000000))for i in blockNumber_account_balance]
        self._db.executemany("INSERT INTO {0} (blockNumber,`account`,`balance`,`fbalance`)VALUES(?,?,?,?)".format(self.table_name),d)
        return


class MetadataTable:
    """name-valueペアのメタデータテーブル
    """
    _db:NukoChanDb
    def __init__(self,db:NukoChanDb,table_name="MetadataTable"):
        self._db=db
        self.table_name=table_name
        pass
    def initTable(self):
        self._db.execute("CREATE TABLE IF NOT EXISTS {0} (name text,value text,unique(name))".format(self.table_name))
        return
    def put(self,name:str,value:str):
        if self.get(name) is None:
            self._db.execute("INSERT INTO {0} VALUES (?,?)".format(self.table_name),[name,value])
        else:
            self._db.execute("UPDATE {0} SET value=? WHERE name=?".format(self.table_name),[value,name])
        return
    def putInt(self,name:str,value:int):
        self.put(name,str(value))
    def get(self,name:str,default=None):
        v=self._db.selectOne("SELECT value FROM {0} WHERE name=?".format(self.table_name),[name])
        return v[0] if v is not None else default
    def getInt(self,name:str,default:int=None)->int:
        v=self.get(name)
        return default if v is None else int(v)


#%%