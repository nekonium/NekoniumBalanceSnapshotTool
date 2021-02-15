"""署名付き残高の生成ツール

init     残高データベースから署名なしリストを生成
sign     証明アカウントで残高に署名を追加
export   トランザクションリストを生成
    トランザクションリストはこのツールチェインの最終出力データです。
    これは、アカウントとそのメタデータ、残高生成トランザクションのリストです。

"""
#%%
from web3 import Web3
from eth_account.messages import encode_defunct



# %%
from typing import Union
import argparse
import datetime
import json
from tqdm import tqdm
import time
import os,sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from nukochan import AccountTable as _AccountTable,BalanceSnapshotTable,fromBlobUint,NukoChanDb
class AccountTable(_AccountTable):
    def __init__(self,db,tn=None):
        super().__init__(db)
    # def getListBeforeBlockNumber(self,number:int):
    #     """ブロック番号numberの時点で存在するアカウントを全て列挙する
    #     """
    #     return self._db.select("SELECT * FROM {0} WHERE foundat<=?;".format(self.table_name),[number])
# %%



class BalanceCertificationData:
    """
    アカウントアドレスaccountについて、ブロック高height数量amountの残高証明書を格納するクラス。
    height uint 32(4)
    amount uint 96(12)
    message str 128(16)
    """
    _hex:bytes #20+(4+12+16)=52バイトの残高識別値
    _signedHash:list #署名のバイナリ配列
    def __init__(self,account,height,amount,message,signedhash=None):
        def encodeStr(s:str,l:int):
            r=s.encode()
            while len(r)<l:
                r=r+b"\0"
            assert(len(r)<=l)
            return r
        account_=Web3.toBytes(hexstr=Web3.toChecksumAddress(account))
        height_=int.to_bytes(height,4,byteorder="big",signed=False)
        amount_=int.to_bytes(amount,12,byteorder="big",signed=False)
        message_=encodeStr(message,16)
        self._hex=account_+height_+amount_+message_
        self._signedHash=[] if signedhash is None else signedhash
    @property
    def account(self)->str:
        return Web3.toChecksumAddress(Web3.toHex(self._hex[0:20]))
    @property
    def height(self)->int:
        return int.from_bytes(self._hex[20:24],byteorder="big",signed=False)
    @property
    def balance(self)->int:
        return int.from_bytes(self._hex[24:36],byteorder="big",signed=False)
    @property
    def message(self)->str:
        return self._hex[36:].decode('utf-8')
    @property
    def hex(self)->bytes:
        return self._hex
    @property
    def signedHash(self)->list:
        return self._signedHash
    def appendSign(self,web3,proof_account:str):
        """署名を追記する。
        """
        a=web3.toChecksumAddress(proof_account)
        s=web3.eth.sign(a,data=self._hex)
        self._signedHash.append(bytes(s))
    def checkSign(self,web3,accounts:list):
        """署名リストを検証する
        signedHash[n]が、sign(x,account[n])と等しいか確認
        """
        assert(len(accounts)==len(self._signedHash))
        for a,s in zip(accounts,self._signedHash):
            message = encode_defunct(hexstr=Web3.toHex(self.hex))
            ac=web3.eth.account.recover_message(message, signature=Web3.toHex(s))
            if ac!=a:
                return False
        return True






#%%

"""
    {
        version:str,
        created_date:int,
        params:{
            signer:[[str,date]...],
            height:int
            message:str
        }
        balances:[
        ],
    }
"""
class BalanceCertifications:

    VERSION="BalanceCertification/0.1"
    _balances:list #[account,balances,type,[sign],...]

    def __init__(self,params:dict,balances:list):
        
        self._params=params
        self._balances=balances
    def appendSign(self,web3:Web3,proof_account:str,password=None,progress=True):
        """残高に署名を追加する
        署名が追加できればTrue/出来なければFalse
        """
        pa=Web3.toChecksumAddress(proof_account)
        if pa in self._params["proofAccounts"]:
            raise Exception("{0} is already exist in proofAccounts.".format(pa))
        self._params["proofAccounts"].append(pa)
        if password is not None:
            web3.geth.personal.unlock_account(pa,password)
        for i in (self._balances if progress==False else tqdm(self._balances)):
            i.appendSign(web3,pa)
        return True
    @classmethod
    def ganerateList(cls,db,height,message="",progress=False):
        b=BalanceSnapshotReader(db)
        l=b.getBalanceSnapshot(height)
        p={
            "proofAccounts":[],
            "height":l["height"],
            "message":message,
        }
        return BalanceCertifications(p,
            [BalanceCertificationData(i[0],l["height"],i[1],message) for i in (l["balances"] if progress==False else tqdm(l["balances"]))]
        )

    @classmethod
    def dumpToDict(cls,inst):
        j={
            "version":cls.VERSION,
            "created_date":str(datetime.datetime.now()),
            "params":inst._params,
            "balances":[(
                i.account,
                i.balance,
                Web3.toHex(i.hex),
                [Web3.toHex(j) for j in i.signedHash]) for i in inst._balances]
        }
        return j
    @classmethod
    def validateParams(cls,p):
        for i in ["proofAccounts","height","message"]:
            if i not in p:
                raise Exception("{0} is not exists in params.".format(i))
        for i in p["proofAccounts"]:
            if not Web3.isChecksumAddress(i):
                raise Exception("{0} is not checksum account.".format(i))
        if type(p["height"])!=int:
            raise Exception("height is not int.")
        return

    @classmethod
    def loadFromDict(cls,web3:Web3,d):
        """値を検証しながらJsonから読みだす。
        """
        if d["version"]!=cls.VERSION:
            raise Exception("Invalid version")
        p=d["params"]
        cls.validateParams(p)
        b=[BalanceCertificationData(
            i[0],
            p["height"],
            i[1],
            p["message"],
            [Web3.toBytes(hexstr=j)for j in i[3]]) for i in d["balances"]]
        for i,j in zip(b,d["balances"]):
            if Web3.toHex(i.hex)!=j[2]:
                #HEXが不正な構成
                raise Exception("{0} invalid hex.".format(i.account))
            if not i.checkSign(web3,p["proofAccounts"]):
                #サインが一致しない
                raise Exception("{0} invalid signeture.".format(i.account))
        return BalanceCertifications(p,b)

