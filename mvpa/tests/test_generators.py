# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Unit tests for generators."""


import numpy as np

from mvpa.testing.tools import ok_, assert_array_equal, assert_true, \
        assert_false, assert_equal, assert_raises

from mvpa.datasets import dataset_wizard
from mvpa.generators.splitters import Splitter
from mvpa.base.node import ChainNode
from mvpa.generators.partition import OddEvenPartitioner


def give_data():
    # 100x10, 10 chunks, 4 targets
    return dataset_wizard(np.random.normal(size=(100,10)),
                          targets=[ i%4 for i in range(100) ],
                          chunks=[ i/10 for i in range(100)])


def test_splitter():
    ds = give_data()
    # split with defaults
    spl1 = Splitter('chunks')
    assert_raises(NotImplementedError, spl1, ds)

    splits = list(spl1.generate(ds))
    assert_equal(len(splits), len(ds.sa['chunks'].unique))

    for split in splits:
        # it should have perform basic slicing!
        assert_true(split.samples.base is ds.samples)
        assert_equal(len(split.sa['chunks'].unique), 1)
        assert_true('lastsplit' in split.a)
    assert_true(splits[-1].a.lastsplit)

    # now again, more customized
    spl2 = Splitter('targets', attr_values = [0,1,1,2,3,3,3], count=4,
                   noslicing=True)
    splits = list(spl2.generate(ds))
    assert_equal(len(splits), 4)
    for split in splits:
        # it should NOT have perform basic slicing!
        assert_false(split.samples.base is ds.samples)
        assert_equal(len(split.sa['targets'].unique), 1)
        assert_equal(len(split.sa['chunks'].unique), 10)
    assert_true(splits[-1].a.lastsplit)

    # two should be identical
    assert_array_equal(splits[1].samples, splits[2].samples)

    # now go wild and split by feature attribute
    ds.fa['roi'] = np.repeat([0,1], 5)
    # splitter should auto-detect that this is a feature attribute
    spl3 = Splitter('roi')
    splits = list(spl3.generate(ds))
    assert_equal(len(splits), 2)
    for split in splits:
        assert_true(split.samples.base is ds.samples)
        assert_equal(len(split.fa['roi'].unique), 1)
        assert_equal(split.shape, (100, 5))

    # and finally test chained splitters
    cspl = ChainNode([spl2, spl3, spl1])
    splits = list(cspl.generate(ds))
    # 4 target splits and 2 roi splits each and 10 chunks each
    assert_equal(len(splits), 80)


def test_partitionmapper():
    ds = give_data()
    oep = OddEvenPartitioner()
    parts = list(oep.generate(ds))
    assert_equal(len(parts), 2)
    for i, p in enumerate(parts):
        assert_array_equal(p.sa['partitions'].unique, [1, 2])
        assert_equal(p.a.partitions_set, i)
        assert_equal(len(p), len(ds))