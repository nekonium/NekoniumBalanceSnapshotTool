"""pickle可能なオブジェクトをJSONと相互変換します。

Copyright 2020 nyatla

pickle可能なオブジェクトをJSONに変換してシリアライズ/復元します。
変換元のオブジェクトは、配列,辞書,JsonPicklableの継承クラスです。
再帰構造の動作チェックはしてません。

オブジェクトは、{"__cls":str,"d":object}の辞書形式に変換します。
JSONからオブジェクトに戻すときは、"__cls"キーに文字列を持つ要素をクラスインスタンスと判定し、
同名のクラスが存在し、かつそのクラスがpickle可能な場合のみインスタンスの復元を試みます。
_clsキーにCLSIDが含まれる場合は、そちらを優先して復元を試みます。
それ以外の場合は、そのままjsonオブジェクトに変換します。

このツールはPickleインストラクションを再現しません。データ構造をできる限り"そのまま"Jsonに変換します。


This module serialize/desirialize  pickleable objects to/from JSON.
The conversion source object is array, dictionary, and JsonPicklable extend classes.The recursive structure is not checked.
The class object is encoded into the dictionary format of {"__cls": str, "d": object}.
When decode from JSON to an object, the elements are detected that has a character string in the "__cls" key as  a class instance.
Attempts to decode instances only if a class name with in globals()  and the class is extends picklable.
Otherwise, decode it to json object as it is.
This tool does not reproduce Pickle instructions. 


Classes:
    JsonPicklable
Functions:
    dumps ->str
    loads ->object

Licence:
    Copyright (c) 2020, nyatla
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met: 

    1. Redistributions of source code must retain the above copyright notice,
    this list of conditions and the following disclaimer. 
    2. Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution. 

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

    The views and conclusions contained in the software and documentation are those
    of the authors and should not be interpreted as representing official policies, 
    either expressed or implied, of the FreeBSD Project.
"""
__version__ = '1.0.1'
__all__ = [
    'dumps', 'loads','JsonPicklable'
]
#%%
import json
import sys
import inspect


import datetime
class _builtin_datetime_datetime:
    @staticmethod
    def serialize(v:datetime.datetime):
        if v.tzinfo is not None:
            raise TypeError("datetime.tzinfo must be None.")
        return (v.year,v.month,v.day,v.hour,v.minute,v.second,v.microsecond,v.fold)
    @staticmethod
    def desirialize(s:object)->datetime.datetime:
        return datetime.datetime(s[0],s[1],s[2],s[3],s[4],s[5],s[6],fold=s[7])


_builtin_classes={
    'datetime.datetime':_builtin_datetime_datetime,
}
_clsid_table={

}

class JsonPicklable:
    """
    pickle可能なオブジェクトが継承する修飾クラスです。
    dump/loadするクラスは、このクラスを継承する必要があります。
    継承先で__getstate__()と__setstate__()を上書きしない場合は、インスタンスの__dict__をシリアライズします。

    対象のクラスが_CLSIDクラス定数を持つ場合、その値はクラスを特定するキーになります。
    ローダーは、_CLSIDに一致するクラスをCLSIDテーブルから検索し、IDがテーブルに存在しない場合は、通常通りpythonの名前空間から検索します。
    _CLSIDは名前空間を超えて一意にインスタンスを特定する用途に使用します。
    """
    def _jdump(self):
        t=type(self)
        cls_=t.__module__+"."+t.__name__
        if hasattr(t,"_CLSID"):
            cls_=cls_+"#"+t._CLSID
        return {"__cls":cls_,"d":self.__getstate__()}
    def __getstate__(self):
        odict = self.__dict__.copy()
        return odict
    def __setstate__(self, state):
        self.__dict__.update(state)

