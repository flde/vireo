import numpy as np
from scipy.stats import entropy
from scipy.special import logsumexp, digamma

def barcode_entropy(X, y=None):
    """
    entropy for categorical barcodes
    """
    if y is None:
        Z_str = [str(x) for x in X]
    elif len(X) == len(y):
        Z_str = [str(X[i]) + str(y[i]) for i in range(len(X))]
    else:
        #  print("Error: X and y have different length in barcode_entropy.")
        return None, None
    
    Z_val, Z_cnt = np.unique(Z_str, return_counts=True)
    
    return entropy(Z_cnt / np.sum(Z_cnt), base=2), Z_str


def variant_select(GT, var_count=None, rand_seed=0):
    """
    Selection of a set of discriminatory variants by prioritise variants on 
    information gain.

    GT: (n_var * n_donor)
        a matrix with categorical values
    var_count: (n_var, )
        the counts for each variant
    """
    np.random.seed(rand_seed)
    
    K = GT.shape[1]
    entropy_now = 0
    variant_set = []
    barcode_set = ["#"] * K

    entropy_all = np.zeros(GT.shape[0])
    barcode_all = [barcode_set] * GT.shape[0]
    barcode_set = barcode_all

    while True:
        
        for i in range(GT.shape[0]):
            _entropy, _barcode = barcode_entropy(barcode_set[i], GT[i, :])
            entropy_all[i], barcode_all[i] = _entropy, _barcode

        if np.max(entropy_all) == entropy_now:
            break
        
        idx = np.where(np.max(entropy_all) == entropy_all)[0]
        if var_count is not None:
            # idx = idx[np.argsort(var_count[idx])[::-1]]
            idx = idx[var_count[idx] >= np.median(var_count[idx])]
        
        # print("Randomly select 1 more variants out %d" %len(idx))
        # idx_use = idx[np.random.randint(len(idx))]
        
        print("Select all variants with min entropy of %d" %np.max(entropy_all)) 
        idx_use = idx

        variant_set.append(idx_use)
        barcode_set = [barcode_all[i] for i in idx_use]
        entropy_now = np.max(entropy_all[idx_use])
        GT = GT[idx_use, :]

    if entropy_now < np.log2(K):
        print("Warning: variant_select can't distinguish all samples.")

    return entropy_now, barcode_set, variant_set

def variant_ELBO_gain(ID_prob, AD, DP, pseudocount=0.5):
    """variats selection by comparing evidence lower bounds between 
    M1: assigned to multiple donors and M0: with only a single donor

    Parameters
    ----------
    ID_prob: (n_cell * n_donor)
        a matrix for cell assignment probability
    AD, DP: (n_var, n_cell)
        sparse matrices for counts on alternative allele or total depth
    pseudocount: float
        pseudo count as binomial prior

    Return
    ------
    Evidence lower bound gain between M1 with multiple donors denoted in ID_prob
    or M0 wiht single donor.
    """
    BD = DP - AD
    _s1_M2 = AD @ ID_prob + pseudocount      #(n_var, n_donor)
    _s2_M2 = BD @ ID_prob + pseudocount      #(n_var, n_donor)
    _ss_M2 = DP @ ID_prob + pseudocount * 2  #(n_var, n_donor)

    _ELBO2 = logsumexp(
        _s1_M2 * digamma(_s1_M2) +
        _s2_M2 * digamma(_s2_M2) -
        _ss_M2 * digamma(_ss_M2), axis=1
    )

    _s1_M1 = AD.sum(1).A + pseudocount
    _s2_M1 = BD.sum(1).A + pseudocount
    _ss_M1 = DP.sum(1).A + pseudocount * 2

    _ELBO1 = logsumexp(
        _s1_M1 * digamma(_s1_M1) +
        _s2_M1 * digamma(_s2_M1) -
        _ss_M1 * digamma(_ss_M1), axis=1
    )

    ELBO_gain = _ELBO2 - _ELBO1
    return ELBO_gain
