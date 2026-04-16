import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from mycrypto.rsa import generatePairKey

def main():
    publicKey, privateKey = generatePairKey()