class SignedBalanceTransactionTable:
    """
    exportでsqlite3フォーマットを出力するときに使うテーブル
    """
    _db:NukoChanDb
    def __init__(self,db:NukoChanDb,table_name="SignedBalanceTransactionTable"):
        self._db=db
        self.table_name=table_name
        pass
    def initTable(self):
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS {0}
            (id integer,account text,amount text,amount_nuko real,`transaction` text,
            primary key(id),unique(account))
            """.format(self.table_name)
        )
        return
    def put(self,account:str,amount:int,transaction:str):
        self._db.execute("INSERT INTO {0}(account,amount,amount_nuko,`transaction`) VALUES (?,?,?,?)".format(self.table_name)
            ,[account,str(int(amount)),amount/1000000000000000000,transaction])
        return
    # def get(self,account:str,default=None):
    #     v=self._db.selectOne("SELECT * FROM {0} WHERE account=?".format(self.table_name),[account])
    #     return v[0] if v is not None else default
#%%

import argparse
import datetime
import json
from tqdm import tqdm
import time
import urllib.parse
from nukochan import *
import json
import csv





def main_init(args):
    print(args)
    a=NukoChanDb(args.db)
    inst=BalanceCertifications.ganerateList(a,args.height,args.message,progress=True)
    with open(args.out,"w") as fp:
        json.dump(BalanceCertifications.dumpToDict(inst),fp,indent=2)
    return
def main_sign(args):
    d=None
    with open(args.json,"r") as fp:
        d=json.load(fp)
    url=urllib.parse.urlparse(args.rpc)
    providers={"http":Web3.HTTPProvider,"https":Web3.HTTPProvider,"ws":Web3.WebsocketProvider,"wss":Web3.WebsocketProvider,"ipc":Web3.IPCProvider}
    if url.scheme not in providers:
        raise Exception("Bad RPC Scheme")
    w3=Web3(providers[url.scheme](args.rpc if url.scheme!="ipc" else url.path))
    b=BalanceCertifications.loadFromDict(w3,d)
    b.appendSign(w3,args.account,args.password,progress=True)
    with open(args.json,"w") as fp:
        json.dump(BalanceCertifications.dumpToDict(b),fp,indent=2)
def main_export(args):
    with open(args.json,"r") as fp:
        d=json.load(fp)
    #JSON用のdictを生成
    src={
        'version':"SignedBalanceList/0.1;"+d["version"],
        'created_date':d["created_date"],
        'params':{
            'snapshotHeight':d["params"]["height"],
            'proofAccounts':d["params"]["proofAccounts"],
            'lowerLimit':args.lowerLimit,
            'accounts':{
                'total':len(d["balances"]),
                'active':None,
                'drop':None
            }
        },
        'transactions':[]
    }
    enable=[]
    disable=[]
    for i in tqdm(d["balances"]):
        s=Web3.toBytes(hexstr=i[2])
        for j in i[3]:
            s=s+Web3.toBytes(hexstr=j)
        mv=str(i[1]%1000000000000000000)
        #account,wie,transaction
        w=[i[0],i[1],Web3.toHex(s)]
        if i[1]>=args.lowerLimit:
            enable.append(w)
        else:
            disable.append(w)
    src["params"]["accounts"]["active"]=len(enable)
    src["params"]["accounts"]["drop"]=len(disable)
    src["transactions"]=enable
    
    if args.format=="csv":
        fname="./sbl.transaction.csv" if args.out is None else args.out
        with open(fname, 'w', newline='') as fp:
            fp = csv.writer(fp, delimiter='\t',quotechar='"', quoting=csv.QUOTE_MINIMAL)
            fp.writerow(['version','created_date'])
            fp.writerow([src["version"],src['created_date']])

            fp.writerow(['params'])
            fp.writerow(['snapshotHeight',src["params"]["snapshotHeight"]])
            fp.writerow(['proofAccounts']+src["params"]["proofAccounts"])
            fp.writerow(['lowerLimit',src["params"]["lowerLimit"]])

            fp.writerow(['accounts'])
            fp.writerow(['total','active','drop'])
            fp.writerow([src["params"]["accounts"]["total"],src["params"]["accounts"]["active"],src["params"]["accounts"]["drop"]])

            fp.writerow(['transactions'])
            fp.writerow(['account','balance(NUKO)','balance(wie)',"transaction"])
            for i in src["transactions"]:
                fp.writerow([i[0],i[1]/1000000000000000000,i[1],i[2]])
    elif args.format=="json":
        fname="./sbl.transaction.json" if args.out is None else args.out
        with open(fname,"w") as fp:
            json.dump(src,fp,indent=2)
    elif args.format=="sqlite3":
        fname="./sbl.transaction.sqlite3" if args.out is None else args.out
        with NukoChanDb(fname,autocommit=False) as db:
            try:
                meta=MetadataTable(db)
                meta.initTable()
                txs=SignedBalanceTransactionTable(db)
                meta.put("version",src["version"])
                meta.put("created_date",str(src['created_date']))
                meta.putInt("snapshotHeight",src["params"]["snapshotHeight"])
                meta.put("proofAccounts",",".join(src["params"]["proofAccounts"]))
                meta.putInt("lowerLimit",src["params"]["lowerLimit"])
                meta.putInt("accounts_total",src["params"]["accounts"]["total"])
                meta.putInt("accounts_active",src["params"]["accounts"]["active"])
                meta.putInt("accounts_drop",src["params"]["accounts"]["drop"])
                txs.initTable()
                for i in src["transactions"]:
                    txs.put(i[0],i[1],i[2])
                db.commit()
            except:
                db.rollback()
                print("Rollbacked!")
                raise
    else:
        raise Exception("bad format")

def main():
    """
        署名付き残高スナップショットJSONの生成ツール。
        残高証明リストの生成、トランザクションのエクスポートができます。


        genSignedBalanceList init nekonium_acounts.sqlite3 1000 --message MESSAGE
        genSignedBalanceList sign --json sbl.json --account Account
        genSignedBalanceList export ./sbl.json --format json --lowerLimit 1

        exportが生成するトランザクションは、それぞれのアカウントの残高メッセージ(52byte)にsignedHash(64byte)をすべて連結した値です。
    """
    FNAME=""
    parser = argparse.ArgumentParser(prog='Nekonium signed balance list tool.')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_init = subparsers.add_parser('init', help="Generate inital")
    parser_init.add_argument('db', type=str, help='Source sqlite database file path')
    parser_init.add_argument('height', type=int, help='Target block height')
    parser_init.add_argument('--message', type=str, help='Message text',default="")
    parser_init.add_argument('--out', type=str, default="./sbl.json")
    parser_init.set_defaults(func=main_init)


    parser_init = subparsers.add_parser('sign', help="Signe to each balances")
    parser_init.add_argument('json', type=str,help='BalanceCertification format Json path')
    parser_init.add_argument('account', type=str,help="proof account.Must exist on clients.")
    parser_init.add_argument('--password', type=str, default=None,help="Proof account password for unlock.")
    parser_init.add_argument('--rpc', type=str, default="http://127.0.0.1:8293")
    parser_init.set_defaults(func=main_sign)

    parser_init = subparsers.add_parser('export', help="Signe each balances")
    parser_init.add_argument('json', type=str,help='Source BalanceCertification format Json path')
    parser_init.add_argument('--format', type=str, choices=["json","csv","sqlite3"],default="json",help="Output file format")
    parser_init.add_argument('--lowerLimit', type=int, default=0,help="Lower limit in wie")
    parser_init.add_argument('--out', type=str,help="transaction file name",default=None)
    parser_init.set_defaults(func=main_export)




    #T1="init nekonium_accounts.sqlite3-2 1000 --message MESSAGE".split(" ")
    #T1="sign ./sbl.json 0xe9b2857fd2500157122924efa5045a118d797a77 --rpc ipc:/home/nyatla/.nekonium/gnekonium.ipc --password ".split(" ")
    #T1="export ./sbl.json --format json --lowerLimit 1".split(" ")
    args=parser.parse_args()
    args.func(args)
    print("finished.")

if __name__ == "__main__":
    main()

#%%