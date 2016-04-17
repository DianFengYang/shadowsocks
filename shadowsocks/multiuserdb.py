#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
@version: 
@author: 
@license: 
@contact: 
@site: 
@software: PyCharm
@file: multiuserdb.py
@time: 4/15/16 8:27 PM
"""

from __future__ import absolute_import, division, print_function, \
    with_statement

import redis
import pymongo
import pymysql.cursors

import logging

class Config_DB(object):
    # redis
    redis_host = '127.0.0.1'
    redis_port = 6379
    redis_dbid = 0

    #mongodb
    mongo_host = '127.0.0.1'
    mongo_port = 27017
    mongo_db   = 'shadowsocks'

    #mysql
    mysql_host = '127.0.0.1'
    mysql_user = 'ss'
    mysql_pass = 'shadowsocks'
    mysql_db   = 'shadowsocks'



class Redis_DB(object):

    pool = None

    def __init__(self):
        if Redis_DB.pool is None:
            Redis_DB.create_pool()
        self._connection = redis.Redis(connection_pool=Redis_DB.pool)

    @staticmethod
    def create_pool():
        Redis_DB.pool = redis.ConnectionPool(
            host = Config_DB.redis_host,
            port = Config_DB.redis_port,
            db   = Config_DB.redis_dbid
        )

    def set_data(self, key, value):
        return self._connection.set(key, value)

    def get_data(self, key):
        return self._connection.get(key)

    def del_data(self, key):
        return self._connection.delete(key)

    def dec_data(self, key, value):
        return self._connection.decr(key, value)

    def inc_data(self, key, value):
        return self._connection.incr(key, value)

    def add_set(self, key, value):
        return  self._connection.sadd(key, value)

    def rem_set(self, key, value):
        return self._connection.srem(key, value)

    def get_keys(self, key):
        return self._connection.smembers(key)

    def pipe(self):
        return self._connection.pipeline()


class Mongo_DB(object):

    conn = None

    def __init__(self):
        if Mongo_DB.conn is None:
            Mongo_DB.create_conn()
        self._db = Mongo_DB.conn[Config_DB.mongo_db]

    @staticmethod
    def create_conn():
        Mongo_DB.conn = pymongo.Connection(
            Config_DB.mongo_host,
            Config_DB.mongo_port
        )

    def get_db(self):
        return self._db

    def set_data(self, table, key, value):
        print('update port:', key, 'with value:', value)
        self._db[table].update({'port': key}, {'$set' : {'current_transfer' : value}})

    def get_data(self, key):
        return {'8381': 1024*1024*1024, '8382': 10}

    def del_data(self, key):
        print('delete port:', key, 'from server')


class Mysql_DB(object):

    instance = None

    def __init__(self):
        pass

    @staticmethod
    def get_instance():
        if Mysql_DB.instance is None:
            Mysql_DB.instance = Mysql_DB()
        return Mysql_DB.instance

    def _create_conn(self):
        connection = pymysql.connect(
            host=Config_DB.mysql_host,
            user=Config_DB.mysql_user,
            password=Config_DB.mysql_pass,
            db=Config_DB.mysql_db,
            charset='utf8'
            )
        return connection


    # def manage_user(self, config, enable):
    #     connection = self._create_conn()
    #     _enable = enable ^ 1
    #
    #     try:
    #         for port in config['ports']:
    #             with connection.cursor() as cursor:
    #                 sql = "UPDATE `user` SET (`enable`) VALUE (%s) WHERE (`port`, `enable`) VALUES (%s, %s)"
    #                 cursor.execute(sql, (enable, port, _enable))
    #                 connection.commit()
    #
    #                 if enable:
    #                     sql = "UPDATE `user` SET (`current`) VALUE (%s) WHERE (`port`, `enable`) VALUES (%s, 1)"
    #                     cursor.execute(sql, (int(config['current']), port))
    #                     connection.commit()
    #                     self._r.set_data(port, int(config['current']))
    #     except Exception as e:
    #         logging.error(e)
    #     finally:
    #         connection.close()

    def update_stat(self, config):
        connection = self._create_conn()

        try:
            with connection.cursor() as cursor:
                sql = "UPDATE `user` SET `d` = %s, `u` = %s, `last_active_date` = %s WHERE `port` = %s AND `enable` = 1"
                cursor.execute(sql, (config['d'], config['u'], config['last_activity'], config['server_port']))
                connection.commit()
        except Exception as e:
            logging.error(e)
        finally:
            connection.close()

    def get_port_info(self, config = None):
        connection = self._create_conn()

        try:
            with connection.cursor() as cursor:
                # Read a single record
                if config is None:
                    sql = "SELECT `port`, `passwd`, `t`, `d`, `u` FROM `user` WHERE `d` + `u` < `t` AND `enable` = 1"
                    cursor.execute(sql)
                    result = cursor.fetchall()
                    return result
                else:
                    sql = "SELECT `t`, `d`, `u` FROM `user` WHERE `port` = %s AND `enable` = 1"
                    cursor.execute(sql, (config['server_port']))
                    result = cursor.fetchone()
                    return result
        except Exception as e:
            logging.error(e)
        finally:
            connection.close()

    # should not do it at here
    def add_user(self, config):
        connection = self._create_conn()

        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM `user` WHERE `port` = %s AND `enable` = 1"
                cursor.execute(sql, (config['server_port']))
                result = cursor.fetchone()
                if not result:
                    logging.error("server port already exists and running at %s:%d" % (config['server'], config['server_port']))
                    sql = "INSERT INTO `user` (`email`, `user_pass`, `port`, `passwd`, `t`, `d`, `u`, `enable`, " \
                          "`active_date`, `inactive_date`, `last_active_date`) " \
                          "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(sql, (config['email'], config['user_pass'], config['server_port'],
                                         config['password'], config['t'], config['d'], config['u'],
                                         config['enable'], config['active_date'], config['inactive_date'],
                                         config['last_active_date']))
                    connection.commit()
                else:
                    logging.error("server port already exists and running at %s:%d" % (config['server'], config['server_port']))

        except Exception as e:
            logging.error(e)
        finally:
            connection.close()

    # should not do it at here
    def remove_user(self, config):
        connection = self._create_conn()

        try:
            with connection.cursor() as cursor:
                sql = "UPDATE `user` SET `enable` = 0  WHERE `port` = %s AND `enable` = 1"
                cursor.execute(sql, (config['server_port']))
                connection.commit()
        except Exception as e:
            logging.error(e)
        finally:
            connection.close()




if __name__ == '__main__':
    pass