We implemented in Python a **Private Set Intersection (PSI)** protocol, a functionality that allows two parties to *privately join their sets* in order to compute their *common elements*. In our setup, these parties are:
​
* a *server* having a large database
* a *client* who would like to *privately* query the database.
​
## How it works
The starting point of our implementation consisted of this [paper](https://eprint.iacr.org/2017/299.pdf) and its [follow-up](https://eprint.iacr.org/2018/787.pdf). This protocol uses **homomorphic encryption**, a cryptographic primitive that allows performing computations on encrypted data and only the secret key holder (in our case, the client) has access to the result of these computations. For implementing PSI, we used the [FV] homomorphic encryption scheme from the [TenSEAL](https://github.com/OpenMined/TenSEAL) library. You can also check out a concurrent [SEAL](https://github.com/microsoft/SEAL)-based [C++ implementation](https://github.com/microsoft/APSI) of the protocol that has been recently published by Microsoft.

**Disclaimer:** Our implementation is not meant for production use. Use it at your own risk.
​
### Main idea of the protocol
​
Suppose the client wants to check if his query *x* belongs to the database of the server. Consider this database having as entries the integers *y_1,...,y_n*. Then the server can associate to its database the following polynomial *P(X) = (X-y_1) * ... * (X-y_n).* If  *x* belongs to the database, then *P* vanishes at *x*. This is the **main idea of the protocol**: the server should compute this evaluation of *P* at *x* in a secure way and send it to the client. 
​

More precisely, the client sends his query encrypted with a homomorphic encryption scheme, *Enc(x)*. Then the server evaluates *P* at the given encryption: due to homomorphic properties, the result will turn out to be *Enc(P(x)).* Then the client decrypts this result and checks if it is equal to 0; in case of equality, the query belongs to the database. 
​

The protocol is split in two parts: offline phase and online phase. The online phase starts when the client performs the OPRF protocol with the server, for encoding its items with the server's secret key.
​
### The preprocessing phase
In this phase, both the server and the client preprocess their datasets, until performing the PSI protocol.
​
* **Oblivious PRF**: Both the server and the client engage in a Diffie-Hellman-like protocol in order to apply Oblivious PRF to their datasets. 
  * The server embeds his database entries in points on an elliptic curve, multiplies them by a secret key, ```oprf_server_key``` and considers ```sigma_max``` bits out of the first coordinate of these points.
  * The client also embeds his entries in points on an elliptic curve, multiplies them by a secret key, ```oprf_client_key``` and sends them to server.
  * The server multiplies the client's points by ```oprf_server_key``` and sends them back to client. Now the client's points are ```oprf_server_key``` * ```oprf_client_key``` * item.
  * The client multiplies the received points by the inverse of ```oprf_client_key``` and takes ```sigma_max``` bits out of the first coordinate of these points.
  * After this step, both the server and the client have new datasets, each of ```sigma_max```-bit integers.
​
* **Hashing**: We used three Murmur hash functions for mapping items of the client and of the server into ```number_of_bins``` bins:
    * The client performs *Cuckoo hashing*; each of his bins has 1 element. 
    * The server performs *simple hashing*, each of his bins has ```bin_capacity``` elements.
Hence, the PSI protocol can be therefore performed per each bin. (a padding step might be required to get the bins full.)
​
* **Partitioning**: This helps the server evaluate polynomials of lower degree on encrypted data.
    * The server partitions each bin into ```alpha``` minibins, having ```bin_capacity```/```alpha``` elements. 
Hence, performing the PSI protocol on each bin is split as performing ```alpha``` PSI protocols for each minibin. 
​
* **Computing coefficients of the polynomials**: this is applied for each minibin
    * The server computes the coefficients of the polynomials that vanish at all the elements of the minibin. 
Hence each minibin is represented by ```bin_capacity```/```alpha``` + 1 coefficients.

### The actual **PSI** protocol
​
In this phase, both the server and the client perform the actual PSI protocol. The encryption scheme used, [FV], allows encrypting messages as polynomials of degree less than ```poly_modulus_degree```, which is a power of 2, with integer coefficients modulo ```plain_modulus```. This modulus is chosen so that it is a prime congruent with 1 modulo 2 * ```poly_modulus_degree```, which helps identifying each such polynomial with a vector of ```poly_modulus_degree``` integer entries modulo ```plain_modulus```. [TenSEAL](https://github.com/OpenMined/TenSEAL/blob/master/tutorials%2FTutorial%200%20-%20Getting%20Started.ipynb) allows encryption of **vectors of integers**, by first performing the above correspondence and then performing the actual encryption. Also, in a similar way, decrypting in TenSEAL works for **vectors of integers**. The encryption scheme implemented in TenSEAL benefits from allowing to encrypt *vectors of integers*, by performing both encoding and encryption. Also, decrypting in TenSEAL leads to *vectors of integers*, the encodings of the corresponding decryptions.
​
* **Batching**:
     * The client batches his bins (having each 1 integer entry)  into ```number_of_bins```/```poly_modulus_degree``` vectors.
     * The client encodes each such batch as a plaintext.
     * The client encrypts these plaintexts and sends them to the server.
     * The server batches his minibins in minibatches.
 Due to our choice of parameters, only 1 plaintext is obtained and therefore, only 1 ciphertext is sent: *Enc(x)*.
 Hence, performing the PSI protocol can be performed simultaneously per each batch of bins.
 
Since each minibin is represented by a polynomial of degree *D* =```bin_capacity```/```alpha```, evaluating such a polynomial can be performed by doing the scalar product between the vector of its coefficients and all the (encrypted) powers of the *x*, with exponent at most *D*. The next step, *windowing*, helps the client send *sufficiently many powers* so that the server can recover all the powers with small computational effort.
​
* **Windowing**: 
    * The client sends besides *Enc(x)*, *Enc(x ** 2), Enc(x ** 4),...,Enc(x ** {2 ** {log D}})*.     
This scenario corresponds to the windowing parameter ```ell = 1```.
​
* **Recover all powers**:
    * The server recovers any *Enc(x ** i)*, for every *i* less or equal than *D*, from the given powers, by writing *i* in binary decomposition.
​
* **Doing the scalar products**: The server evaluates the polynomials for each minibin by computing the scalar product between the vector of their coefficients and the previous powers. Thanks to TenSEAL, this is done as follows:
    * For each minibatch, the server makes the sum of each encrypted power *Enc(x** i)* multiplied by the *D+1-i*-th column of coefficients from the minibatch.
    * The server gets ```alpha``` * ```number_of_bins```/ ```poly_modulus_degree``` encrypted results and sends them to the client.
​
* **Getting the verdict**:
    * The client decrypts the results he gets from server. Thanks to TenSEAL, he recovers a vector of integers (corresponding to the underlying polynomial plaintext, via encoding). 
    * The client checks this vector to see where he obtains 0. If there is an index of this vector where he gets 0, then the (Cuckoo hashing) item corresponding to this index belongs to a minibin of the corresponding server's bin.
    * This index helps him recover the common element.
​
## How to run
You can generate the datasets of the client and the server by running ```set_gen.py```. Then run ```server_offline.py``` and ```client_offline.py``` to preprocess them. Now go the online phase of the protocol by running ```server_online.py``` and ```client_online.py```. Have fun! :smile: 
