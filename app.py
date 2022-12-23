import flask
from flask import Flask, request, render_template
import requests
import copy

from python.BlockChain import BlockChain, FEE
from python.Wallet import Wallet
from python.Block import Block
from python.Transaction import Transaction

app = Flask(__name__)

if __name__ == '__main__':
    app.run()

SERVER_ADDRESS = "http://127.0.0.1:5000/"   # 节点服务器地址，用于获取邻居节点
LOCAL_ADDRESS = None    # 本地地址，注册成为节点时获得
peers = set()       # 邻居节点
blockchain = BlockChain()   # 本地区块链
wallet = Wallet()   # 本地钱包


# 重定向到/index
@app.route('/', methods=['GET'])
def redirect():
    return flask.redirect("/index")


# 返回并显示模板index.html
@app.route('/index', methods=['GET'])
def index():
    return render_template("index.html")


# 注册成为节点
@app.route('/register', methods=['GET'])
def register():
    global LOCAL_ADDRESS
    LOCAL_ADDRESS = request.host_url if LOCAL_ADDRESS is None else LOCAL_ADDRESS
    data = {"address": request.host_url}
    try:
        res = requests.post(SERVER_ADDRESS + "register", json=data)     # 向节点服务器发送请求
    except:
        return "目标服务器拒绝连接"
    # 请求成功
    if res.status_code == 200:
        global peers
        p = res.json()['peers']
        peers = set(p)
        peers.discard(LOCAL_ADDRESS)    # 邻居节点中要删除自己
        return "注册成功"
    else:
        return "注册失败"


# 查看邻居节点
@app.route('/peers', methods=['GET'])
def view_peers():
    return render_template("peers.html", peers=list(peers))


# 更新邻居节点
@app.route('/update_peers', methods=['GET'])
def update_peers():
    global LOCAL_ADDRESS
    LOCAL_ADDRESS = request.host_url if LOCAL_ADDRESS is None else LOCAL_ADDRESS
    try:
        res = requests.get(SERVER_ADDRESS + "update")
    except:
        return "目标服务器拒绝连接"
    if res.status_code == 200:
        global peers
        length = len(peers)
        p = res.json()['peers']
        peers = set(p)
        peers.discard(LOCAL_ADDRESS)
        return "更新邻居节点成功, 新增{}个邻居节点".format(len(peers)-length)
    else:
        return "更新邻居节点失败"


# 查看本地区块链
@app.route('/chain', methods=['GET'])
def view_chain():
    chain = get_chain()
    return render_template("chain.html", chain=chain)


# 获取本地区块链
@app.route('/get_chain', methods=['GET'])
def get_chain():
    global blockchain
    blockchain.chain.sort(key=lambda b: b.timestamp)    # 发送之前排序确保区块顺序正确
    # 发送之前要先将区块链转换为可以网络传输的字典格式
    chain = []
    for block in blockchain.chain:
        block_dict = block_to_dict(block)   # 将区块转化为字典格式
        chain.append(block_dict)
    return chain


# 依据最长链原则更新本地区块链
@app.route('/update_chain', methods=['GET'])
def update_chain():
    global blockchain, peers
    length = len(blockchain.chain)
    # 向邻居节点发送获取区块链的请求
    for p in peers:
        try:
            res = requests.get(p + "get_chain")
        except:
            continue
        chain = res.json()
        # 如果区块链长度大于本地区块链，验证区块链是否正确
        if len(chain) > length:
            chain.sort(key=lambda b: b["timestamp"])
            flag = True
            _chain = []
            for block_dict in chain:
                block = dict_to_block(block_dict)   # 将字典格式转化为Block格式
                if not is_valid_block(block, _chain):   # 验证当前区块是否正确
                    flag = False
                    break
                _chain.append(block)
            if flag:
                blockchain.chain = _chain
    return "更新区块链成功，新增{}个区块。".format(len(blockchain.chain) - length)


# 查看当前交易池
@app.route('/view_transaction', methods=['GET'])
def view_transaction():
    transaction = []
    for t in blockchain.transaction:
        transaction.append(t.__dict__)
    return render_template("transaction_pool.html", transaction=transaction)


# 挖矿
@app.route('/mine', methods=['GET'])
def mine():
    global blockchain, peers, wallet
    block = blockchain.proof_of_work(wallet.get_address())  # 通过工作量证明机制封装block
    block_dict = block_to_dict(block)
    t = 0   # 统计验证通过的邻居节点的个数
    content = []
    # 使邻居节点验证区块是否正确
    for p in peers:
        try:
            res = requests.post(p + "verify_block", json=block_dict)
        except:
            content.append((p, "已下线"))
            continue
        if res.status_code == 201:
            t = t + 1
            content.append((p, res.text))
        elif res.status_code == 400:
            content.append((p, res.text))
    # 至少一个邻居节点验证通过，交易才算有效
    if t > 0:
        # 从本地交易池中丢弃已被封装成block的交易
        for t1 in block.transaction:
            for i in range(len(blockchain.transaction) - 1, -1, -1):
                if t1.timestamp == blockchain.transaction[i].timestamp:
                    blockchain.transaction.pop(i)
        blockchain.chain.append(block)  # 将区块加入到本地区块链
        return render_template("mine_result.html", content=content, success=True)
    else:
        return render_template("mine_result.html", content=content, success=False)


