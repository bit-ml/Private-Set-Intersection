from random import randint 
import math
import mmh3

#parameters
from parameters import output_bits, number_of_hashes
mask_of_power_of_2 = 2 ** output_bits - 1
log_no_hashes = int(math.log(number_of_hashes) / math.log(2)) + 1


#The hash family used for Cuckoo hashing relies on the Murmur hash family (mmh3)

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

def left_and_index(item, index): 
	'''
	:param item: an integer
	:param index: a log_no_hashes bits integer
	:return: an integer represented as item_left || index 
	'''
	return ((item >> (output_bits)) << (log_no_hashes)) + index 	

def extract_index(item_left_and_index): 
	'''
	:param item_left_and_index: an integer represented as item_left || index
	:return: index extracted
	'''
	return item_left_and_index & (2 ** log_no_hashes - 1) 

def reconstruct_item(item_left_and_index, current_location, seed):
	'''
	:param item_left_and_index: an integer represented as item_left || index
	:param current_location: the corresponding location, i.e. Murmur_hash(item_left) xor item_right
	:param seed: the seed of the Murmur hash function
	:return: the integer item
	'''
	item_left = item_left_and_index >> log_no_hashes
	hashed_item_left = mmh3.hash(str(item_left), seed, signed=False) >> (32 - output_bits)
	item_right = hashed_item_left ^ current_location
	return (item_left << output_bits) + item_right

def rand_point(bound, i): 
	'''
	:param bound: an integer
	:param i: an integer less than bound
	:return: a uniform integer from [0, bound - 1], distinct from i
	'''
	value = randint(0, bound - 1)
	while (value == i):
		value = randint(0, bound - 1)
	return value	

class Cuckoo():

	def __init__(self, hash_seed):
		self.number_of_bins = 2 ** output_bits
		self.recursion_depth = int(8 * math.log(self.number_of_bins) / math.log(2))
		self.data_structure = [None for j in range(self.number_of_bins)]
		self.insert_index = randint(0, number_of_hashes - 1)
		self.depth = 0
		self.FAIL = 0

		self.hash_seed = hash_seed	

	def insert(self, item): #item is an integer
		current_location = location( self.hash_seed[self.insert_index], item)
		current_item = self.data_structure[ current_location]
		self.data_structure[ current_location ] = left_and_index(item, self.insert_index)

		if (current_item == None):
			self.insert_index = randint(0, number_of_hashes - 1)	
			self.depth = 0	
		else:
			unwanted_index = extract_index(current_item)
			self.insert_index = rand_point(number_of_hashes, unwanted_index)	
			if (self.depth < self.recursion_depth):
				self.depth +=1
				jumping_item = reconstruct_item(current_item, current_location, self.hash_seed[unwanted_index])
				self.insert(jumping_item)		
			else:
				self.FAIL = 1	
