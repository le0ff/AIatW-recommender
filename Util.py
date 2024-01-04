import numpy as np
from numpy.linalg import norm

def cosineSim(A, B):
    cosine = np.dot(A,B)/(norm(A)*norm(B))
    if np.isnan(cosine):
        cosine = 0.0
    return cosine

def k_highest_argmax(k, array):
    result = []
    for i in range(k):
        current_index = np.argmax(array)
        array[current_index] = (-1)
        result.append(current_index)
    
    return np.array(result)