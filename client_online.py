import tenseal as ts
from time import time
import socket
import pickle
from math import log2
from parameters import sigma_max, output_bits, plain_modulus, poly_modulus_degree, number_of_hashes, bin_capacity, alpha, ell, hash_seeds
from cuckoo_hash import reconstruct_item, Cuckoo
from auxiliary_functions import windowing
from oprf import order_of_generator, client_prf_online_parallel

oprf_client_key = 12345678910111213141516171819222222222222

log_no_hashes = int(log2(number_of_hashes)) + 1
base = 2 ** ell
minibin_capacity = int(bin_capacity / alpha)
logB_ell = int(log2(minibin_capacity) / ell) + 1 # <= 2 ** HE.depth
dummy_msg_client = 2 ** (sigma_max - output_bits + log_no_hashes)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 4470))

# Setting the public and private contexts for the BFV Homorphic Encryption scheme
private_context = ts.context(ts.SCHEME_TYPE.BFV, poly_modulus_degree=poly_modulus_degree, plain_modulus=plain_modulus)
public_context = ts.context_from(private_context.serialize())
public_context.make_context_public()

# We prepare the partially OPRF processed database to be sent to the server
pickle_off = open("client_preprocessed", "rb")
encoded_client_set = pickle.load(pickle_off)
encoded_client_set_serialized = pickle.dumps(encoded_client_set, protocol=None)

L = len(encoded_client_set_serialized)
sL = str(L) + ' ' * (10 - len(str(L)))
client_to_server_communiation_oprf = L #in bytes
# The length of the message is sent first
client.sendall((sL).encode())
client.sendall(encoded_client_set_serialized)

L = client.recv(10).decode().strip()
L = int(L, 10)

PRFed_encoded_client_set_serialized = b""
while len(PRFed_encoded_client_set_serialized) < L:
    data = client.recv(4096)
    if not data: break
    PRFed_encoded_client_set_serialized += data   
PRFed_encoded_client_set = pickle.loads(PRFed_encoded_client_set_serialized)
t0 = time()
server_to_client_communication_oprf = len(PRFed_encoded_client_set_serialized)

# We finalize the OPRF processing by applying the inverse of the secret key, oprf_client_key
key_inverse = pow(oprf_client_key, -1, order_of_generator)
PRFed_client_set = client_prf_online_parallel(key_inverse, PRFed_encoded_client_set)
print(' * OPRF protocol done!')

# Each PRFed item from the client set is mapped to a Cuckoo hash table
CH = Cuckoo(hash_seeds)
for item in PRFed_client_set:
    CH.insert(item)

# We padd the Cuckoo vector with dummy messages
for i in range(CH.number_of_bins):
    if (CH.data_structure[i] == None):
        CH.data_structure[i] = dummy_msg_client

# We apply the windowing procedure for each item from the Cuckoo structure
windowed_items = []
for item in CH.data_structure:
    windowed_items.append(windowing(item, minibin_capacity, plain_modulus))

plain_query = [None for k in range(len(windowed_items))]
enc_query = [[None for j in range(logB_ell)] for i in range(1, base)]

# We create the <<batched>> query to be sent to the server
# By our choice of parameters, number of bins = poly modulus degree (m/N =1), so we get (base - 1) * logB_ell ciphertexts
for j in range(logB_ell):
    for i in range(base - 1):
        if ((i + 1) * base ** j - 1 < minibin_capacity):
            for k in range(len(windowed_items)):
                plain_query[k] = windowed_items[k][i][j]
            enc_query[i][j] = ts.bfv_vector(private_context, plain_query)

enc_query_serialized = [[None for j in range(logB_ell)] for i in range(1, base)]
for j in range(logB_ell):
    for i in range(base - 1):
        if ((i + 1) * base ** j - 1 < minibin_capacity):
            enc_query_serialized[i][j] = enc_query[i][j].serialize()

context_serialized = public_context.serialize()
message_to_be_sent = [context_serialized, enc_query_serialized]
message_to_be_sent_serialized = pickle.dumps(message_to_be_sent, protocol=None)
t1 = time()
L = len(message_to_be_sent_serialized)
sL = str(L) + ' ' * (10 - len(str(L)))
client_to_server_communiation_query = L 
#the lenght of the message is sent first
client.sendall((sL).encode())
print(" * Sending the context and ciphertext to the server....")
# Now we send the message to the server
client.sendall(message_to_be_sent_serialized)

print(" * Waiting for the servers's answer...")

# The answer obtained from the server:
L = client.recv(10).decode().strip()
L = int(L, 10)
answer = b""
while len(answer) < L:
    data = client.recv(4096)
    if not data: break
    answer += data
t2 = time()
server_to_client_query_response = len(answer) #bytes
# Here is the vector of decryptions of the answer
ciphertexts = pickle.loads(answer)
decryptions = []
for ct in ciphertexts:
    decryptions.append(ts.bfv_vector_from(private_context, ct).decrypt())

recover_CH_structure = []
for matrix in windowed_items:
    recover_CH_structure.append(matrix[0][0])

count = [0] * alpha

g = open('client_set', 'r')
client_set_entries = g.readlines()
g.close()
client_intersection = []
for j in range(alpha):
    for i in range(poly_modulus_degree):
        if decryptions[j][i] == 0:
            count[j] = count[j] + 1

            # The index i is the location of the element in the intersection
            # Here we recover this element from the Cuckoo hash structure
            PRFed_common_element = reconstruct_item(recover_CH_structure[i], i, hash_seeds[recover_CH_structure[i] % (2 ** log_no_hashes)])
            index = PRFed_client_set.index(PRFed_common_element)
            client_intersection.append(int(client_set_entries[index][:-1]))

h = open('intersection', 'r')
real_intersection = [int(line[:-1]) for line in h]
h.close()
t3 = time()
print('\n Intersection recovered correctly: {}'.format(set(client_intersection) == set(real_intersection)))
print("Disconnecting...\n")
print('  Client ONLINE computation time {:.2f}s'.format(t1 - t0 + t3 - t2))
print('  Communication size:')
print('    ~ Client --> Server:  {:.2f} MB'.format((client_to_server_communiation_oprf + client_to_server_communiation_query )/ 2 ** 20))
print('    ~ Server --> Client:  {:.2f} MB'.format((server_to_client_communication_oprf + server_to_client_query_response )/ 2 ** 20))
client.close()

# ------------------------------
my_file = open('our_results', 'a')
my_file.write('Client ONLINE computation time {:.2f}s'.format(t1 - t0 + t3 - t2)+'\n')
my_file.write('Client --> Server:  {:.2f} MB'.format((client_to_server_communiation_oprf + client_to_server_communiation_query )/ 2 ** 20)+'\n')
my_file.write('Server --> Client:  {:.2f} MB'.format((server_to_client_communication_oprf + server_to_client_query_response )/ 2 ** 20)+'\n')
my_file.write('-------------------------------------------------')
my_file.close()