# 验证区块
@app.route('/verify_block', methods=['POST'])
def verify_block():
    block_dict = request.json
    block = dict_to_block(block_dict)
    if is_valid_block(block):
        global blockchain
        # 从本地交易池中丢弃已被封装成block的交易
        for t1 in block.transaction:
            for i in range(len(blockchain.transaction) - 1, -1, -1):
                if t1.timestamp == blockchain.transaction[i].timestamp:
                    blockchain.transaction.pop(i)
        blockchain.chain.append(block)  # 将区块加入到本地区块链
        return "区块有效", 201
    else:
        return "区块无效", 400


# 交易界面
@app.route('/transaction', methods=['GET'])
def begin_transaction():
    return render_template("transaction.html", money=wallet.get_money(blockchain.chain))


# 使邻居节点验证交易
@app.route('/deal_transaction', methods=['POST'])
def deal_transaction():
    global wallet, peers, blockchain
    transaction_data = request.form
    transaction = Transaction(wallet.get_address(), transaction_data.get("recipient"),
                              float(transaction_data.get("amount")), wallet.get_public_key())
    transaction.set_sig(wallet.sign(transaction.get_message()))
    t = 0   # 统计验证通过的邻居节点的个数
    content = []
    # 使邻居节点验证交易
    for p in peers:
        try:
            res = requests.post(p + "verify_transaction", json=transaction.__dict__)
        except:
            content.append((p, "已下线"))
            continue
        if res.status_code == 201:
            t += 1
            content.append((p, res.text))
        elif res.status_code == 400:
            content.append((p, res.text))
    # 至少一个邻居节点验证通过，交易才算有效
    if t > 0:
        blockchain.transaction.append(transaction)  # 将交易添加到交易池中
        return render_template("transaction_result.html", content=content, success=True)
    else:
        return render_template("transaction_result.html", content=content, success=False)


# 验证交易
@app.route('/verify_transaction', methods=['POST'])
def verify_transaction():
    transaction_data = request.json
    transaction = Transaction(transaction_data["sender"], transaction_data["recipient"],
                              transaction_data["amount"], transaction_data["public_key"],
                              transaction_data["signature"], transaction_data["timestamp"])
    # 验证交易是否有效
    if is_valid_transaction(transaction):
        global blockchain
        blockchain.transaction.append(transaction)  # 将交易添加到交易池中
        return "交易有效", 201
    else:
        return "交易无效", 400


# 获取本地钱包信息
@app.route('/wallet', methods=['GET'])
def wallet_info():
    global blockchain, wallet
    money = wallet.get_money(blockchain.chain)  # 计算钱包金额
    # 处理并显示交易记录
    transaction_list = []
    for t in wallet.transaction:
        transaction_list.append([t.sender, t.recipient, t.amount])
    return render_template("wallet.html", money=money, transaction=transaction_list,
                           address=wallet.get_address())


# 验证交易是否有效
def is_valid_transaction(transaction, _chain=None):
    # _chain表示区块链，主要用于判断发送方的金额是否充足
    if _chain is None:
        global blockchain
        _chain = blockchain.chain
    # 判断交易的发送方地址与公匙计算出的地址是否相同，防止公匙被篡改
    if not transaction.sender == wallet.get_address(transaction.public_key):
        return False
    # 验证签名是否正确，防止交易信息被修改
    if not wallet.verify_sign(transaction.public_key, transaction.get_message(), transaction.signature):
        return False
    # 判断发送方已有金额是否足以支付交易金额
    sender = transaction.sender
    amount = 0
    for block in _chain:
        for t in block.transaction:
            if t.sender == sender:
                amount -= t.amount
            elif t.recipient == sender:
                if t.sender == "":
                    amount += t.amount
                else:
                    amount += t.amount * (1 - FEE)
    if round(amount, 10) < round(transaction.amount, 10):
        return False
    return True


# 验证区块是否有效
def is_valid_block(block, _chain=None):
    # _chain表示区块链，主要用于判断当前区块的pre_hash是否等于区块链最后一个区块的hash
    if _chain is None:
        global blockchain
        _chain = blockchain.chain
    t = 0   # 统计每个区块的矿工费交易的个数，应为1
    for transaction in block.transaction:
        if transaction.sender == "":
            t += 1
            if t > 1:
                return False
        else:
            if not is_valid_transaction(transaction, _chain):   # 验证区块中包含的交易是否有效
                return False
    # 验证区块的merkel值是否正确，防止交易被修改
    if not block.merkel == block.get_merkel(block.transaction):
        return False
    # 验证区块的pre_hash是否等于区块链最后一个区块的hash值
    if not block.pre_hash == _chain[-1].get_hash() if len(_chain) > 0 else 0:
        return False
    # 验证区块的hash值是否满足难度值，防止区块头信息被修改
    prefix = '0' * block.get_difficulty()
    if not block.get_hash().startswith(prefix):
        return False
    return True


# 将Block类型转换为dict类型
def block_to_dict(_block):
    block = copy.deepcopy(_block)
    # 将区块中的交易转换为dict类型
    transaction_dict = []
    for t in block.transaction:
        transaction_dict.append(t.__dict__)
    block_dict = block.__dict__
    block_dict["transaction"] = transaction_dict
    return block_dict


# 将dict类型转换为Block类型
def dict_to_block(block_dict):
    transaction_dict = block_dict["transaction"]
    transaction = []
    for t in transaction_dict:
        transaction.append(Transaction(t["sender"], t["recipient"], t["amount"],
                                       t["public_key"], t["signature"], t["timestamp"]))
    block = Block(transaction, block_dict["pre_hash"], block_dict["timestamp"],
                  block_dict["nonce"], block_dict["merkel"])
    return block