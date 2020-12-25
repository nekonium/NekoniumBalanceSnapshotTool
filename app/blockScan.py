"""NUKOチェーンからブロックリスト、アドレスリスト、トランザクションリスト、アンクルリスト、コントラクトリストを生成する。



"""
#%%
from web3 import Web3




# %%
import os,sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import argparse
import datetime
import json
from tqdm import tqdm
import time
import urllib.parse
from nukochan import *





#%%
if __name__ == "__main__":
    """
        0から1000ブロック目までを探索して結果を表示する。
            # python3 blockScan.py 0 --close 1000 --format console
        0から1000ブロック目までを探索して結果をJSONへ返す。
            # python3 blockScan.py 0 --close 1000 --format json
        0から最後までのブロックを探索してデータベースへ蓄積する。
            # python3 blockScan.py 0 --format sqlite
    
    sqlite以外のパラメータは探索範囲の始点を指定できます。結果は探索範囲内での結果です。
    sqliteパラメータの場合は必ずブロック0から探索します。結果はブロック0から探索の終了したブロックまでです。
    """
    FNAME=""
    parser = argparse.ArgumentParser(description="Nekonium Address list generator")
    parser.add_argument('open', help='探索開始位置',type=int,default=0)
    parser.add_argument('--close', help='探索ブロックの終点',type=int,default=None)
    parser.add_argument('--format', help='出力形式',choices=["sqlite","json","csv","console"],type=str,default="console")
    parser.add_argument('--out', help='出力ファイル名',type=str,default=None)
    parser.add_argument('--rpc', help='RPCサーバのアドレス(ipc,http,ws)',type=str,default="http://127.0.0.1:8293")
    args=parser.parse_args()
    # args=parser.parse_args("0 --close 10000".split(" "))
    print(args)    


    def read(open_,close_,callback=None):
        url=urllib.parse.urlparse(args.rpc)
        providers={"http":Web3.HTTPProvider,"https":Web3.HTTPProvider,"ws":Web3.WebsocketProvider,"wss":Web3.WebsocketProvider,"ipc":Web3.IPCProvider}
        if url.scheme not in providers:
            raise Exception("Bad RPC Scheme")
        nt=NukoBlockReader(Web3(providers[url.scheme](args.rpc if url.scheme!="ipc" else url.path)))
        # nt=NukoScan(Web3.IPCProvider('./path/to/gnekonium.ipc'))
        s=open_
        e=(close_ if close_ is not None else nt.latestBlockNumber)
        if s>=e:
            raise Exception("Nothing to do")
        print("探索ブロック高 {0}->{1}".format(s,e))
        #100ブロックづつ探す
        STEP=100
        remaining=e-s
        n=((e-s+STEP-1)//STEP)
        pbar = tqdm(total=(e-s))
        results={}
        for i in range(n):
            b=s+i*STEP
            nob=min(remaining,STEP)
            pbar.update(nob)
            r=nt.scanBlock(b,b+nob)
            remaining=remaining-STEP
            for i in r:
                if i in results:
                    continue
                results[i]=r[i]
            if callback is not None:
                #コールバックがあるならちょっとづつ送る
                callback(results,b,b+nob)
                results={}
        pbar.close()
        return results
    def _console():
        print(read(args.open,args.close))
    def _json():
        j={
            "version":"blockScan/0.2;KONUKO",
            "created_date:":str(datetime.datetime.now()),
            "args":args.__dict__,
            "results":read(args.open,args.close)
        }
        out=args.out if args.out is not None else "./account_list.json"
        with open(out,"w") as fp:
            json.dump(j,fp,indent=2, default=str)
    def _sqlite():
        """sqliteの場合は追記のみ可能。
        """
        if args.close is not None or args.open!=0:
            print("sqliteが出力先の場合はopenを無視します。")
        out=args.out if args.out is not None else "./nekonium_accounts.sqlite3"
        with NukoChanDb(out,autocommit=False) as db:
            try:
                meta=MetadataTable(db)
                meta.initTable()
                atbl=AccountTable(db)
                atbl.initTable()
                btbl=BlockTable(db)
                btbl.initTable()
                ttbl=TransactionTable(db)
                ttbl.initTable()
                utbl=UncleBlockTable(db)
                utbl.initTable()
                ctbl=ContractTable(db)
                ctbl.initTable()
                target_block=meta.getInt("NextAccountScanTarget",0)
                print("AccountScanBlock={0}".format(target_block))
                def callback(r,s,e):
                    #アドレスの書き込み
                    for k,v in r["addresses"].items():
                        atbl.appendAccount(k,v[0],v[1])
                    #ブロックの書き込み
                    bq=[]
                    tq=[]
                    uq=[]
                    cq=[]
                    for v in r["blocks"]:
                        miner=atbl.getId(v[2])
                        assert(miner is not None)
                        # btbl.addBlock(v[0],v[1],miner,v[3])
                        bq.append((v[0],v[1],miner,v[3]))
                        #トランザクションの書き込み
                        for t in v[5]:
                            _from=atbl.getId(t[0])
                            _to=None if t[1] is None else atbl.getId(t[1])
                            #ttbl.addTransaction(v[0],_from,_to,t[2],t[3],t[4],t[5])
                            tq.append((v[0],_from,_to,t[2],t[3],t[4],t[5],t[6]))
                        #uncleの書き込み
                        up=0
                        for u in v[6]:
                            miner=atbl.getId(u[2])
                            #utbl.addBlock(v[0],up,u[0],u[1],miner,u[3])
                            uq.append((v[0],up,u[0],u[1],miner,u[3]))
                            up=up+1
                        #contractの書き込み
                        for u in v[7]:
                            c=atbl.getId(u[0])
                            f=atbl.getId(u[1])
                            cq.append((v[0],c,f))

                    btbl.addBlocks(bq)
                    ttbl.addTransactions(tq)
                    utbl.addBlocks(uq)
                    ctbl.addContracts(cq)
                    meta.putInt("NextAccountScanTarget",e)
                    db.commit()
                read(target_block,args.close,callback)
            except:
                db.rollback()
                print("Rollback! NextAccountScanTarget at {0}".format(meta.getInt("NextAccountScanTarget",0)))
                raise
            pass
    {"sqlite":_sqlite,"json":_json,"console":_console}[args.format]()
    

# %%
