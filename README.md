# Dyadic Phase Transport in Semiprime Integers

This repository reports empirical results on the angular structure of semiprime integers, based on a large-scale numerical analysis in the 64-bit regime.

We show that the phase associated with a semiprime integer $𝑛=𝑝𝑞$ is not independent, but instead follows a dyadic phase composition law governed by the phases of its prime factors.

## Summary of results

Given a semiprime $𝑛=𝑝𝑞$, we associate to each integer 𝑥 an angular coordinate $𝜃𝑥∈[0,2𝜋)$.

The main empirical findings are:

* Phase composition law
    $𝜃𝑛≈(𝜃𝑝+𝜃𝑞)mod2𝜋$

* Dyadic carry bifurcation 
      When both factors lie in the same dyadic band 𝑘, the stability of the phase transport depends on whether 
      $𝑘𝑛=2𝑘n$ or $𝑘𝑛=2𝑘+1$.
* The carry case 
      $𝑘𝑛=2𝑘+1$ exhibits significantly tighter phase locking.
* Pendular dissipation law
      The residual phase error $𝛿=𝜃𝑛−(𝜃𝑝+𝜃𝑞)$ grows monotonically with the intra-dyadic imbalance $∣𝑢𝑝−𝑢𝑞∣$, where $𝑢𝑥=log2(𝑥)−⌊log2(𝑥)⌋$

Together, these results define a dyadic phase transport law for semiprime integers.
