import hashlib
import json

from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        if len(self.chain) == 0:
            self.create_genesis_block()

    def create_genesis_block(self):
        """
        Create genesis block and add it to the chain
        """

        block = {
            'index': 1,
            'timestamp': 0,
            'transactions': [],
            'proof': 42,
            'previous_hash': 1
        }

    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block in the Blockchain

        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: <str> Address of the Recipient
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the BLock that will hold this transaction
        """

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block": <dict> Block
        "return": <str>
        """

        # We must make sure that the Dictionary is Ordered,
        # or we'll have inconsistent hashes

        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def valid_proof(block_string, proof):
        """
        Validates the Proof:  Does hash(last_block_string, proof) contain 6
        leading zeroes?
        
        :param proof: <string> The proposed proof
        :return: <bool> Return true if the proof is valid, false if it is not
        """
        guess = f'{block_string}{proof}'.encode()
        # hexdigest converts to hexadecimal
        guess_hash = hashlib.sha256(guess).hexdigest()

        # TODO: change back to guess_hash[:6] == '000000'
        # Lowering required leading zeroes to 4 for fast testing
        return guess_hash[:4] == '0000'

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid

        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        prev_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{prev_block}')
            print(f'{block}')
            print("\n-------------------\n")
            # Check that the hash of the block is correct:
            # Return false if hash isn't correct
            if block['previous_hash'] != self.hash(prev_block):
                return False

            # Check that the Proof of Work is correct:
            # Return false if proof isn't correct
            block_string = json.dumps(prev_block, sort_keys=True).encode()
            
            if not self.valid_proof(block_string, block["proof"]):
                return False

            prev_block = block
            current_index += 1

        return True

    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def broadcast_new_block(self, new_block):
        neighbors = self.nodes
        post_data = {'block': new_block}

        for node in neighbors:
            response = request.post(f'http://{node}/block/new', json=post_data)

            if response.status_code != 200:
                # Error handling
                pass


# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['POST'])
def mine():
    # request.form() is a Flask method. It receives 'proof' from client
    proof = request.get_json()['proof']
    print('PROOF in POST /mine', proof)

    # Check if proof is valid. Return success/failure message
    block_string = json.dumps(blockchain.last_block, sort_keys=True).encode()

    if blockchain.valid_proof(block_string, proof):
        # We must receive a reward for finding the proof:
        # The sender is "0" to signify that this node has mine a new coin
        # The recipient is the current node, it did the mining!
        # The amount is 1 coin as a reward for mining the next block
        blockchain.new_transaction(0, node_identifier, 1)

        # Forge the new Block by adding it to the chain
        last_block_hash = blockchain.hash(blockchain.last_block)
        block = blockchain.new_block(proof, last_block_hash)

        response = {
            'message': 'New Block Forged',
            'index': block['index'],
            'transactions': block['transactions'],
            'proof': block['proof'],
            'previous_hash': block['previous_hash'],
        }
        return jsonify(response), 200
    else:
        response = {
            'message': 'You provided an invalid proof.'
        }
        return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing Values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'],
                                       values['recipient'],
                                       values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        # Return the chain and its current length
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/chain_validity', methods=['GET'])
def chain_validity():
    response = {
        'valid_chain': blockchain.valid_chain(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/last_block', methods=['GET'])
def last_proof():
    response = {
        'last_block': blockchain.last_block
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    nodes = request.get_json()['nodes']

    if nodes is None:
        return "Error: please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': "New nodes have been added.",
        'total_nodes': list(blockchain.nodes)
    }

    return jsonify(response), 200


@app.route('/block/new', methods=['POST'])
def receive_block():
    new_block = request.get_json()['block']

    # TODO: Validate that it's a peer in the network

    # Check index of block and make sure it's 1 greater than previous
    old_block = blockchain.last_block

    if new_block['index'] == old_block['index'] + 1:
        # Index is correct
        if new_block['previous_hash'] == blockchain.hash(old_block):
            # Hash is good
            block_string = json.dumps(old_block, sort_keys=True).encode()
            if blockchain.valid_proof(block_string, new_block['proof']):
                # Proof is valid
                print("New block accepted.")
                blockchain.add(new_block)
                return 'Block Accepted', 200
            else:
                # Bad proof
                pass
        else:
            # Hashes don't match
            pass
    else:
        # Index is more than 1 greater
        # Block may be invalid, or may be behind
        # Do consensus process
        # Ask all of the nodes in our network for their chains
        # Check their lengths and replace ours with the longest valid chain
        pass


# Run the program on port 5000
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)