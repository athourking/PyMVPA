# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""FeaturewiseDatasetMeasure performing a univariate ANOVA."""

__docformat__ = 'restructuredtext'

import numpy as np

from mvpa.base import externals
from mvpa.measures.base import FeaturewiseDatasetMeasure
from mvpa.base.dataset import vstack
from mvpa.datasets.base import Dataset

# TODO: Extend with access to functionality from scipy.stats?
# For binary:
#  2-sample kolmogorov-smirnof might be interesting
#   (scipy.stats.ks_2samp) to judge if two conditions are derived
#   from different distributions (take it as 'activity' vs 'rest'),
#
# For binary+multiclass:
#  kruskal-wallis H-test (scipy.stats.kruskal)
#
# and may be some others

class OneWayAnova(FeaturewiseDatasetMeasure):
    """`FeaturewiseDatasetMeasure` that performs a univariate ANOVA.

    F-scores are computed for each feature as the standard fraction of between
    and within group variances. Groups are defined by samples with unique
    labels.

    No statistical testing is performed, but raw F-scores are returned as a
    sensitivity map. As usual F-scores have a range of [0,inf] with greater
    values indicating higher sensitivity.

    The sensitivity map is returned as a single-sample dataset. If SciPy is
    available the associated p-values will also be computed and are available
    from the 'fprob' feature attribute.
    """

    def __init__(self, targets_attr='targets', **kwargs):
        """
        Parameters
        ----------
        targets_attr : str
          What samples attribute to use as targets (labels).
        """
        self._targets_attr = targets_attr
        FeaturewiseDatasetMeasure.__init__(self, **kwargs)


    def __repr__(self, prefixes=None):
        if prefixes is None:
            prefixes = []
        if self._targets_attr != 'targets':
            prefixes = prefixes + ['targets_attr=%r' % (self._targets_attr)]
        return \
            super(FeaturewiseDatasetMeasure, self).__repr__(prefixes=prefixes)


    def _call(self, dataset):
        # This code is based on SciPy's stats.f_oneway()
        # Copyright (c) Gary Strangman.  All rights reserved
        # License: BSD
        #
        # However, it got tweaked and optimized to better fit into PyMVPA.

        # number of groups
        targets_sa = dataset.sa[self._targets_attr]
        labels = targets_sa.value
        ul = targets_sa.unique

        na = len(ul)
        bign = float(dataset.nsamples)
        alldata = dataset.samples

        # total squares of sums
        sostot = np.sum(alldata, axis=0)
        sostot *= sostot
        sostot /= bign

        # total sum of squares
        sstot = np.sum(alldata * alldata, axis=0) - sostot

        # between group sum of squares
        ssbn = 0
        for l in ul:
            # all samples for the respective label
            d = alldata[labels == l]
            sos = np.sum(d, axis=0)
            sos *= sos
            ssbn += sos / float(len(d))

        ssbn -= sostot
        # within
        sswn = sstot - ssbn

        # degrees of freedom
        dfbn = na-1
        dfwn = bign - na

        # mean sums of squares
        msb = ssbn / float(dfbn)
        msw = sswn / float(dfwn)
        f = msb / msw
        # assure no NaNs -- otherwise it leads instead of
        # sane unittest failure (check of NaNs) to crazy
        #   File "mtrand.pyx", line 1661, in mtrand.shuffle
        #  TypeError: object of type 'numpy.int64' has no len()
        # without any sane backtrace
        f[np.isnan(f)] = 0

        if externals.exists('scipy'):
            from scipy.stats import fprob
            return Dataset(f[np.newaxis], fa={'fprob': fprob(dfbn, dfwn, f)})
        else:
            return Dataset(f[np.newaxis])


class CompoundOneWayAnova(OneWayAnova):
    """Compound comparisons via univariate ANOVA.

    This measure compute an ANOVA F-score per each feature, for each
    one-vs-rest comparision for all unique labels in a dataset. Each F-score
    vector for each comparision is included in the return datasets as a separate
    samples. Corresponding p-values are avialable in feature attributes named
    'fprob_X', where `X` is the name of the actual comparision label. Note that
    p-values are only available, if SciPy is installed. The comparison labels
    for each F-vectore are also stored as 'targets' sample attribute in the
    returned dataset.
    """

    def _call(self, dataset):
        """Computes featurewise f-scores using compound comparisons."""

        targets_sa = dataset.sa[self._targets_attr]
        orig_labels = targets_sa.value
        labels = orig_labels.copy()

        # Lets create a very shallow copy of a dataset with just
        # samples and targets_attr
        dataset_mod = Dataset(dataset.samples,
                              sa={self._targets_attr : labels})
        results = []
        for ul in targets_sa.unique:
            labels[orig_labels == ul] = 1
            labels[orig_labels != ul] = 2
            f_ds = OneWayAnova._call(self, dataset_mod)
            if 'fprob' in f_ds.fa:
                # rename the fprob attribute to something label specific
                # to survive final aggregation stage
                f_ds.fa['fprob_' + str(ul)] = f_ds.fa.fprob
                del f_ds.fa['fprob']
            results.append(f_ds)

        results = vstack(results)
        results.sa[self._targets_attr] = targets_sa.unique
        return results
