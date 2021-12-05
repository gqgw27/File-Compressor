import math,os,time
import json
import sys

surround = (' ','.',',','!','?',':',';','(',')','{','}','[',']','_','\\','/','\n','\r','"',"'",'\t','$','=','^','&')
surround_dict = {s:None for s in surround}

with open('wordConversion.json','r') as f:
    wordConversion = json.load(f)

wordToCode = wordConversion['wtc']
codeToWord = wordConversion['ctw']
del wordConversion

def splitByWord(string):
    splitted = []
    current = ''
    for c in string:
        if c in surround_dict:
            if current != '':
                splitted.append(current)
            current = ''
            splitted.append(c)
        else:
            current += c
    return splitted + [current]

def alphaDecode(msg):
    msg_split = splitByWord(msg)

    new = []
    for word in msg_split:
        if word[:3] in codeToWord:
            for i in range(0,len(word),3):
                new.append(codeToWord[word[i:i+3]])
                new.append(' ')
            del new[-1]
        else:
            new.append(word)

    return ''.join(new)

def bwtDecode(index, encoded):
    total = len(encoded)
    F = []
    for i in range(total):
        F.append((i,encoded[i]))
    F.sort(key=lambda x:x[1])

    T = [None]*total
    for i in range(total):
        T[F[i][0]] = i

    decoded = []
    for i in range(total):
        decoded.append(encoded[index])
        index = T[index]
        
    decoded.reverse()
    return ''.join(decoded)

def mtfDecode(encoded):
    chars = [chr(n) for n in range(256)]
    decoded= ''
    for n in [ord(s) for s in encoded]:
        s = chars[n]
        decoded += s
        del chars[n]
        chars.insert(0,s)
        
    return decoded

def arthDecode(encoded, probs):
    # Generating cummalative probabilities
    cumProbs = {}
    current = 0
    for k in probs:
        current += probs[k]
        cumProbs[k] = current
    prob_keys = list(probs.keys())

    total = current
    num_bits = math.ceil(math.log(4*total,2))

    # Decoding
    decoded = ''
    low = 0
    high = 2**num_bits - 1
    mid = 2**(num_bits - 1)
    lquart = 2**(num_bits - 2)
    uquart = 3*2**(num_bits - 2)

    tag = int(encoded[0:num_bits],2)
    btag = '0b'+bin(tag)[2:].zfill(num_bits)
    i = num_bits

    #pbar = tqdm(total=total)
    while len(decoded) < total:
        ftop = (tag-low+1)*total - 1
        fbot = high - low + 1
        val = ftop//fbot
        
        k = -1
        while True:
            if val >= (cumProbs[prob_keys[k]] if k > -1 else 0):
                k += 1
            else:
                break

        decoded += prob_keys[k]
        #pbar.update(1)
        if len(decoded) == total:
            #pbar.close()
            break
        
        s = prob_keys[k]
        diff = high - low + 1
        high = low + (diff*(cumProbs[s] if prob_keys.index(s) > -1 else 0)//total)-1
        low = low + (diff*((cumProbs[s]-probs[s]) if prob_keys.index(s) > 0 else 0)//total)

        while (high < mid) or (low >= mid) or ((low >= lquart) and (high < uquart)):
            if (high < mid):
                low = 2*low
                high = 2*high + 1
                tag = 2*tag + int(encoded[i])
                i += 1
                
            elif (low >= mid):
                low = 2*(low - mid)
                high = 2*(high - mid) + 1
                tag = 2*(tag - mid) + int(encoded[i])
                i += 1

            if (low >= lquart) and (high < uquart):
                low = 2*(low-lquart)
                high = 2*(high-lquart) + 1
                tag = 2*(tag-lquart) + int(encoded[i])
                i += 1
    return decoded


def extractEncoded(file):
    #file = open(name, 'rb').read()
    
    bitstream = ''
    for s in file:
        bitstream += bin(ord(s))[2:].zfill(8)

    key_bits = int(bitstream[:3],2) + 1
    val_bits = int(bitstream[3:8],2) + 1
    probs_length = int(bitstream[8:16],2) + 1
    probs_bit_length = probs_length*(key_bits+val_bits)
    
    probs = {}
    for i in range(16,16+probs_bit_length,key_bits+val_bits):
        key = chr(int(bitstream[i:i+key_bits],2))
        val = int(bitstream[i+key_bits:i+key_bits+val_bits],2)
        probs[key] = val

    start_index = 16 + probs_bit_length
    if start_index%8 != 0:
        start_index += (8-start_index%8)

    return bitstream[start_index:], probs

def RLDecode(encoded):
    id1 = chr(141)
    id2 = chr(142)
    id3 = chr(143)
    id4 = chr(144)

    decoded = ''
    i = 0
    while i < len(encoded):
        s = encoded[i]

        if s!= id1 and s!= id2 and s!= id3 and s!= id4:
            decoded += s
            i += 1
        elif s == id2:
            count = ord(encoded[i+1]) + 3
            decoded += chr(0)*count
            i += 2
        elif s == id1:
            decoded += chr(0)*2
            i += 1
        elif s == id3:
            decoded += encoded[i+1]*3
            i += 2
        else:
            count = ord(encoded[i+1]) + 4
            decoded += encoded[i+2]*count
            i += 3

    return decoded

##########################################################################
try:
    name = sys.argv[1][:-3]
    output = name+'-decoded.tex'
except:
    name = 'war'
    output = 'war-decoded.tex'
        
file = open(name+'.lz','r',encoding='latin1',newline='').read()
start = time.time()

#Getting indexes for BWT before Arth, RLE and Mtf decoding
batch_size = int(2**20.5 - 1)
index_bit_num = math.ceil(math.log(batch_size,2))

num_batches_bin = bin(ord(file[0]))[2:].zfill(8) + bin(ord(file[1]))[2:].zfill(8)
num_batches = int(num_batches_bin,2)
num_indexBytes = math.ceil((index_bit_num*num_batches)/8)

indexesBits = ''
for i in range(2,2+num_indexBytes):
    indexesBits += bin(ord(file[i]))[2:].zfill(8)

indexes = []
for i in range(0,num_batches*index_bit_num,index_bit_num):
    indexes.append(int(indexesBits[i:i+index_bit_num],2))

file = file[2+num_indexBytes:]



# Arithmetic decoding
encoded, probs = extractEncoded(file)
decoded = arthDecode(encoded, probs)
#print('Arth:',time.time()-start)


# RLE decoding
decoded = RLDecode(decoded)
#print('RLE:',time.time()-start)

# Mtf decoding
decoded = mtfDecode(decoded)
#print('Mtf:',time.time()-start)

# BWT decoding
decodedbwt = ''

for i in range(0,len(decoded),batch_size):
    index_num = i//batch_size
    index = indexes[index_num]
    decodedbwt += bwtDecode(index, decoded[i:i+batch_size])
#print('BWT:',time.time()-start)

# Alpha decoding
decoded = alphaDecode(decodedbwt)

#print('Total:',time.time()-start)
file = open(output,'w',encoding='latin1',newline='')
file.write(decoded)
file.close()

