import numpy as np
import matplotlib.pyplot as plt
from scikits.learn import mixture
from pylab import *

mu, sigma = -5, 0.2
mu2, sigma2 = 10, 0.3

s = np.random.normal(mu, sigma, (500,1))
s2 = .5*np.random.normal(mu2, sigma2, (100,1))

dist1 = np.random.randn(100)*2 + 3
dist2 = np.random.randn(500)*5 + 10

#s = []
#s2 = []
#for i in dist1:
#    s.append([i])
#for i in dist2:
#    s2.append([i])

total = np.concatenate((s,s2))


count, bins, ignored = plt.hist(s, 30, normed=True)
count2, bins2, ignored2 = plt.hist(s2, 30, normed=True)

total = []
for c in count:
    total.append([c])

x = bins[:-1]
print "x", x

plt.plot(x, total, 'g')
print len(count)
print len(bins)

g = mixture.GMM(n_states=1)
g.fit(total, n_iter=100)

print "weights", g.weights
print "means", g.means
print "covars", g.covars

w=g.weights[0]
m=g.means[0][0]
sig=g.covars[0][0][0]

#w2=g.weights[1]
#m2=g.means[1][0]
#sig2=g.covars[1][0][0]


def gaussian(x, a, b, c):
    val = a * np.exp(-(x - b)**2 / c**2)
    return val

#plt.plot(bins, (1/sig)*np.exp(-(bins - m)**2/(2*sig**2)),linewidth=2,color='r')


plt.plot(bins,100*normpdf(bins, m, sig))
#plt.plot(bins, gaussian(bins, w2, m2, sig2))
#print "score", g.score(total)
#print "eval", g.eval(total)

plt.show()
