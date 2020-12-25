"""NUKOチェーンからブロックエクスプローラに必要な基本情報を読みだすクラスさん
"""
#%%
from web3 import Web3

import os,sys
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
from nukochandb import AccountTable,NukoChanDb,fromBlobUint



class BlockReader:
    @property
    def latestBlockNumber(self):
        """最後に採掘されたブロック番号
        """
        raise NotImplementedError()
    def scanBlock(self,start:int,end:int=None):
        """
        returns
        {blocks:[(number,gasUsed,miner,timestamp,reward,[TRANSACTIONS,...],[UNCLE]),...],
        addresses:[(account,foundat,foundin),...]}
        TRANSACTIONS=(from,to,gas,gasPrice,value)
        UNCLE=(number,gasUsed,miner,timestamp,reward)
        """
        raise NotImplementedError()

    def scanActiveAccount(self,start:int,end:int=None):
        """start<n<endにあるブロック番号で検出した口座リストを返す。
        口座は、以下の情報の重複無しリスト。        
        1.そのブロックの採掘口座
        2.そのブロックのトランザクションに含まれる送信元、送信先口座
        3.genesisblock
        returns:
            {アドレス:(出現ブロック高,検出理由)}
        """
        raise NotImplementedError()

    def blockReword(self,number):
        raise NotImplementedError()


class EthBasedBlockReader(BlockReader):
    """イーサリウムのスキャナ
    """
    _block_0_hash:str
    _genesis:list
    _web3:Web3
    def __init__(self,web3,block_0_hash,genesis):
        if web3 is not None:
            if web3.eth.getBlock(0)["hash"].hex()!=block_0_hash:
                raise Exception("This chain is not valid!")
        self._web3=web3
        self._genesis=genesis
        return
    @property
    def latestBlockNumber(self):
        """最後に採掘されたブロック番号
        """
        assert(self._web3 is not None)
        return self._web3.eth.blockNumber
    def scanBlock(self,start:int,end:int=None):
        assert(self._web3 is not None)
        web3=self._web3
        genesis=self._genesis
        end=start+1 if end is None else end
        latest=web3.eth.blockNumber+1
        bn=start
        end=end if end<latest else latest
        assert(start<end)
        blocks=[]
        #0版の場合はgenesisブロックを追加
        addresses = {k:(0,AccountTable.FoundIn.GENESIS) for k in genesis} if start==0 else {}
        for bn in range(start,end):
            block=web3.eth.getBlock(bn)
            #ブロックの採掘者
            if block["miner"] not in addresses:
                addresses[block["miner"]]=(bn,AccountTable.FoundIn.MINING)
            #トランザクション
            contracts=[]
            transactions=[]
            for i in block["transactions"]:
                tx=web3.eth.getTransaction(i)
                rx=web3.eth.getTransactionReceipt(i)
                transactions.append((tx["from"],tx["to"],tx["gas"],tx["gasPrice"],tx["value"],rx["gasUsed"],rx["cumulativeGasUsed"]))
                #トランザクションで初めて現れたアドレス
                if tx["to"] is not None and tx["to"] not in addresses:
                    addresses[tx["to"]]=(bn,AccountTable.FoundIn.TX_TO)
                if tx["from"] is not None and tx["from"] not in addresses:
                    addresses[tx["from"]]=(bn,AccountTable.FoundIn.TX_FROM)
                if rx["contractAddress"] is not None:
                    contracts.append((rx["contractAddress"],rx["from"]))
                    if rx["contractAddress"] not in addresses:
                        addresses[rx["contractAddress"]]=(bn,AccountTable.FoundIn.CONTRACT)
            #uncle
            uncles=[]
            for j in range(web3.eth.getUncleCount(bn)):
                ub=web3.eth.getUncleByBlock(bn,j)
                if len(ub["uncles"])>0:
                    raise("UncleTree!",bn) 
                ubn=int(ub["number"],16)
                ugu=int(ub["gasUsed"],16)
                uts=int(ub["timestamp"],16)
                ureward=(ubn + 8 - bn) * self.blockReword(bn) // 8 
                ub_m=web3.toChecksumAddress(ub["miner"])
                uncles.append((ubn,ugu,ub_m,uts,ureward))
                #Uncleで初めてあらわれたアドレス
                if ub_m not in addresses:
                    addresses[ub_m]=(bn,AccountTable.FoundIn.MINING)

            blocks.append((bn,block["gasUsed"],block["miner"],block["timestamp"],self.blockReword(bn),transactions,uncles,contracts))
        return {"addresses":addresses,"blocks":blocks}
    def allcated(self,account):
        """初期割り当て量を返す。
        """
        return 0 if account not in self._genesis else self._genesis[account][0]
    def unkceBlockReword(self,number,uncleNumber):
        assert(number-uncleNumber>0)
        return (uncleNumber + 8 - number) * self.blockReword(number) // 8 



class NukoBlockReader(EthBasedBlockReader):
    _GENESIS={
        "0xBbFdCBbD22960B6fcf4a0a101b816614aa551c4b":(2448421*1000000000000000000,),
        "0xBc4517bc2ddE774781E3D7B49677DE3449D4D581":(2000000*1000000000000000000,),
        "0x62A87d9716b5826063d98294688ec76F774034d6":(6000000*1000000000000000000,),
        "0x817570E7E0838ca0c6c136bF9701962FF7a6e562":(1000000*1000000000000000000,),
        "0xbd2746c132393fD822D971EecAF7f4cd770A5472":(1000000*1000000000000000000,)
    }
    _HASH_B0='0x1a505395bfe4b2a8eef2f80033d68228db70e82bb695dd4ffb20e6d0cf71cb73'
    _web3:Web3
    def __init__(self,web3= Web3(Web3.HTTPProvider('http://127.0.0.1:8293'))):
        super().__init__(web3,NukoBlockReader._HASH_B0,NukoBlockReader._GENESIS)
        return
    def blockReword(self,number):
        return 0 if number==0 else 7500000000000000000

#%%


class BalanceSnapshotReader:
    """バランススナップショットの読み出し用
    """
    _db:NukoChanDb
    _table_names:list
    def __init__(self,db:NukoChanDb,table_names=None):
        """
        Args:
        table_names:dict {"AccountTable","BalanceSnapshotTable"}
        """
        self._db=db
        self._table_names=table_names if table_names is not None else {i:i for i in ["AccountTable","BalanceSnapshotTable"]}
    def getBalanceSnapshot(self,height:int):
        """チェーンからアカウントごとのバランスリストを得る。
        Args:
            account エンコードアドレス又はアカウントID
        Return:
            {
                height:int,
                balances:[account,balance]
            }
        """
        tnames=self._table_names
        tr=self._db.select("SELECT A.account,B.balance,A.foundin FROM {0} AS B INNER JOIN {1} AS A ON B.account=A.id AND B.blockNumber=?;".format(tnames["BalanceSnapshotTable"],tnames["AccountTable"]),[height])
        return {
            "height":height,
            "balances":[
                (i[0],fromBlobUint(i[1]),AccountTable.FoundIn.toEnum(i[2]))
            for i in tr]
        }



# %%
