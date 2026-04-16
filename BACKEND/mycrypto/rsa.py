import secrets

smallPrime = [3,5,7,11,13,17,19,23,29]

def generateLargeNumber():
    value = secrets.randbits(1024)#128 bytes
    value = value | (1<<1023)
    value = value | 1
    return value

def millerRabin(value):
    r = -1
    d = value - 1
    while d % 2 == 0:
        d //= 2
        r += 1

    a = secrets.randbelow(value-3) + 2

    x = pow(a,d,value)
    if x == 1 or x == value-1:
        return True
    while r!=0:
        x = pow(x,2,value)
        r -= 1
        if x == value - 1:
            return True
        if x == value -1:
            return False
    return False

def isLargePrime(value):
    for x in smallPrime:
        if value % x == 0:
            return False
    for _ in range(40):
        if millerRabin(value) == True:
            continue
        return False
    return True

def generateLargePrime():
    while True:
        p = generateLargeNumber()
        if isLargePrime(p) == False:
            continue
        break;
    return p

def generatePairKey():
    p = generateLargePrime()
    while True:
        q = generateLargePrime()
        if q == p:
            continue
        break
    
    n = p*q
    phi = (p-1)*(q-1)
    e = 65537
    d = pow(e,-1,phi)

    publicKey = (e,n)
    privateKey = (d,n)
    return publicKey, privateKey

def encrypt(message,publicKey):
    e, n = publicKey
    cipher = pow(message,e,n)
    return cipher

def decrypt(message, privateKey):
    d, n = privateKey
    plain = pow(message,d,n)
    return plain