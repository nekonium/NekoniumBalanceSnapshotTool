#%%
import time
import traceback
from urllib.parse import urlparse
import os,sys




class Db:
    @staticmethod    
    def create(uri,autocommit=False):
        """
        urlでデータベースに接続する。
        'mysql://user:pass@localhost:3306/dbname'
        'sqlite:///dbpath'
        """
        url = urlparse(uri)
        if url.scheme=="mysql":
            return MySqlDb(url.hostname,url.port,url.username,url.password,url.path[1:],autocommit)
        elif url.scheme=="sqlite":
            return SqliteDb(url.path)
        else:
            raise Excption("bad uri")
    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        if self._connection is not None:
            self.close()        
    @property
    def connection(self):
        return self._connection
    def execute(self,sql,params=None):
        raise NotImplementedError()
    def executemany(self,sql,params:list=None):
        raise NotImplementedError()
    def select(self,sql,params=None):
        raise NotImplementedError()
    def selectOne(self,sql,params:list=None):
        """一行だけを返す。結果が複数ある時は例外。ない時はNone
        """
        r=self.select(sql,params)
        if r is None or len(r)==0:
            return None
        if len(r)>1:
            raise Exception("many rows were returned.")
        return r[0]
    def lastInsertedId(self):
        raise NotImplementedError()
    def numberOfChanges(self):
        raise NotImplementedError()
    def commit(self):
        raise NotImplementedError()
    def rollback(self):
        raise NotImplementedError()
    def close(self):
        raise NotImplementedError()

import sqlite3

class SqliteDb(Db):
    def __init__(self,path,isolation_level_='EXCLUSIVE',autocommit=True):
        self._connection=sqlite3.connect(path, isolation_level=isolation_level_)
    @property
    def connection(self):
        return self._connection
    def execute(self,sql,params=None):
        c = self._connection.cursor()
        try:
            if params is None:
                c.execute(sql)
            else:
                c.execute(sql,params)
            return
        finally:
            c.close()
    def executemany(self,sql,params:list=None):
        c = self._connection.cursor()
        try:
            if params is None:
                c.executemany(sql)
            else:
                c.executemany(sql,params)
            return
        finally:
            c.close()
    def select(self,sql,params=None):
        c = self._connection.cursor()
        try:
            if params is None:
                c.execute(sql)
            else:
                c.execute(sql,params)
            ret=c.fetchall()
            return ret
        finally:
            c.close()
    def lastInsertedId(self):
        s=self.select("select last_insert_rowid()")
        print(s)
        return s[0][0]
    def numberOfChanges(self):
        return self.select("select changes();")[0][0]
    def commit(self):
        self._connection.commit()
    def rollback(self):
        self._connection.rollback()
    def close(self):
        self._connection.commit()
        self._connection.close()

import mysql;
import mysql.connector;

class MyConverter(mysql.connector.conversion.MySQLConverter):
    def row_to_python(self, row, fields):
        row = super(MyConverter, self).row_to_python(row, fields)
        def to_unicode(col):
            if isinstance(col, bytearray):
                return col.decode('utf-8')
            return col
        return[to_unicode(col) for col in row]

class MySqlDb(Db):
    """MySQLのコネクタ
    """
    _connection:mysql.connector.connection.MySQLConnection
    def __init__(self,host="localhost",port=3306,user="root",password="",database="mysql",autocommit:bool=True):
        conn = mysql.connector.connect(host=host,port=port,user=user,password=password,database=database,converter_class=MyConverter)
        conn.autocommit=autocommit
        self._connection=conn
    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        if self._connection is not None:
            self.close()
    @property
    def connection(self):
        return self.conn
    def execute(self,sql,params=None):
        cur = self._connection.cursor()
        try:
            if params is None:
                cur.execute(sql)
            else:
                cur.execute(sql,params)
            return
        finally:
            cur.close()
    def executemany(self,sql,params:list=None):
        cur = self._connection.cursor()
        try:
            if params is None:
                cur.executemany(sql)
            else:
                cur.executemany(sql,params)
            return
        finally:
            cur.close()
    def select(self,sql,params=None):
        cur = self._connection.cursor()     
        try:
            if params is None:
                cur.execute(sql)
            else:
                cur.execute(sql,params)
            ret=cur.fetchall()
            return ret
        finally:
            cur.close()
    def callproc(self,method,params=None):
        cur = self._connection.cursor()
        try:
            if params is None:
                ra=cur.callproc(method)
            else:
                ra=cur.callproc(method,params)
            return ra
        finally:
            cur.close()            
    def commit(self):
        self._connection.commit()
        return
    def rollback(self):
        self._connection.rollback()
    def close(self):
        self._connection.commit()
        self._connection.close()
        self._connection=None
        return

#%%