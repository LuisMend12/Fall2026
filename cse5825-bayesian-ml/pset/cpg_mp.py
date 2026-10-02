import sys
from math import log

states = ('CPG', 'NCPG')

file_name = sys.argv[1]
ffile = open(file_name)
observations = ""
ffile.readline() # Skip the first header line
for line in ffile:
    observations += line.strip()

start_dist = {'CPG': 0.5, 'NCPG':  0.5}

transition_dist = {
'CPG' : {'CPG': 0.9, 'NCPG': 0.1},
'NCPG' : {'CPG': 0.1, 'NCPG': 0.9}
}

emission_dist = {
'CPG' : {'A': 0.15, 'C': 0.35, 'G': 0.35, 'T': 0.15},
'NCPG' : {'A': 0.25, 'T': 0.25, 'C': 0.25, 'G': 0.25}}


def max_product(observations, states, start, trans, emit):
    DP = [{}]
    paths = {}
    for y in states:
        DP[0][y] = log(start[y]) + log(emit[y][observations[0]]) # notice we use log probabilities
        paths[y] = [y]
    # max-product
    for t in range(1, len(observations)):
        # store max-product results in a table
        DP.append({})
        #Initialize an empty dictionary of new paths.
        newpaths = {} 
        for y in states:
            #Get the state of maximum probability for this state.
            #Tuple of probability and current state
            (prob, state) = max((DP[t-1][y0] + log(trans[y0][y]) + log(emit[y][observations[t]]), y0) for y0 in states)
            #Set the value of path for the DP at this point
            DP[t][y] = prob
            #Set the paths that are optimum for this state.
            newpaths[y] = paths[state] + [y]
            #print newpath
        #The new optimal paths per state
        paths = newpaths
    #Initialize at 0
    n = 0
    if len(observations)!=1:
        #t is the index of the last observation
        n = t
    #The probability-state pair with the maximum probability
    (prob, state) = max((DP[n][y], y) for y in states)
    #Return the path of the state that is optimum
    return paths[state]

print max_product(observations, states, start_dist, transition_dist, emission_dist)
