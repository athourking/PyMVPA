# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Unit tests for PyMVPA ridge regression classifier"""

from mvpa.clfs.ridge import RidgeReg
from scipy.stats import pearsonr
from tests_warehouse import *

class RidgeRegTests(unittest.TestCase):

    def test_ridge_reg(self):
        # not the perfect dataset with which to test, but
        # it will do for now.
        data = datasets['dumb']

        clf = RidgeReg()

        clf.train(data)

        # prediction has to be almost perfect
        # test with a correlation
        pre = clf.predict(data.samples)
        cor = pearsonr(pre,data.targets)
        self.failUnless(cor[0] > .8)

        # do again for fortran implementation
        # DISABLE for now, at it is known to be broken
#        clf = RidgeReg(implementation='gradient')
#        clf.train(data)
#        cor = pearsonr(clf.predict(data.samples), data.targets)
#        print cor
#        self.failUnless(cor[0] > .8)



    def test_ridge_reg_state(self):
        data = datasets['dumb']

        clf = RidgeReg()

        clf.train(data)

        clf.ca.enable('predictions')

        p = clf.predict(data.samples)

        self.failUnless((p == clf.ca.predictions).all())


def suite():
    return unittest.makeSuite(RidgeRegTests)


if __name__ == '__main__':
    import runner

