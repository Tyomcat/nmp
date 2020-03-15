## Project Nmp

### 环境准备

```bash
$ git clone https://github.com/Project-Nmp/nmp.git
$ cd nmp
$ python3.7 -m venv .env
$ source .env/bin/activate
$ python setup.py develop
```

### 服务启动

- 启动服务端

```bash
$ nmp server
```

- 启动本地 socks 服务

```bash
$ nmp socks
```

### 打包上传

```bash
$ python setup.py sdist bdist_wheel
$ python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```


### TODO

- dummy 数据随机生成 p0
- 客户端从 api server 动态更新 encoder p0
- api server UUID 权限认证 p1
- 易用性完善，参数配置化 p1
- daemon 进程，进程优雅退出 p1
- 线程池，事件驱动替换当前模型 p2
- 单元测试，集成测试体系引入 p2
- kcp 协议集成 p3
- 英文版文档 p3
