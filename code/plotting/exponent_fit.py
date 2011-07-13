import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import leastsq
import os
import sys


#file = sys.argv[1]
file = '20110630/20110630-6638.01.npz'

filename = '/Users/kellyz/Documents/Code/python/Fiberkontrol/code/' + file

print filename

a = np.load(filename)['x']

dataA = a.tolist()[0][2]
if dataA.count([]) > 0:
    dataA.remove([])

length = int(len(dataA))

x = np.linspace(0, length-1000, length-1000)
y = dataA[1000:length]
plt.plot(x, y)

fp = lambda a, x: a[0]*np.exp(a[1]*np.exp(a[2]*x))

error = lambda a, x, y: (fp(a,x)-y)

a0 = [850.0, -1.0, -1.0]
a, success = leastsq(error, a0, args=(x,y), maxfev=2000)

def plot_fit():
    print 'Estimator parameters: ', a

    X = x
    plt.plot(x, y, 'ro', X, fp(a, X))
    
plot_fit()

plt.figure(2)

dIntensity = fp(a, x[0])-fp(a,x)
yFlat = y + dIntensity

plt.plot(x, yFlat)

plt.show()
