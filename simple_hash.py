from random import randint
import math
import mmh3

#parameters
from parameters import output_bits, number_of_hashes, bin_capacity
log_no_hashes = int(math.log(number_of_hashes) / math.log(2)) + 1
mask_of_power_of_2 = 2 ** output_bits - 1


def left_and_index(item, index):
    '''
    :param item: an integer
    :param index: a log_no_hashes bits integer
    :return: an integer represented as item_left || index
    '''

    return ((item >> (output_bits)) << (log_no_hashes)) + index

#The hash family used for simple hashing relies on the Murmur hash family (mmh3)

def location(seed, item):
    '''
    :param seed: a seed of a Murmur hash function
    :param item: an integer
    :return: Murmur_hash(item_left) xor item_right, where item = item_left || item_right
    '''

    item_left = item >> output_bits
    item_right = item & mask_of_power_of_2
    hash_item_left = mmh3.hash(str(item_left), seed, signed=False) >> (32 - output_bits)
    return hash_item_left ^ item_right

class Simple_hash():

    def __init__(self, hash_seed):
        self.no_bins = 2 ** output_bits
        self.simple_hashed_data = [[None for j in range(bin_capacity)] for i in range(self.no_bins)]
        self.occurences = [0 for i in range(self.no_bins)]
        self.FAIL = 0
        self.hash_seed = hash_seed
        self.bin_capacity = bin_capacity

    #  insert item using hash i on position given by location
    def insert(self, item, i):
        loc = location(self.hash_seed[i], item)
        if (self.occurences[loc] < self.bin_capacity):
            self.simple_hashed_data[loc][self.occurences[loc]] = left_and_index(item, i)
            self.occurences[loc] += 1
        else:
            self.FAIL = 1
            print('Simple hashing aborted')
