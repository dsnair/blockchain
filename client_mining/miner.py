import hashlib
import requests
import json
import sys

# Implement functionality to validate proof 
def valid_proof(block_string, proof):
    """
    Validates the Proof:  Does hash(last_block_string, proof) contain 6
    leading zeroes?
    
    :param proof: <string> The proposed proof
    :return: <bool> Return true if the proof is valid, false if it is not
    """
    guess = f'{block_string}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()

    return guess_hash[:6] == '000000'


if __name__ == '__main__':
    # What node are we interacting with?
    if len(sys.argv) > 1:
        node = sys.argv[1]
    else:
        node = 'http://localhost:5000'
    print('NODE', node)

    coins_mined = 0
    
    while True:
        # Request the latest proof from the `last_block` endpoint on the server
        response = requests.get(f'{node}/last_block')
        last_block = response.json()

        # Run `valid_proof()` until a valid proof is found, validating or rejecting each attempt
        block_string = json.dumps(last_block, sort_keys=True).encode()

        proof = 0
        print("Started validating proof ...")
        while not valid_proof(block_string, proof):
            proof += 1
        print("Finished validating proof.")
        print("PROOF", proof)

        # When a valid proof is found, POST it to the `mine` endpoint as {'proof': new_proof}
        response = requests.post(f'{node}/mine', data={'proof': proof})
        print('STATUS', response.status_code)

        # On success, increment coin total by 1
        if response.status_code == 200:
            coins_mined += 1
        print("COINS", coins_mined)

        if coins_mined > 5:
            break