We implemented in Python a **Private Set Intersection (PSI)** protocol, a functionality that allows two parties to compute their common elements, without revealing their datasets or learning anything but their intersection. These parties are:
​
* a *server* having a large database
* a *client* who would like to query the database. (in an encrypted way)
​
## How it works
The starting point of our implementation consisted of this [paper](https://eprint.iacr.org/2017/299.pdf) and its [follow-up](https://eprint.iacr.org/2018/787.pdf). This protocol uses **homomorphic encryption**, a cryptographic primitive that allows performing computations on encrypted data and only the secret key holder (in our case, the client) has access to the result of these computations. For implementing PSI, we used the [FV] homomorphic encryption scheme from the [TenSEAL](https://github.com/OpenMined/TenSEAL) library.
​
### Main idea of the protocol
​
Suppose the client wants to check if his query *x* belongs to the database of the server. Consider this database having as entries the integers *y_1,...,y_n*. Then the server can associate to its database the following polynomial *P(X) = (X-y_1) * ... * (X-y_n).* If  *x* belongs to the database, then *P* vanishes at *x*. This is the **main idea of the protocol**: the server should compute this evaluation of *P* at *x* in a secure way and send to the client. 
​
More precisely, the client sends his query encrypted with a homomorphic encryption scheme, *Enc(x)*. Then the server evaluates *P* at the given encryption: due to homomorphic properties, the result will turn out to be *Enc(P(x)).* Then the client decrypts this result and checks if it is equal to 0; in case of equality, the query belongs to the database. 
​
The protocol is split in two parts: offline phase and online phase.
​
### The offline phase
In this phase, both server and client preprocess their datasets, until performing the PSI protocol.
​
* **Oblivious PRF**: Both server and client engage in a Diffie-Hellman-like protocol in order to apply Oblivious PRF to their datasets. 
  * Server embeds his database entries in points on an elliptic curve, multiplies them by a secret key, ```oprf_server_key``` and considers 32 bits out of the first coordinate of these points.
  * Client also embeds his entries in points on an elliptic curve, multiplies them by a secret key, ```oprf_client_key``` and sends them to server.
  * Server multiplies the client's points by ```oprf_server_key``` and sends them back to client. Now the client's points are ```oprf_server_key``` * ```oprf_client_key``` * item.
  * Client multiplies the received points by the inverse of ```oprf_client_key``` and takes 32 bits out of the first coordinate of these points.
  * After this step, both server and client have new datasets, each of 32-bit integers.
​
* **Hashing**: We used three Murmur hash functions for mapping elements into ```number_of_bins``` bins:
    * Client performs Cuckoo hashing; each of his bins has 1 element. 
    * Server performs simple hashing, each of his bins has ```bin_capacity``` elements.
Hence, the PSI protocol can be therefore performed per each bin. (a padding step might be required to get the bins full.)
​
* **Partitioning**: This helps evaluate polynomials of lower degree on encrypted data.
    * Server partitions each bin into ```alpha``` minibins, having ```bin_capacity```/```alpha``` elements. 
Hence, performing PSI on each bin is split as performing ```alpha``` PSI protocols for each minibin. 
​
* **Computing coefficients of polynomials**: this is applied for each minibin
    * Server computes the coefficients of the polynomials that vanish at all the elements of the minibin. 
Hence each minibin is represented by ```bin_capacity```/```alpha``` + 1 coefficients.
### The online phase
​
In this phase, both server and client perform the PSI protocol. The encryption scheme used, [FV], allows encrypting messages as polynomials of degree less than ```poly_modulus_degree```, a power of 2, whose coefficients are integers modulo ```plain_modulus```. This modulus is chosen so that it is a prime congruent with 1 modulo 2 * ```poly_modulus_degree```, which helps *encode* each such polynomial as a vector of ```poly_modulus_degree``` integer entries less than ```plain_modulus```. The encryption scheme implemented in TenSEAL benefits of allowing to encrypt *vectors of integers*, by performing both encoding and encryption. Also, decrypting in TenSEAL leads to *vectors of integers*, the encodings of the corresponding decryptions.
​
* **Batching**
    * Client batches his (integer) entries  into ```number_of_bins```/```poly_modulus_degree``` plaintexts.
    * Client encrypts these plaintexts and sends to the server. 
 Due to our choice of parameters, only 1 plaintext is obtained, namely *Enc(x)*.
 
 Since each minibin is represented by a polynomial of degree *D* =```bin_capacity```/```alpha```, evaluating such a polynomial can be performed by doing the scalar product between the vector of its coefficients and all the (encrypted) powers of the *x*, with exponent at most *D*. This windowing procedure helps the client send *sufficiently many powers* so that the server can recover all the powers with small computation effort.
​
* **Windowing**: 
    * Client sends besides *Enc(x)* also *Enc(x ** 2), Enc(x ** 4),...,Enc(x ** {2 ** {log D}})*.     
This scenario corresponds to the windowing parameter ```ell = 1```.
​
* **Recover all powers**: 
    * Server recovers any *Enc(x ** i)*, for every *i* less or equal than *D*, from the given powers.
​
* **Doing scalar products**:
    * Server evaluates the polynomials for each minibin by computing the scalar product between the vector of their coefficients and the previous powers.
    * Server gets ```alpha``` encrypted results and sends to the client.
​
* **Getting the verdict**:
    * Client decrypts the results. 
    * Client computes the common elements by looking at the index of a 0.
​
## How to run
You can generate the datasets of client and server by running ```set_gen.py```. Then run ```server_offline.py``` and ```client_offline.py``` to preprocess them. Now go the online phase of the protocol by running ```server_online.py``` and ```client_online.py```. Have fun! :smile: 
