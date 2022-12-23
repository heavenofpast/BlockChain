import time


class Transaction:
    def __init__(self, sender, recipient, amount, public_key=None, signature=None, timestamp=None):
        self.sender = sender    # 发送方地址
        self.recipient = recipient  # 接收方地址
        self.amount = round(amount, 6)  # 交易金额

        self.public_key = public_key    # 发送方公匙
        self.signature = signature      # 交易的签名
        self.timestamp = str(time.time()) if timestamp is None else timestamp   # 交易产生的时间，用于唯一确定交易

    # 获取要签名的信息
    def get_message(self):
        return "sender:{}, recipient:{}, amount:{}, timestamp:{}"\
            .format(self.sender, self.recipient, self.amount, self.timestamp)

    def set_sig(self, signature):
        self.signature = signature