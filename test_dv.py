import labrad
import numpy as np
import time

cxn = labrad.connect()
dv = cxn.data_vault


dv.new('Test Plot', ['index1', 'index2', 'field', 'voltage'], ['n0', 'p0', 'v2'])
print dv.get_name()

raw_input("...")

for j in range(0, 50):
	print j
	line = []
	for i in range(0, 50):
		line.append([i, j, i, j, np.sin(i) + 0.1*np.random.random(), np.cos(i)+ 0.1*np.random.random(), np.random.random()])
	dv.add(line)
	time.sleep(2)
	