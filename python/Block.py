import copy
from datetime import datetime
import hashlib


class Block:
    def __init__(self, transaction=[], pre_hash=0, timestamp=None, nonce=None, merkel=None):
        self.transaction = transaction  # 区块中包含的交易列表
        self.pre_hash = pre_hash  # 前一个区块的hash值
        self.version = self.get_version()  # 版本号
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if timestamp is None else timestamp  # 时间戳
        self.difficulty = self.get_difficulty()  # 当前难度值
        self.nonce = 0 if nonce is None else nonce  # 随机值，不断改变用于找到满足难度值的hash值
        self.merkel = self.get_merkel(transaction) if merkel is None else merkel  # 该区块所有交易经过某种运算得到的值

    def get_version(self):  # 获得版本号
        return 0

    def get_difficulty(self):  # 获得当前难度值
        return 4

    def get_merkel(self, _transaction):  # 计算merkel值
        transaction = copy.deepcopy(_transaction)
        transaction.sort(key=lambda t: t.amount, reverse=True)  # 交易进行排序，确保顺序正确
        # 对某个交易先进行一次sha256
        for index, t in enumerate(transaction):
            h = hashlib.sha256()
            h.update(str(t.sender).encode('utf-8'))
            h.update(str(t.recipient).encode('utf-8'))
            h.update(str(t.amount).encode('utf-8'))
            transaction[index] = h.hexdigest()
        # 每两个交易合并求一次sha256
        while len(transaction) > 1:
            if len(transaction) % 2 != 0:
                transaction.append(transaction[len(transaction) - 1])
            l = []
            for i in range(len(transaction) // 2):
                t1 = transaction.pop()
                t2 = transaction.pop()
                l.append(hashlib.sha256((str(t1) + str(t2)).encode('utf-8')).hexdigest())
            transaction = l
        return transaction[0] if len(transaction) > 0 else 0

    # 计算区块头的hash值
    def get_hash(self):
        h = hashlib.sha256()
        h.update(str(self.pre_hash).encode('utf-8'))
        h.update(str(self.version).encode('utf-8'))
        h.update(str(self.timestamp).encode('utf-8'))
        h.update(str(self.difficulty).encode('utf-8'))
        h.update(str(self.nonce).encode('utf-8'))
        h.update(str(self.merkel).encode('utf-8'))
        return h.hexdigest()