def _dump_default(item):
    #JsonPicklableなクラス
    if isinstance(item,JsonPicklable):
        return item._jdump()
    #ビルトインクラス
    cn=item.__module__+"."+item.__class__.__name__    
    bc=_builtin_classes.get(cn)
    if bc is not None:
        d=bc.serialize(item)
        assert(d is not None)
        return {"__blt":cn,"d":d}
    #不明
    raise TypeError("%s %s is not pickleable"%(str(type(item)),str(item)))

def _load_hook(dct):
    class_name2 = dct.get('__cls')
    if type(class_name2) is str:
        n=class_name2.split("#")
        if len(n)==2:
            #idでクラスを検索して生成
            if n[1] in _clsid_table:
                c=_clsid_table[n[1]]
                o=c.__new__(c)
                o.__setstate__(dct.get("d"))
                return o
        #クラス名で検索をする
        class_name=n[0]
        #module内のクラスの一覧を検索
        sp=class_name.split(".")
        mod=sys.modules.get(".".join(sp[0:-1]))
        if mod is not None:
            cl={i[1].__module__+"."+i[1].__name__:i[1] for i in inspect.getmembers(mod,inspect.isclass)}
            c=cl.get(class_name)
            if c is not None:
                o=c.__new__(c)
                o.__setstate__(dct.get("d"))
                return o
    class_name = dct.get('__blt')
    if type(class_name) is str:
        bc=_builtin_classes.get(class_name)
        if bc is not None:
            return bc.desirialize(dct.get("d"))
    return dct

def addClass(c:JsonPicklable):
    """CLSIDを持つクラスを登録します
    """
    assert(hasattr(c,"_CLSID"))
    _clsid_table[c._CLSID]=c

def dumps(bj, *v, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None,sort_keys=False, **kw):
    """
    json.dumps互換の関数です。
    """
    return json.dumps(bj,default=_dump_default,*v,skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular,allow_nan=allow_nan,cls=cls, indent=indent,separators=separators,sort_keys=sort_keys,**kw)
def dump(bj,fp, *v, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None,sort_keys=False, **kw):
    """
    json.dumps互換の関数です。
    """
    return json.dump(bj,fp,default=_dump_default,*v,skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular,allow_nan=allow_nan,cls=cls, indent=indent,separators=separators,sort_keys=sort_keys,**kw)

def loads(s, *v, cls=None, parse_float=None, parse_int=None, parse_constant=None,**kw):
    """
    json.loads互換の関数です。
    """
    return json.loads(s, *v, cls=cls, object_hook=_load_hook,parse_float=parse_float, parse_int=parse_int, parse_constant=parse_constant,**kw)
def load(fp, *v, cls=None, parse_float=None, parse_int=None, parse_constant=None,**kw):
    """
    json.load互換の関数です。
    """
    return json.load(fp, *v, cls=cls, object_hook=_load_hook,parse_float=parse_float, parse_int=parse_int, parse_constant=parse_constant,**kw)


#%%
import pickle
if __name__ == "__main__":
    """
    テスト
    """
    class A(JsonPicklable):
        def __init__(self):
            self.a=1
            self.b="a"
            self.d=datetime.datetime.now()
    class B(JsonPicklable):
        def __init__(self):
            self.a=2
            self.b="b"
            self.c=A()
        def __getstate__(self):
            """
            Make override if you have owen pickle function.
            独自のpickle実装があればこの関数を上書きします。
            """    
            odict = super().__getstate__()
            return odict
        def __setstate__(self, state):
            """
            Make override if you have owen pickle function.
            独自のpickle実装があればこの関数を上書きします。
            """    
            self.__dict__.update(state)
    for b in [
        [A(),B()],
        [{"__cls":1},A(),B()],
        [{"__cls":"name"},A(),B()],
        [{"__cls":[A(),B()]}]
        ]:
        print("----")
        #ダンプ
        ds=dumps(b)
        print("dump:"+ds)
        #ロード
        lo=loads(ds)
        print("load:"+str(lo))
        #ダンプ
        ds2=dumps(lo)
        print("dump:"+ds2)

# %%
