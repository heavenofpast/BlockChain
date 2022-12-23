import base64
import binascii

from ecdsa import SigningKey, SECP256k1, VerifyingKey
import hashlib
from python.BlockChain import FEE


class Wallet:
    def __init__(self):
        self.private_key = SigningKey.generate(curve=SECP256k1)     # 私匙
        self.public_key = self.private_key.get_verifying_key()      # 公匙
        self.transaction = []   # 与该地址有关的交易
        self.chain_len = 0      # 已遍历的区块链长度
        self.amount = 0     # 钱包包含的金额

    # 根据公匙计算交易地址
    def get_address(self, public_key=None):
        if public_key is None:
            public_key = self.get_public_key()
        h = hashlib.sha256(public_key.encode('utf-8'))
        return base64.b64encode(h.digest()).decode('utf-8')

    # 获取公匙
    def get_public_key(self):
        return self.public_key.to_pem().decode('utf-8')

    # 计算钱包的金额
    def get_money(self, chain):
        # 若该区块链已遍历过，则无需再次遍历，直接返回钱包金额
        if len(chain) == self.chain_len:
            return self.amount
        # 遍历区块链计算钱包金额
        money = 0
        self.transaction = []
        for block in chain:
            for t in block.transaction:
                if t.sender == self.get_address():
                    self.transaction.append(t)
                    money -= t.amount
                elif t.recipient == self.get_address():
                    self.transaction.append(t)
                    if t.sender == "":
                        money += t.amount
                    else:
                        money += t.amount * (1 - FEE)   # 计算金额时要减掉矿工费
        self.chain_len = len(chain)
        self.amount = round(money, 10)
        return self.amount

    # 签名，给交易信息签名
    def sign(self, message):
        h = hashlib.sha256(message.encode('utf-8'))
        return binascii.hexlify(self.private_key.sign(h.digest())).decode('utf-8')

    # 验证签名，根据公匙，交易信息和签名
    def verify_sign(self, public_key, message, signature):
        verifier = VerifyingKey.from_pem(public_key)
        h = hashlib.sha256(message.encode('utf-8'))
        try:
            verifier.verify(binascii.unhexlify(signature.encode('utf-8')), h.digest())
            return True
        except:
            return False
