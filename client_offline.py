import pickle
from oprf import client_prf_offline, order_of_generator, G
from time import time

# client's PRF secret key (a value from  range(order_of_generator))
oprf_client_key = 12345678910111213141516171819222222222222
t0 = time()

# key * generator of elliptic curve
client_point_precomputed = (oprf_client_key % order_of_generator) * G

client_set = []
f = open('client_set', 'r')
lines = f.readlines()
for item in lines:
	client_set.append(int(item[:-1]))
f.close()

# OPRF layer: encode the client's set as elliptic curve points.
encoded_client_set = [client_prf_offline(item, client_point_precomputed) for item in client_set]

g = open('client_preprocessed', 'wb')
pickle.dump(encoded_client_set, g)	 
g.close()   
t1 = time()
print('Client OFFLINE time: {:.2f}s'.format(t1-t0))

# ------------------------------
my_file = open('our_results', 'a')
my_file.write("C_offline " + str(t1 - t0) + '\n')
my_file.close()