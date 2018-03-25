'''
[info]
version = -3.0
Stupid version. Simulated data. For testing grapher. 
'''
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import time
import math
import numpy as np
import labrad
import labrad.units as U

X_MAX = 10.0
X_MIN = -10.0
Y_MAX = 10.0
Y_MIN = -10.0

def dac_adc_measure(dacadc, scale, chx, chy):
    return np.array([dacadc.read_voltage(chx), dacadc.read_voltage(chy)]) / 2.5 * scale
    
def vb_fixed(p0, n0, delta, vb):
    """
    :param p0: polarizing field
    :param n0: charge carrier density
    :param delta: capacitor asymmetry
    :param vb: fixed voltage set on the bottom gate
    :return: (v_top, v_sample)
    """
    return vb - (n0 * delta - p0) / (1.0 - delta ** 2), vb - 0.5 * (n0 - p0) / (1.0 - delta)


def vt_fixed(p0, n0, delta, vt):
    """
    :param p0: polarizing field
    :param n0: charge carrier density
    :param delta: capacitor asymmetry
    :param vt: fixed voltage set on the top gate
    :return: (v_bot, v_sample)
    """
    return (n0 * delta - p0) / (1.0 - delta ** 2) + vt, vt - 0.5 * (n0 + p0) / (1.0 + delta)


def vs_fixed(p0, n0, delta, vs):
    """
    :param p0: polarizing field
    :param n0: charge carrier density
    :param delta: capacitor asymmetry
    :param vs: fixed voltage set on graphene sample
    :return: (v_top, v_bottom)
    """
    return vs + 0.5 * (n0 + p0) / (1.0 + delta), vs + 0.5 * (n0 - p0) / (1.0 - delta)


def function_select(s):
    """
    :param s: ('vb', 'vt', 'vs') selection based on which parameter is fixed
    :return: function f
    """
    if s == 'vb':
        f = vb_fixed

    elif s == 'vt':
        f = vt_fixed
    elif s == 'vs':
        f = vs_fixed
    return f

def mesh(vfixed, offset, drange, nrange, fixed="vb", pxsize=(100, 100), delta=0.0):
    """
    drange and nrange are tuples (dmin, dmax) and (nmin, nmax)
    offset  is a tuple of offsets:  (N0, D0)
    pxsize  is a tuple of # of steps:  (N steps, D steps)
    fixed sets the fixed channel: "vb", "vt", "vs"
    fast  - fast axis "D" or "N"
    """
    f = function_select(fixed)
    p0 = np.linspace(drange[0], drange[1], pxsize[1]) - offset[1]
    n0 = np.linspace(nrange[0], nrange[1], pxsize[0]) - offset[0]
    n0, p0 = np.meshgrid(n0, p0)  # p0 - slow n0 - fast
    # p0, n0 = np.meshgrid(p0, n0)  # p0 - slow n0 - fast
    v_fast, v_slow = f(p0, n0, delta, vfixed)
    return np.dstack((v_fast, v_slow)), np.dstack((p0, n0))

def create_file(dv): # try kwarging the vfixed

    dv.new("Test plot", ("i", "j", 'V1', 'V2'),
           ('Cs', 'Ds', 'p0', 'n0', 'X', 'Y', 't'))
           
    print("Created {}".format(dv.get_name()))

    dv.add_parameter('n0_rng', (-1.0,1.0))
    dv.add_parameter('p0_pnts', 500)
    dv.add_parameter('n0_pnts', 150)
    dv.add_parameter('p0_rng', (10.0,-8.0))

def main():

    # Connections and Instrument Configurations
    cxn = labrad.connect()
    reg = cxn.registry
    dv = cxn.data_vault
   
    create_file(dv)

    t0 = time.time()
    
    pxsize = (150, 500)
    extent = (-1, 1, 10, -8)
    num_x = pxsize[0]
    num_y = pxsize[1]
    
    print extent, pxsize

    m, mdn = mesh(vfixed=0, offset=(0, -0.0), drange=(extent[2], extent[3]),
                  nrange=(extent[0], extent[1]), fixed='vs',
                  pxsize=pxsize, delta=0.035)
    
    for i in range(num_y):
        
        data_x = np.zeros(num_x)
        data_y = np.zeros(num_x)
        
        vec_x = m[i, :][:, 0]
        vec_y = m[i, :][:, 1]

        md = mdn[i, :][:, 0]
        mn = mdn[i, :][:, 1]

        mask = np.logical_and(np.logical_and(vec_x <= X_MAX, vec_x >= X_MIN),
                              np.logical_and(vec_y <= Y_MAX, vec_y >= Y_MIN))
        if np.any(mask == True):
            start, stop = np.where(mask == True)[0][0], np.where(mask == True)[0][-1]

            num_points = stop - start + 1

            print("Simulating {} of {}  --> Ramping. Points: {}".format(i + 1, num_y, num_points))
            
            d_tmp = [np.random.rand(num_points),np.random.rand(num_points)]

            data_x[start:stop + 1], data_y[start:stop + 1] = d_tmp

        d_cap = data_x + data_y
        d_dis = data_x - data_y

        j = np.linspace(0, num_x - 1, num_x)
        ii = np.ones(num_x) * i
        t1 = np.ones(num_x) * time.time() - t0
        totdata = np.array([j, ii, vec_x, vec_y, d_cap, d_dis, md, mn, data_x, data_y, t1])
        dv.add(totdata.T)
        
        time.sleep(0.5)
    print("it took {} s. to write data".format(time.time() - t0))


if __name__ == '__main__':
    main()
