"""NUKOチェーンから任意ブロックに存在する全アドレスの残高スナップショットを生成する。
データベースの口座は同期されていること。


[blockNumber],[address],[balance]

"""
#%%
from web3 import Web3




# %%

from typing import Union
from collections.abc import Callable
import argparse
import datetime
import json
from tqdm import tqdm
import time
import urllib
import os,sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from nukochan import AccountTable as _AccountTable,NukoChanDb,BalanceSnapshotTable,MetadataTable
class AccountTable(_AccountTable):
    def __init__(self,db,tn=None):
        super().__init__(db)

# %%




#%%



#%%
if __name__ == "__main__":
    """
    """
    FNAME=""
    parser = argparse.ArgumentParser(description="Nekonium balance snapshot utility")
    parser.add_argument('db', help='データベース名',type=str,default="./nekonium_accounts.sqlite3")
    parser.add_argument('block', help='スナップショットを記録するブロック番号',type=int,default=None)
    parser.add_argument('--rpc', help='RPCサーバのアドレス(ipc,http,ws)',type=str,default="http://127.0.0.1:8293")
    parser.add_argument('--out', help='出力ファイル名',type=str,default=None)
    parser.add_argument('--format', help='出力形式',choices=["sqlite","json","console"],type=str,default="console")
    args=parser.parse_args()
    # args=parser.parse_args("0 --close 10000".split(" "))
    print(args)
    url=urllib.parse.urlparse(args.rpc)
    providers={"http":Web3.HTTPProvider,"https":Web3.HTTPProvider,"ws":Web3.WebsocketProvider,"wss":Web3.WebsocketProvider,"ipc":Web3.IPCProvider}
    if url.scheme not in providers:
        raise Exception("Bad RPC Scheme")
    web3=Web3(providers[url.scheme](args.rpc if url.scheme!="ipc" else url.path))


    def read(db,web3,number,callback=None):
        meta=MetadataTable(db)
        target_block=meta.getInt("NextAccountScanTarget",0)
        if target_block<=number:
            raise Exception("Out of sync block number")

        atbl=AccountTable(db)
        l=atbl.selectActiveAccounts(args.block)
        STEP=100
        pbar = tqdm(total=len(l))
        a=[]
        for n in range(len(l)):
            a.append((l[n],web3.eth.getBalance(l[n][1],number)))
            n=n-1
            pbar.update(1)
            if n%STEP==0:
                if callback is not None:
                    callback(a)
                    a=[]
        if len(a)>0:
            pbar.update(len(a))
            if callback is not None:
                callback(a)
                a=[]
        pbar.close()
        return a
    def _console():
        with NukoChanDb(args.db,autocommit=False) as db:
            print(read(db,web3,args.block))
    def _json():
        with NukoChanDb(args.db,autocommit=False) as db:
            j={
                "version":"balanceSnapshot/0.1;KONUKO",
                "created_date:":str(datetime.datetime.now()),
                "args":args.__dict__,
                "results":read(db,web3,args.block)
            }
            out=args.out if args.out is not None else "./balance_snapshot.json"
            with open(out,"w") as fp:
                json.dump(j,fp,indent=2,default=str)
    def _sqlite():
        """sqliteの場合は追記のみ可能。
        """
        out=args.out if args.out is not None else args.db
        r=None
        with NukoChanDb(args.db,autocommit=False) as db:
            r=read(db,web3,args.block)
        with NukoChanDb(out,autocommit=False) as db:
            try:
                atbl=AccountTable(db)
                btbl=BalanceSnapshotTable(db)
                btbl.initTable()
                d=[]
                for i in r:
                    d.append((
                        args.block, #block
                        i[0][0], #AccountId
                        i[1] #balance
                    ))
                btbl.adds(d)
                db.commit()
            except:
                db.rollback()
                print("Rollbacked.")
                raise
            pass
    {"sqlite":_sqlite,"json":_json,"console":_console}[args.format]()
    

#%%
