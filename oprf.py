from fastecdsa.curve import P192
from fastecdsa.point import Point
from math import log2
from multiprocessing import Pool
from parameters import sigma_max

mask = 2 ** sigma_max - 1

number_of_processes = 4

# Curve parameters
curve_used = P192
prime_of_curve_equation = curve_used.p
order_of_generator = curve_used.q
log_p = int(log2(prime_of_curve_equation)) + 1
G = Point(curve_used.gx, curve_used.gy, curve=curve_used) #generator of the curve_used

def server_prf_offline(vector_of_items_and_point): #used as a subroutine for server_prf_offline_paralel
	vector_of_items = vector_of_items_and_point[0]
	point = vector_of_items_and_point[1]
	vector_of_multiples = [item * point for item in vector_of_items]
	return [(Q.x >> log_p - sigma_max - 10) & mask for Q in vector_of_multiples]

def server_prf_offline_parallel(vector_of_items, point):
	'''
	:param vector_of_items: a vector of integers
	:param point: a point on elliptic curve (it will be key * G)
	:return: a sigma_max bits integer from the first coordinate of item * point (this will be the same as item * key * G)
	'''
	division = int(len(vector_of_items) / number_of_processes)
	inputs = [vector_of_items[i * division: (i+1) * division] for i in range(number_of_processes)]
	if len(vector_of_items) % number_of_processes != 0:
		inputs.append(vector_of_items[number_of_processes * division: number_of_processes * division + (len(vector_of_items) % number_of_processes)])
	inputs_and_point = [(input_vec, point) for input_vec in inputs]
	outputs = []
	with Pool(number_of_processes) as p:
		outputs = p.map(server_prf_offline, inputs_and_point)	
	final_output = []
	for output_vector in outputs:
		final_output = final_output + output_vector
	return final_output		

def server_prf_online(keyed_vector_of_points): #used as a subroutine in server_prf_online_paralel
	key = keyed_vector_of_points[0]
	vector_of_points = keyed_vector_of_points[1]
	vector_of_multiples = [key * PP for PP in vector_of_points]
	return [[Q.x, Q.y] for Q in vector_of_multiples]


def server_prf_online_parallel(key, vector_of_pairs):
	'''
	:param key: an integer
	:param vector_of_pairs: vector of coordinates of some points P on the elliptic curve
	:return: vector of coordinates of points key * P on the elliptic curve
	'''
	vector_of_points = [Point(P[0], P[1], curve=curve_used) for P in vector_of_pairs]
	division = int(len(vector_of_points) / number_of_processes)
	inputs = [vector_of_points[i * division: (i+1) * division] for i in range(number_of_processes)]
	if len(vector_of_points) % number_of_processes != 0:
		inputs.append(vector_of_points[number_of_processes * division: number_of_processes * division + (len(vector_of_points) % number_of_processes)])
	keyed_inputs = [(key, _) for _ in inputs]
	outputs = []
	with Pool(number_of_processes) as p:
		outputs = p.map(server_prf_online, keyed_inputs)
	final_output = []
	for output_vector in outputs:
		final_output = final_output + output_vector
	return final_output

def client_prf_offline(item, point):
	'''
	:param item: an integer
	:param point: a point on elliptic curve  (ex. in the protocol point = key * G)
	:return: coordinates of item * point (ex. in the protocol it computes key * item * G)
	'''
	P = item * point
	x_item = P.x
	y_item = P.y
	return [x_item, y_item]

def client_prf_online(keyed_vector_of_pairs):
	key_inverse = keyed_vector_of_pairs[0]
	vector_of_pairs = keyed_vector_of_pairs[1]
	vector_of_points = [Point(pair[0],pair[1], curve=curve_used) for pair in vector_of_pairs]
	vector_key_inverse_points = [key_inverse * PP for PP in vector_of_points]
	return [(Q.x >> log_p - sigma_max - 10) & mask for Q in vector_key_inverse_points]

def client_prf_online_parallel(key_inverse, vector_of_pairs):
	vector_of_pairs = vector_of_pairs
	division = int(len(vector_of_pairs) / number_of_processes)
	inputs = [vector_of_pairs[i * division: (i+1) * division] for i in range(number_of_processes)]
	if len(vector_of_pairs) % number_of_processes != 0:
		inputs.append(vector_of_pairs[number_of_processes * division: number_of_processes * division + (len(vector_of_pairs) % number_of_processes)])
	keyed_inputs = [(key_inverse, _) for _ in inputs]		
	outputs = []
	with Pool(number_of_processes) as p:
		outputs = p.map(client_prf_online, keyed_inputs)
	final_output = []
	for output_vector in outputs:
		final_output = final_output + output_vector
	return final_output

