from random import sample
from parameters import server_size, client_size, intersection_size

#set elements can be integers < order of the generator of the elliptic curve (192 bits integers if P192 is used); 'sample' works only for a maximum of 63 bits integers.
disjoint_union = sample(range(2 ** 63 - 1), server_size + client_size)
intersection = disjoint_union[:intersection_size]
server_set = intersection + disjoint_union[intersection_size: server_size]
client_set = intersection + disjoint_union[server_size: server_size - intersection_size + client_size]

f = open('server_set', 'w')
for item in server_set:
	f.write(str(item) + '\n')
f.close()

g = open('client_set', 'w')
for item in client_set:
	g.write(str(item) + '\n')
g.close()		

h = open('intersection', 'w')
for item in intersection:
	h.write(str(item) + '\n')
h.close()

#------------------------------------------------------------------------
from parameters import alpha, ell
f = open("our_results", 'a')
f.write("|C|="+str(client_size)+'\n')
f.write("|S|="+str(server_size)+'\n')
f.write("alpha="+str(alpha)+'\n')
f.write("ell="+str(ell)+'\n')
f.close()