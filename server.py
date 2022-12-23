import copy

from flask import Flask, request

app = Flask(__name__)

if __name__ == '__main__':
    app.run()

peers = set()


@app.route('/register', methods=['POST'])
def register_new_node():
    global peers
    address = request.json["address"]
    peers.add(address)
    return {
        "peers": list(peers)
    }


@app.route('/update', methods=['GET'])
def update_peers():
    global peers
    return {
        "peers": list(peers)
    }