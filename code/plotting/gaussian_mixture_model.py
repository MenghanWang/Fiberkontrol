import numpy as np
import pylab as p
import copy

mu1, sigma1 = 2, 1
mu2, sigma2 = 7, 4

print "mus", mu1, mu2
print "sigs", sigma1, sigma2

x1 = mu1 + sigma1*p.randn(7000)
x2 = mu2 + sigma2*p.randn(1000)
xTotal = np.hstack((x1, x2))

def norm_density(values, mu_est, sigma_est):
    diffFromMean = values - mu_est
    print "diffrommean", diffFromMean
    exponent =(np.multiply(diffFromMean, diffFromMean))/sigma_est**2
    print "exponenet", exponent
    print "e^exponent", np.exp(-(.5)*exponent)
    value = (1/(np.sqrt(2*np.pi)*sigma_est))*np.exp(-(.5)*(exponent))
    print "norm_density", value
    return value

##---Initialize---##
values = xTotal
num_mixtures = 2
num_iter = 25000

N = len(values)
epsilon = 1e-4;

counter = 0
mu_est = 2*np.mean(values)*np.sort(np.random.rand(num_mixtures, 1)) ##vectors of means of each curve
sigma_est = np.ones((num_mixtures, 1))*np.std(values); ##vector of standard deviations of each curve
p_est = np.ones((num_mixtures, 1))/num_mixtures ##curve membership probability estimates
difference = epsilon


##----Now iterate ----##
while (difference >= epsilon and counter < num_iter):
    print "counter", counter
  #[mu_est, sigma_est, p_est]

    ## E step: classify values into one of the mixtures
    curve = np.ones((num_mixtures, len(values)))
    for j in range(num_mixtures):
        print "values", values
        curve[j,:] = p_est[j]*norm_density(values, mu_est[j], sigma_est[j])
    #normalize
    #divide each member of a column by the sum of its column
    sumsOfColumns = np.sum(curve, axis=0)
    for j in range(num_mixtures):
        curve[j,:] = np.divide(curve[j,:], sumsOfColumns)

    print "curves", curve

    # M setp: maximize the parameters of each curve (i.e. p, mu, sigma)
    mu_est_old = copy.deepcopy(mu_est)
    sigma_est_old = copy.deepcopy(sigma_est)
    p_est_old = copy.deepcopy(p_est)

    print "mu_est_old", mu_est_old
    print "sigma_est_old", sigma_est_old
    print "p_est_old", p_est_old
    print "epsilon", epsilon

    for j in range(num_mixtures):
        mu_est[j] = np.divide(np.sum( np.multiply(curve[j,:], values)), np.sum(curve[j,:]))

        diffFromMean = values - mu_est[j]
        diffFromMeanSumSquared = np.sum(np.multiply(diffFromMean, diffFromMean))
        sigma_est[j] = np.sqrt( np.divide(np.sum(np.multiply(curve[j,:], diffFromMeanSumSquared)), np.sum(curve[j,:])))

        p_est[j] = np.mean(curve[j, :])
        
    print "sigma_est", sigma_est
    print "p_est", p_est

    print "sum mu", np.sum(np.abs(mu_est_old - mu_est))

    calculatedDifference = np.sum(np.abs(mu_est_old - mu_est)) + np.sum(np.abs(sigma_est_old - sigma_est)) + np.sum(np.abs(p_est_old - p_est))
    difference = calculatedDifference
    print "difference", difference

    counter = counter + 1

print "\n\nfinal mu", mu_est
print "final sig", sigma_est
print "final p", p_est