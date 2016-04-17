#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
@version: 
@author: 
@license: 
@contact: 
@site: 
@software: PyCharm
@file: multiuser.py
@time: 4/16/16 3:30 PM
"""

from __future__ import absolute_import, division, print_function, \
    with_statement

import time
import errno
import traceback
import socket
import logging
import json
import collections
import os

import common, eventloop, tcprelay, udprelay, asyncdns, shell
from multiuserdb import Redis_DB, Mongo_DB, Mysql_DB

BUF_SIZE = 1506
STAT_SEND_LIMIT = 50

# we save stat to db every TIMEOUT_PRECISION seconds, larger than eventloop's TIMEOUT_PRECISION
TIMEOUT_PRECISION = 15

class MultiUser(object):
    def __init__(self, config):
        self._config = config
        self.r = Redis_DB()
        self.m = Mysql_DB.get_instance()
        self._stat = False # important！！
        self._relays = {}  # (tcprelay, udprelay)
        self._loop = eventloop.EventLoop()
        self._dns_resolver = asyncdns.DNSResolver()
        self._dns_resolver.add_to_loop(self._loop)

        self._statistics = collections.defaultdict(int)
        self._control_client_addr = None
        try:
            manager_address = config['manager_address']
            if ':' in manager_address:
                addr = manager_address.rsplit(':', 1)
                addr = addr[0], int(addr[1])
                addrs = socket.getaddrinfo(addr[0], addr[1])
                if addrs:
                    family = addrs[0][0]
                else:
                    logging.error('invalid address: %s', manager_address)
                    exit(1)
            else:
                addr = manager_address
                if os.path.exists(addr):
                    logging.warning('manager address already in use, try to remove it')
                    os.remove(addr)
                family = socket.AF_UNIX
            self._control_socket = socket.socket(family,
                                                 socket.SOCK_DGRAM)
            self._control_socket.bind(addr)
            self._control_socket.setblocking(False)
        except (OSError, IOError) as e:
            logging.error(e)
            logging.error('can not bind to manager address')
            exit(1)
        self._loop.add(self._control_socket,
                       eventloop.POLL_IN, self)
        self._loop.add_periodic(self.handle_periodic)

        # port_password = config['port_password']
        # del config['port_password']
        # for port, password in port_password.items():
        #     a_config = config.copy()
        #     a_config['server_port'] = int(port)
        #     a_config['password'] = password
        #     # self.add_port(a_config)
        #     self.add_user(a_config)

        self._stat = self.stat_init(config)
        self.ports_to_remove = []


    def stat_init(self, config):
        ports_info = self.m.get_port_info()
        print(ports_info)
        if not ports_info:
            return False

        for row in ports_info:
            a_config = config.copy()
            a_config['server_port'] = row[0] # server_port in config.json will be replace with ports in database,
            a_config['password'] = common.to_bytes(row[1]) # and password too
            a_config['t'] = row[2]
            a_config['d'] = row[3]
            a_config['u'] = row[4]
            self.add_port(a_config)
        return True

    def stat_cache(self, port, value, up_down):
        if not self._stat:
            return
        now = int(time.time())
        port_activity = '%s_activity' % port
        port_up_down = '%s_%s' % (port, up_down)
        self.r.inc_data(port_up_down, value)
        self.r.set_data(port_activity, now)

    def stat_process(self):
        if not self._stat:
            return
        now = int(time.time())
        ports_to_remove = []
        for port in self.r.get_keys('ports_to_stat'):
            stat_t = int(self.r.get_data('%s_t' % port))
            stat_d = int(self.r.get_data('%s_d' % port))
            stat_u = int(self.r.get_data('%s_u' % port))
            port_activity = '%s_activity' % port
            if stat_d + stat_u >= stat_t:
                print('db stop server at port [%s] reason: out bandwidth' % (port))
                ports_to_remove.append(port)
            last_activity = self.r.get_data(port_activity)
            if last_activity and now - int(last_activity) < TIMEOUT_PRECISION:
                print('update port:', port)
                print({'server_port':port, 'd':stat_d, 'u':stat_u, 'last_activity':last_activity})
                self.m.update_stat({'server_port':port, 'd':stat_d, 'u':stat_u, 'last_activity':last_activity})
        return ports_to_remove

    # TODO: realize with flask in front end
    def add_user(self, config):
        # mysql
        self.m.add_user(config)

    # TODO: realize with flask in front end
    def remove_user(self, config):
        # mysql
        self.m.remove_user(config)

    def add_port(self, config):
        port = int(config['server_port'])
        servers = self._relays.get(port, None)
        if servers:
            logging.error("server already exists at %s:%d" % (config['server'],
                                                              port))
            return

        # redis cache
        pipe = self.r.pipe()
        pipe.set('%s_t' % config['server_port'], config['t'])
        pipe.set('%s_d' % config['server_port'], config['d'])
        pipe.set('%s_u' % config['server_port'], config['u'])
        pipe.sadd('ports_to_stat', config['server_port'])
        pipe.execute()

        logging.info("adding server at %s:%d" % (config['server'], port))
        t = tcprelay.TCPRelay(config, self._dns_resolver, False,
                              self.stat_callback)
        u = udprelay.UDPRelay(config, self._dns_resolver, False,
                              self.stat_callback)
        t.add_to_loop(self._loop)
        u.add_to_loop(self._loop)
        self._relays[port] = (t, u)

    def remove_port(self, config):
        port = int(config['server_port'])
        servers = self._relays.get(port, None)
        if servers:
            logging.info("removing server at %s:%d" % (config['server'], port))
            t, u = servers
            t.close(next_tick=False)
            u.close(next_tick=False)
            del self._relays[port]

            # redis cache
            pipe = self.r.pipe()
            pipe.delete('%s_t' % config['server_port'])
            pipe.delete('%s_d' % config['server_port'])
            pipe.delete('%s_u' % config['server_port'])
            pipe.srem('ports_to_stat', config['server_port'])
            pipe.execute()

        else:
            logging.error("server not exist at %s:%d" % (config['server'],
                                                         port))

    def handle_event(self, sock, fd, event):
        if sock == self._control_socket and event == eventloop.POLL_IN:
            data, self._control_client_addr = sock.recvfrom(BUF_SIZE)
            parsed = self._parse_command(data)
            if parsed:
                command, config = parsed
                a_config = self._config.copy()
                if config:
                    # let the command override the configuration file
                    a_config.update(config)
                if 'server_port' not in a_config:
                    logging.error('can not find server_port in config')
                else:
                    if command == 'add':
                        aa_config = shell.make_config(a_config, False)
                        self.add_user(aa_config)
                        self.add_port(aa_config)
                        self._send_control_data(b'ok')
                    elif command == 'remove':
                        self.remove_port(a_config)
                        self.remove_user(a_config)
                        self._send_control_data(b'ok')
                    elif command == 'ping':
                        self._send_control_data(b'pong')
                    else:
                        logging.error('unknown command %s', command)

    def _parse_command(self, data):
        # commands:
        # add: {"server_port": 8000, "password": "foobar"}
        # remove: {"server_port": 8000"}
        data = common.to_str(data)
        parts = data.split(':', 1)
        if len(parts) < 2:
            return data, None
        command, config_json = parts
        try:
            config = shell.parse_json_in_str(config_json)
            return command, config
        except Exception as e:
            logging.error(e)
            return None

    def stat_callback(self, port, data_len, up_down):
        self._statistics[port] += data_len
        self.stat_cache(port, data_len, up_down)

    def handle_periodic(self):
        r = {}
        i = 0

        def send_data(data_dict):
            if data_dict:
                # use compact JSON format (without space)
                data = common.to_bytes(json.dumps(data_dict,
                                                  separators=(',', ':')))
                self._send_control_data(b'stat: ' + data)

        def make_config(port):
            a_config = self._config.copy()
            config =  {'server_port': port}
            a_config.update(config)
            return a_config

        for k, v in self._statistics.items():
            r[k] = v
            i += 1
            # split the data into segments that fit in UDP packets
            if i >= STAT_SEND_LIMIT:
                send_data(r)
                r.clear()
                i = 0
        if len(r) > 0:
            send_data(r)
        self._statistics.clear()
        self.ports_to_remove = self.stat_process()
        if self.ports_to_remove:
            for port in self.ports_to_remove:
                a_config = make_config(port)
                self.remove_port(a_config)
                self.remove_user(a_config)
                print('port to remove:', port)

    def _send_control_data(self, data):
        if self._control_client_addr:
            try:
                self._control_socket.sendto(data, self._control_client_addr)
            except (socket.error, OSError, IOError) as e:
                error_no = eventloop.errno_from_exception(e)
                if error_no in (errno.EAGAIN, errno.EINPROGRESS,
                                errno.EWOULDBLOCK):
                    return
                else:
                    shell.print_exception(e)
                    if self._config['verbose']:
                        traceback.print_exc()

    def run(self):
        self._loop.run()


def run(config):
    MultiUser(config).run()


def test():
    import time
    import threading
    import struct
    import encrypt

    logging.basicConfig(level=5,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    enc = []
    eventloop.TIMEOUT_PRECISION = 1

    def run_server():
        config = {
            'server': '127.0.0.1',
            'local_port': 1081,
            'method': 'aes-256-cfb',
            'manager_address': '127.0.0.1:6001',
            'timeout': 60,
            'fast_open': False,
            'verbose': 2
        }
        manager = MultiUser(config)
        enc.append(manager)
        manager.run()

    t = threading.Thread(target=run_server)
    t.start()
    time.sleep(1)
    manager = enc[0]
    cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cli.connect(('127.0.0.1', 6001))

    # test add and remove
    time.sleep(1)
    cli.send(b'add: {"server_port":7001, "password":"asdfadsfasdf", "t":10737418240}')
    time.sleep(1)
    assert 7001 in manager._relays
    data, addr = cli.recvfrom(1506)
    assert b'ok' in data

    cli.send(b'remove: {"server_port":8381}')
    time.sleep(1)
    assert 8381 not in manager._relays
    data, addr = cli.recvfrom(1506)
    assert b'ok' in data
    logging.info('add and remove test passed')

    # test statistics for TCP
    header = common.pack_addr(b'bcy.net') + struct.pack('>H', 80)
    data = encrypt.encrypt_all(b'asdfadsfasdf', 'aes-256-cfb', 1,
                               header + b'GET /\r\n\r\n')
    tcp_cli = socket.socket()
    tcp_cli.connect(('127.0.0.1', 7001))
    tcp_cli.send(data)
    tcp_cli.recv(4096)
    tcp_cli.close()

    data, addr = cli.recvfrom(1506)
    data = common.to_str(data)
    assert data.startswith('stat: ')
    data = data.split('stat:')[1]
    stats = shell.parse_json_in_str(data)
    assert '7001' in stats
    print(stats)
    logging.info('TCP statistics test passed')

    # test statistics for UDP
    header = common.pack_addr(b'127.0.0.1') + struct.pack('>H', 80)
    data = encrypt.encrypt_all(b'asdfghjkl', 'aes-256-cfb', 1,
                               header + b'test')
    udp_cli = socket.socket(type=socket.SOCK_DGRAM)
    udp_cli.sendto(data, ('127.0.0.1', 8382))
    tcp_cli.close()

    data, addr = cli.recvfrom(1506)
    data = common.to_str(data)
    assert data.startswith('stat: ')
    data = data.split('stat:')[1]
    stats = json.loads(data)
    assert '8382' in stats
    logging.info('UDP statistics test passed')

    manager._loop.stop()
    t.join()





if __name__ == '__main__':
    test()