#from tqdm import tqdm
import sys,json,math,time

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

def alphaEncode(msg):
    msg_split = splitByWord(msg)
    
    new = []
    for word in msg_split:
        if word in wordToCode:
            new.append(wordToCode[word])
        else:
            new.append(word)

    spaces = 0
    spaced = []
    index = 0
    previous = False
    partial = ''
    last = False
    while index < len(new)-2:
        word1 = new[index]
        word2 = new[index+1]
        word3 = new[index+2]
        if word1 in codeToWord and word2 == ' ' and word3 in codeToWord:
            index += 2
            if previous:
                partial += word3        
            else:
                previous = True
                partial += word1+word3
        else:
            index += 1
            if previous:
                spaced.append(partial)
                partial = ''
                previous = False
            else:
                spaced.append(word1)
    for i in range(index, len(new)):
        if previous:
            spaced.append(partial)
            partial = ''
            previous = False
            continue
        else:
            spaced.append(new[i])

    return ''.join(spaced)

def shift(msg2,i):
    return msg2[i:i+len(msg2)//2]

def shiftPart(msg2,i,p):
    return msg2[i:i+p],msg2[i+len(msg2)//2-1]

def bwtEncode(msg):
    search_size = 500
    full_length = len(msg)
    table = []
    msg2 = msg*2
    for i in range(full_length):
        shifted, last = shiftPart(msg2,i,search_size)
        table.append((shifted,last,i))
    table.sort()

    encoded = [None]*full_length
    sames = []
    gap = False
    start = 0
    for i in range(len(table)-1):
        if table[i][0] != table[i+1][0]:
            if gap:
                index_present = False
                if table[start][0] == msg[:search_size]:
                    index_present = True
                    
                current = []
                for x in range(start,i+1):
                    index = table[x][2]
                    current.append(shift(msg2,index))
                current.sort()
                
                if index_present:
                    index_val = start + current.index(msg)
                    #print('1) Index =',index_val)
                
                for x in range(len(current)):
                    encoded[start+x] = current[x][-1]

                gap = False
                start = 0
            else:
                encoded[i] = table[i][1]
                index = table[i][2]
                if index == 0:
                    index_val = i
                    #print('2) Index =',index_val)
        else:
            if not gap:
                start = i
                gap = True
                
    if not gap:
        encoded[i+1] = table[i+1][1]

        index = table[i+1][2]
        if index == 0:
            index_val = i+1
            #print('4) Index =',index_val)
        
    else:
        if table[start][0] == msg[:search_size]:
            index_present = True

        current = []
        for x in range(start,i+2):
            index = table[x][2]
            current.append(shift(msg2,index))
        current.sort()

        if index_present:
            index_val = start+current.index(msg)
            print('5) Index =',index_val)

        for x in range(len(current)):
            encoded[start+x] = current[x][-1]

    return index_val, ''.join(encoded)

def mtfEncode(string):
    chars = [chr(n) for n in range(256)]
    encodedMtf = []
    for s in string:
        index_val = chars.index(s)
        encodedMtf.append(index_val)
        del chars[index_val]
        chars.insert(0,s)

    return ''.join([chr(n) for n in encodedMtf])

def bitsToBytes(bits):
    if len(bits)%8 != 0:
        bits += '0'*(8-len(bits)%8)
    Bytes = ''
    for i in range(0,len(bits),8):
        Bytes += chr(int(bits[i:i+8],2))
    return Bytes

def RLEncode(msg):
    encoded = ''
    id1 = chr(141) # ==2 and 0
    id2 = chr(142) # >2 and 0
    id3 = chr(143) # ==3 and not 0
    id4 = chr(144) # >3 and not 0
    
    i = 0
    while i < len(msg):
        s = msg[i]
        count = 0
        
        upper = i+258 if i+258<len(msg) else len(msg)
        for x in range(i,upper):
            if msg[x] == s:
                count += 1
            else:
                break
        i += count

        if s == chr(0):
            if count < 2:
                encoded += s*count
            elif count > 2:
                encoded += id2+chr(count-3)
            else:
                encoded += id1
        else:
            if count < 3:
                encoded += s*count
            elif count > 3:
                encoded += id4+chr(count-4)+s
            else:
                encoded += id3+s

    return encoded

def arthEncode(msg):
    probs = {}

    for s in msg:
        if s not in probs:
            probs[s] = 1
        else:
            probs[s] += 1

    cumProbs = {}
    current = 0
    for k in probs:
        current += probs[k]
        cumProbs[k] = current
    prob_keys = list(probs.keys())
    total = current

    global low, high
    num_bits = math.ceil(math.log(4*total,2)) #if actual else 32
    low = 0
    high = 2**num_bits - 1
    mid = 2**(num_bits - 1)
    lquart = 2**(num_bits - 2)
    uquart = 3*2**(num_bits - 2)

    encoded = ''
    scale3 = 0

    for s in msg:
        diff = high - low + 1
        high = low + (diff*(cumProbs[s] if prob_keys.index(s) > -1 else 0)//total)-1
        low = low + (diff*((cumProbs[s]-probs[s]) if prob_keys.index(s) > 0 else 0)//total)

        while (high < mid) or (low >= mid) or ((low >= lquart) and (high < uquart)):
            if (high < mid):
                encoded += '0' # Send 0 bit
                low = 2*low
                high = 2*high + 1
                
                # E3 Logic, sending "1" bits
                while scale3 > 0:
                    encoded += '1'
                    scale3 -= 1
                
            elif (low >= mid):
                encoded += '1' # Send 1 bit
                low = 2*(low - mid)
                high = 2*(high - mid) + 1

                # E3 Logic, sending "0" bits
                while scale3 > 0:
                    encoded += '0'
                    scale3 -= 1

            if (low >= lquart) and (high < uquart):
                #print('E3')
                scale3 += 1
                low = 2*(low-lquart)
                high = 2*(high-lquart) + 1
                

    lowpad = bin(low)[2:].zfill(num_bits)
    encoded += lowpad[0]+'1'*scale3+lowpad[1:]

    if len(encoded)%8 != 0:
        encoded += '0'*(8-len(encoded)%8) # Padding to make length multiple of 8 

    return encoded, probs

def saveEncoded(encoded, probs):
    keys = [ord(k) for k in probs]
    vals = [probs[k] for k in probs]

    key_bits = int(math.log(max(keys),2)) + 1
    val_bits = int(math.log(max(vals),2)) + 1

    bitstream = bin(key_bits-1)[2:].zfill(3)  # 3 bits to store number of bits to encode key values (up to 8 bits)
    bitstream += bin(val_bits-1)[2:].zfill(5) # 5 bits to store number of bits to encoded values (up to 32 bits)
    bitstream += bin(len(probs)-1)[2:].zfill(8) # 8 bits to store number of items in dictionary (i.e. up to 256 characters in the file)
    
    for k in probs:
        bitstream += bin(ord(k))[2:].zfill(key_bits)
        bitstream += bin(probs[k])[2:].zfill(val_bits)

    if len(bitstream)%8 != 0:
        bitstream += '0'*(8-len(bitstream)%8)

    bitstream += encoded

    encoded_bytes = ''
    for i in range(0,len(bitstream),8):
        encoded_bytes += chr(int(bitstream[i:i+8],2))

    #file = open(name, 'wb')
    #file.write(encoded_bytes)
    #file.close()

    return encoded_bytes

#####################################################################################
try:
    name = sys.argv[1][:-4]
    output = name+'.lz'
except:
    name = 'Acts'
    output = 'Acts.lz'

msg = open(name+'.tex','r',newline='',encoding='latin1').read()
start1 = time.time()

#################################################
################ Alpha Encoding #################
msg = alphaEncode(msg)

#################################################
################# BWT Encoding ##################

batch_size = int(2**20.5-1)
index_bit_num = math.ceil(math.log(batch_size,2))

start = time.time()

encodedBatches = []
encodedIndexes = []
for i in range(0,len(msg),batch_size):
    #print(i,len(msg),100*round(i/len(msg),3),'Time:',time.time()-start)
    index, encoded = bwtEncode(msg[i:i+batch_size])
    if index != None:
        encodedBatches.append(encoded)
        encodedIndexes.append(index)

num_batches = math.ceil(len(msg)/batch_size)
num_batches_bin = bin(num_batches)[2:].zfill(16)
num_batches_bytes = bitsToBytes(num_batches_bin)

bwtencodedHeader = num_batches_bytes # 16 bits representing number of batches

indexesBits = ''
for index in encodedIndexes:
    indexesBits += bin(index)[2:].zfill(index_bit_num)
indexBytes = bitsToBytes(indexesBits)

bwtencodedHeader += indexBytes # bits representing index values for the batches

bwtencoded = ''
for x in encodedBatches:
    bwtencoded += x

#print('BWT:','✓', time.time()-start1)

#################################################
################# Mtf encoding ##################

encodedMtf = mtfEncode(bwtencoded)
#print('Mtf:','✓', time.time()-start1)

#################################################
################# RLE encoding ##################

encodedRun = RLEncode(encodedMtf)

#print('RLE:','✓', time.time()-start1)

#'''
#################################################
############### Arithmetic Encoding #############

#encoded, probs = arthEncode(bwtencodedHeader+encodedRun)
encoded, probs = arthEncode(encodedRun)
#print('Arithmetic:','✓', time.time()-start1)

encoded = saveEncoded(encoded, probs)
encoded = bwtencodedHeader + encoded

file = open(output,'w',newline='',encoding='latin1')
file.write(encoded)
file.close()

#print('Total:',time.time()-start1)
#'''
