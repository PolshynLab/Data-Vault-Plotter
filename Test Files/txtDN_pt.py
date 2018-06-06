'''
[info]
version = -3.0
Stupid version. Simulated data. For testing grapher. 
'''


import time
import math
import numpy as np
import labrad
import labrad.units as U

cxn = labrad.connect()
dv = cxn.data_vault()

#Create new data set
dv.new('Test Point-like Data', ['n0', 'p0'], ['C_v', 'T', 'V'])

#For each independent variable, add a parameter variable_rng with the range of value the variable will take and variable_pnts for the number of values the variable will take
dv.add_parameter('n0_rng', (1,-2))
dv.add_parameter('p0_pnts', 100)
dv.add_parameter('n0_pnts', 150)
dv.add_parameter('p0_rng', (5,0))
dv.add_parameter('live_plots', (('n0', 'p0', 'C_v'), ('p0', 'T'), ('p0', 'n0', 'V')))

print 'setup file...'
time.sleep(5)

n_space = np.linspace(1, -2, 150)
p_space = np.linspace(5, 0, 100)

for i in range(0, 150):
	for j in range(0, 100):
		Cv = 10 * i + np.random.random() * j
		T = np.random.random() + 5*np.sin(j)
		V = np.cos(i+j)
		dv.add(n_space[i], p_space[j], Cv, T, V)
		time.sleep(0.1)
	if i%10 == 0:
		print i
		
		


