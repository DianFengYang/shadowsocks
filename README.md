shadowsocks
===========

[![PyPI version]][PyPI]
[![Build Status]][Travis CI]
[![Coverage Status]][Coverage]

A fast tunnel proxy that helps you bypass firewalls.

Features:
- TCP & UDP support
- User management API
- TCP Fast Open
- Workers and graceful restart
- Destination IP blacklist

Server
------

### Install

Debian / Ubuntu:

    apt-get install python-pip
    pip install shadowsocks

CentOS:

    yum install python-setuptools && easy_install pip
    pip install shadowsocks

Windows:

See [Install Server on Windows]

### Usage

    ssserver -p 443 -k password -m aes-256-cfb

To run in the background:

    sudo ssserver -p 443 -k password -m aes-256-cfb --user nobody -d start

To stop:

    sudo ssserver -d stop

To check the log:

    sudo less /var/log/shadowsocks.log

Check all the options via `-h`. You can also use a [Configuration] file
instead.

多用户版本——multiuser分支
===========

主要添加了多用户流量管理功能。
## 功能
* 在shadowsocks的[Manage Multiple Users](https://github.com/shadowsocks/shadowsocks/wiki/Manage-Multiple-Users)添加和移除用户（端口）的功能的基础上，
使用了mysql来管理用户信息、redis来缓存用户状态，服务器端启动时从mysql加载用户信息并打开相应的端口，具体实现见`multiuser.py`。  
* 实现了多用户下的流量监控与管理，自动禁用超出流量的用户。  

配合基于Flask的shadowsocks-admin多用户后台管理网站使用效果更佳。

## 数据库
* mysql
* redis  

在mysql中建立了`shadowsocks`数据库和`ss`用户，并通过`grant all privileges on shadowsocks.* to ss@localhost IDENTIFIED by 'shadowsocks';`为`ss`分配`shadowsocks`数据库的权限。  
在redis中使用了密码，修改其配置文件`/etc/redis/redis.conf`，取消`requirepass`前的注释，并在后面添加密码。  
建议修改mysql和redis的端口、用户名以及密码，数据相关配置与操作见`multiuserdb.py`。

## 使用
### 安装
```
git clone -b multiuser git@github.com:arrti/shadowsocks.git
cd shadowsocks
python setup.py install
```

### 依赖  
* redis
* PyMySQL  

### 导入数据表
通过mysql导入`shadowsocks/shadowsocks.sql`，在`shadowsocks`数据库中建立用户表`user`。

### 独立使用
如果想要数据库功能而不使用后台管理网站的话，可以对源代码的"multiuser.py"进行如下的修改：  
1.注释掉210行：
```
210   # self.stat_init(a_config, True)
```   

2.取消211、212、213行前的注释：
```
211   aa_config = shell.make_config(a_config, False)
212   self.add_user(aa_config)
213   self.add_port(aa_config)
```
3.取消217行前的注释：
```
217   self.remove_user(a_config)
```

其余的使用方法不变。

Documentation
-------------

You can find all the documentation in the [Wiki].

License
-------

Apache License





[Build Status]:      https://img.shields.io/travis/shadowsocks/shadowsocks/master.svg?style=flat
[Coverage Status]:   https://jenkins.shadowvpn.org/result/shadowsocks
[Coverage]:          https://jenkins.shadowvpn.org/job/Shadowsocks/ws/PYENV/py34/label/linux/htmlcov/index.html
[PyPI]:              https://pypi.python.org/pypi/shadowsocks
[PyPI version]:      https://img.shields.io/pypi/v/shadowsocks.svg?style=flat
[Travis CI]:         https://travis-ci.org/shadowsocks/shadowsocks

