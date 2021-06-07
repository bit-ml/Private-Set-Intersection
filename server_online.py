import socket
import tenseal as ts
import pickle
import numpy as np
from math import log2


from parameters import number_of_hashes, bin_capacity, alpha, ell, poly_modulus_degree

from auxiliary_functions import power_reconstruct
from oprf import server_prf_online_parallel

oprf_server_key = 1234567891011121314151617181920
from time import time

log_no_hashes = int(log2(number_of_hashes)) + 1
base = 2 ** ell
minibin_capacity = int(bin_capacity / alpha)
logB_ell = int(log2(minibin_capacity) / ell) + 1 # <= 2 ** HE.depth

serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serv.bind(('', 4770))
serv.listen(1)

g = open('server_preprocessed', 'rb')
poly_coeffs = pickle.load(g)

# For the online phase of the server, we need to use the columns of the preprocessed database
transposed_poly_coeffs = np.transpose(poly_coeffs).tolist()

for i in range(1):
    conn, addr = serv.accept()
    L = conn.recv(10).decode().strip()
    L = int(L, 10)
    # OPRF layer: the server receives the encoded set elements as curve points
    encoded_client_set_serialized = b""
    while len(encoded_client_set_serialized) < L:
        data = conn.recv(4096)
        if not data: break
        encoded_client_set_serialized += data   
    encoded_client_set = pickle.loads(encoded_client_set_serialized)
    t0 = time()
    # The server computes (parallel computation) the online part of the OPRF protocol, using its own secret key
    PRFed_encoded_client_set = server_prf_online_parallel(oprf_server_key, encoded_client_set)
    PRFed_encoded_client_set_serialized = pickle.dumps(PRFed_encoded_client_set, protocol=None)
    L = len(PRFed_encoded_client_set_serialized)
    sL = str(L) + ' ' * (10 - len(str(L))) #pad len to 10 bytes

    conn.sendall(sL.encode())
    conn.sendall(PRFed_encoded_client_set_serialized)    
    print(' * OPRF layer done!')
    t1 = time()
    L = conn.recv(10).decode().strip()
    L = int(L, 10)

    # The server receives bytes that represent the public HE context and the query ciphertext
    final_data = b""
    while len(final_data) < L:
        data = conn.recv(4096)
        if not data: break
        final_data += data

    t2 = time()    
    # Here we recover the context and ciphertext received from the received bytes
    received_data = pickle.loads(final_data)
    srv_context = ts.context_from(received_data[0])
    received_enc_query_serialized = received_data[1]

    # Server prepares the answer for each of the number_of_batches = number_of_bins/poly_modulus_degree encrypted batches
    from server_offline import number_of_bins
    number_of_batches = int(number_of_bins / poly_modulus_degree)
    server_answers = []
    for s in range(number_of_batches):
        received_enc_query = [[None for j in range(logB_ell)] for i in range(base - 1)]
        for i in range(base - 1):
            for j in range(logB_ell):
                if ((i + 1) * base ** j - 1 < minibin_capacity):
                    received_enc_query[i][j] = ts.bfv_vector_from(srv_context, received_enc_query_serialized[s][i][j])

        # Here we recover all the encrypted powers Enc(y), Enc(y^2), Enc(y^3) ..., Enc(y^{minibin_capacity}), from the encrypted windowing of y.
        # These are needed to compute the polynomial of degree minibin_capacity

        all_powers = [None for i in range(minibin_capacity)]
        for i in range(base - 1):
            for j in range(logB_ell):
                if ((i + 1) * base ** j - 1 < minibin_capacity):
                    all_powers[(i + 1) * base ** j - 1] = received_enc_query[i][j]
        for k in range(minibin_capacity):
            if all_powers[k] == None:
                all_powers[k] = power_reconstruct(received_enc_query, k + 1)

        all_powers = all_powers[::-1]

        # For each batch, the server sends alpha ciphertexts, obtained from performing dot_product between the polynomial coefficients from the preprocessed server database and all the powers Enc(y), ..., Enc(y^{minibin_capacity})
        # The server sends a total of number_of_batches * alpha ciphertexts.
        server_answer_per_batch = []
        for i in range(alpha):
            # the rows with index multiple of (B/alpha+1) have only 1's
            dot_product = all_powers[0]
            for j in range(1, minibin_capacity):
                dot_product = dot_product + transposed_poly_coeffs[(minibin_capacity + 1) * i + j][s * poly_modulus_degree: s * poly_modulus_degree + poly_modulus_degree] * all_powers[j]
            dot_product = dot_product + transposed_poly_coeffs[(minibin_capacity + 1) * i + minibin_capacity][s * poly_modulus_degree: s * poly_modulus_degree + poly_modulus_degree]
            server_answer_per_batch.append(dot_product.serialize())
        server_answers.append(server_answer_per_batch)
    # The answer to be sent to the client is prepared
    response_to_be_sent = pickle.dumps(server_answers, protocol=None)
    t3 = time()
    L = len(response_to_be_sent)
    sL = str(L) + ' ' * (10 - len(str(L))) #pad len to 10 bytes

    conn.sendall(sL.encode())
    conn.sendall(response_to_be_sent)

    # Close the connection
    print("Client disconnected \n")
    print('Server ONLINE computation time {:.2f}s'.format(t1 - t0 + t3 - t2))

    conn.close()

    # ------------------------------
    my_file = open('our_results', 'a')
    my_file.write("S_online " + str(t1 - t0 + t3 - t2) + '\n')
    my_file.close()