import copy

from python.Block import Block
from python.Transaction import Transaction

FEE = 0.001     # 每笔交易提供的矿工费比例


class BlockChain:
    def __init__(self):
        self.chain = []  # 包含所有有效的区块
        self.transaction = []   # 还未被打包成区块的交易池

    # 矿工费
    def get_mine_fee(self):
        return 100

    # 从交易池中选择若干个交易
    def get_transaction(self, address, max_num=5):
        self.transaction.sort(key=lambda t: t.amount, reverse=True)
        if len(self.transaction) < max_num:
            transaction = copy.deepcopy(self.transaction)
        else:
            transaction = copy.deepcopy(self.transaction[:max_num])
        # 计算矿工费
        fee = 0
        for t in transaction:
            f = t.amount * FEE
            fee += f
        # 每个区块的第一笔交易，用于保存矿工费
        t = Transaction("", address, round(fee + self.get_mine_fee(), 10))
        transaction.append(t)
        return transaction

    # 工作量证明机制
    def proof_of_work(self, address):
        transaction = self.get_transaction(address, 5)
        block = Block(transaction, self.chain[-1].get_hash() if len(self.chain) > 0 else 0)
        # 计算区块的hash值开头包含若干0的nonce
        prefix = '0' * block.get_difficulty()
        nonce = block.nonce
        while True:
            nonce += 1
            block.nonce = nonce
            h = block.get_hash()
            if h.startswith(prefix):
                return block