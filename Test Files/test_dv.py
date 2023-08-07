import labrad
import numpy as np
import time

cxn = labrad.connect()
dv = cxn.data_vault
number_of_field_points = 100
number_of_voltage_points = 100

dv.new('Test Plot', ['index1', 'index2', 'field', 'voltage'], ['n0', 'p0', 'v2'])
dv.add_parameter('field_pnts', number_of_field_points) 
dv.add_parameter('field_rng', (0, number_of_field_points))
dv.add_parameter('voltage_pnts', number_of_voltage_points) 
dv.add_parameter('voltage_rng', (0, number_of_voltage_points))
print(dv.get_name())

# raw_input("...")

for j in range(0, number_of_voltage_points):
	print(j)
	line = []
	for i in range(0, number_of_field_points):
		line.append([i, j, i, j, np.sin(i) + 0.1*np.random.random(), np.cos(i)+ 0.1*np.random.random(), np.random.random()])
	dv.add(line)
	time.sleep(2)
	