.. -*- mode: rst; fill-column: 78; indent-tabs-mode: nil -*-
.. ex: set sts=4 ts=4 sw=4 et tw=79:
  ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###
  #
  #   See COPYING file distributed along with the PyMVPA package for the
  #   copyright and license terms.
  #
  ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###

.. index:: Tutorial
.. _chap_tutorial_mappers:

***************************************
Part 3: Mappers -- The Swiss Army Knife
***************************************

In the :ref:`previous tutorial part <chap_tutorial_datasets>` we have discovered a
magic ingredient of datasets: a mapper. Mappers are probably the most
powerful concept in PyMVPA, and there is little one would do without them.
As a matter of fact, even in the :ref:`first tutorial part
<chap_tutorial_start>` we have used them already, without even seeing them.

In general, a mapper is an algorithm that transforms data.
This transformation can be as simple as selecting a subset of data, or as
complex as a multi-stage preprocessing pipeline. Some transformations are
reversible, others are not. Some are simple one-step computations, others
are iterative algorithms that have to be trained on data before they can be
used. In PyMVPA, all these transformations are :mod:`~mvpa.mappers`.

Let's create a dummy dataset (5 samples, 12 features). This time we will use a
new method to create the dataset, the `dataset_wizard`. Here it is fully
equivalent to a regular constructor call (i.e.  `~mvpa.datasets.base.Dataset`),
but we will shortly see some nice convenience aspects.

>>> from tutorial_lib import *
>>> ds = dataset_wizard(np.ones((5, 12)))
>>> ds.shape
(5, 12)

A mapper is a :term:`dataset attribute`, hence it is stored in the
corresponding attribute collection. However, not every dataset actually has
a mapper. For example, the simple one we have just created doesn't have any:

>>> 'mapper' in ds.a
False

Now let's look at a very similar dataset that only differs in a tiny but
a very important detail:

>>> ds = dataset_wizard(np.ones((5, 4, 3)))
>>> ds.shape
(5, 12)
>>> 'mapper' in ds.a
True
>>> print ds.a.mapper
<FlattenMapper>

We see that the resulting dataset looks identical to the one above, but this time
it got created from a 3D samples array (i.e. five samples, where each is a 4x3
matrix). Somehow this 3D array got transformed into a 2D samples array in the
dataset. This magic behavior is unveiled by observing that the dataset's mapper
is a `~mvpa.mappers.flatten.FlattenMapper`.

The purpose of this mapper is precisely what we have just observed: reshaping
data arrays into 2D. It does it by preserving the first axis (in PyMVPA datasets
this is the axis that separates the samples) and concatenates all other axis
into the second one.

Since mappers represent particular transformations they can also be seen as a
protocol of what has been done. If we look at the dataset, we know that it had
been flattened on the way from its origin to a samples array in a dataset. This
feature can become really useful, if the processing become more complex. Let's
look at a possible next step -- selecting a subset of interesting features:

>>> myfavs = [1, 2, 8, 10]
>>> subds = ds[:, myfavs]
>>> subds.shape
(5, 4)
>>> 'mapper' in subds.a
True
>>> print subds.a.mapper
<ChainMapper: <Flatten>-<FeatureSlice>>

Now the situation has changed: *two* new mappers appeared in the dataset -- a
`~mvpa.mappers.base.ChainMapper` and a `~mvpa.mappers.base.FeatureSliceMapper`.
The latter describes (and actually performs) the slicing operation we just made,
while the former encapsulates the two mappers into a processing pipeline.
We can see that the mapper chain represents the processing history of the
dataset like a breadcrumb track.

As it has been mentioned, mappers  not only can transform a single dataset, but
can be feed with other data (as long as it is compatible with the mapper).

>>> fwdtest = np.arange(12).reshape(4,3)
>>> print fwdtest
[[ 0  1  2]
 [ 3  4  5]
 [ 6  7  8]
 [ 9 10 11]]
>>> fmapped = subds.a.mapper.forward1(fwdtest)
>>> fmapped.shape
(4,)
>>> print fmapped
[ 1  2  8 10]

Although `subds` has less features than our input data, forward mapping applies
the same transformation that had been done to the dataset itself also to our
test 4x3 array. The procedure yields a feature vector of the same shape as the
one in `subds`. By looking at the forward-mapped data, we can verify that the
correct features have been chosen.


Doing ``get_haxby2001_data()`` From Scratch
===========================================

Now we have pretty much all the pieces that we need to perform a full
cross-validation analysis. Remember, in :ref:`part one of the tutorial
<chap_tutorial_start>` we cheated a bit, by using a magic function to load the
preprocessed fMRI data. This time we are more prepared. We know how to
load fMRI data from timeseries images, we know how to add and access
attributes in a dataset, we know how to slice datasets, and we know that
we can manipulate datasets with mappers.

Now our goal is to combine all these little pieces into the code that produces
the dataset we already used at beginning. That is:

  A *pattern of activation* for each stimulus category in each half of the
  data (split by odd vs. even runs; i.e. 16 samples), including the
  associated :term:`sample attribute`\ s that are necessary to perform a
  cross-validated classification analysis of the data.

We have already seen how fMRI data can be loaded from NIfTI images, but this
time we need more than just the EPI images. For a classification analysis we
also need to associate each sample with a corresponding experimental condition,
i.e. a class label, also sometimes called :term:`target` value.  Moreover, for
a cross-validation procedure we also need to partition the full dataset into,
presumably, independent :term:`chunk`\ s. Independence is critical to achieve an
unbiased estimate of the generalization performance of a classifier, i.e. its
accuracy in predicting the correct class label for new data, unseen during
training. So, where do we get this information from?

Both, target values and chunks are defined by the design of the experiment.
In the simplest case the target value for an fMRI volume sample is the
experiment condition that has been present/active while the volume has been
acquired. However, there are more complicated scenarios which we will look
at later on. Chunks of independent data correspond to what fMRI volumes are
assumed to be independent. The properties of the MRI acquisition process
cause subsequently acquired volumes to be *very* similar, hence they cannot
be considered as independent. Ideally, the experiment is split into several
acquisition sessions, where the sessions define the corresponding data
chunks.

There are many ways to import this information into PyMVPA. The most simple
one is to create a two-column text file that has the target value in the
first column, and the chunk identifier in the second, with one line per
volume in the NIfTI image.

>>> # directory that contains the data files
>>> datapath = os.path.join(tutorial_data_path, 'data')
>>> attr = SampleAttributes(os.path.join(datapath, 'attributes.txt'))
>>> len(attr.targets)
1452
>>> print np.unique(attr.targets)
['bottle' 'cat' 'chair' 'face' 'house' 'rest' 'scissors' 'scrambledpix'
 'shoe']
>>> len(attr.chunks)
1452
>>> print np.unique(attr.chunks)
[  0.   1.   2.   3.   4.   5.   6.   7.   8.   9.  10.  11.]

`SampleAttributes` allows us to load this type of file, and access its
content. We got 1452 label and chunk values, one for each volume. Moreover,
we see that there are nine different conditions and 12 different chunks.

Now we can load the fMRI data, as we have done before -- only loading
voxels corresponding to a mask of ventral temporal cortex, and assign the
samples attributes to the dataset. `fmri_dataset()` allows us to pass them
directly:

>>> fds = fmri_dataset(samples=os.path.join(datapath, 'bold.nii.gz'),
...                    targets=attr.targets, chunks=attr.chunks,
...                    mask=os.path.join(datapath, 'mask_vt.nii.gz'))
>>> fds.shape
(1452, 577)
>>> print fds.sa
<SampleAttributesCollection: chunks,time_indices,targets,time_coords>

We got the dataset that we already know from the last part, but this time
is also has information about chunks and targets.

The next step is to extract the *patterns of activation* that we are
interested in from the dataset. But wait! We know that fMRI data is
typically contaminated with a lot of noise, or actually *information* that
we are not interested in. For example, there are temporal drifts in the
data (the signal tends to increase when the scanner is warming up). We
also know that the signal is not fully homogeneous throughout the brain.

All these artifacts carry a lot of variance that is (hopefully) unrelated
to the experiment design, and we should try to remove it to present the
classifier with the cleanest signal possible. There are countless ways to
preprocess the data to try to achieve this goal. Some keywords are:
high/low/band-pass filtering, de-spiking, motion-correcting, intensity
normalization, and so on. In this tutorial, we keep it simple. The data we
have just loaded is already motion corrected. For every experiment that is
longer than a few minutes, as in this case, temporal trend removal, or
:term:`detrending` is crucial.

Detrending
----------
PyMVPA provides functionality to remove polynomial trends from the data,
meaning that polynomials are fitted to the timeseries and only what is not
explained by them remains in the dataset. In the case of linear detrending,
this means fitting a straight line to the timeseries of each voxel via linear
regression and taking the residuals as the new feature values. Detrending can
be seen as a type of data transformation, hence in PyMVPA it is implemented as
a mapper.

>>> detrender = PolyDetrendMapper(polyord=1, chunks_attr='chunks')

What we have just created is a mapper that will perform chunk-wise linear
(1st-order polynomial) detrending. Chunk-wise detrending is desirable,
since our data stems from 12 different runs, and the assumption of a
continous linear trend across all runs is not appropriate. The mapper is
going to use the ``chunks`` attribute to identify the chunks in the
dataset.

We have seen that we could simply forward-map our dataset with this mapper.
However, if we want to have the mapper present in the datasets processing
history breadcrumb track, we can use its
`~mvpa.datasets.base.Dataset.get_mapped()` method. This method will cause
the dataset to map a shallow copy of itself with the given mapper, and
return it. Let's try:

>>> detrended_fds = fds.get_mapped(detrender)
>>> print detrended_fds.a.mapper
<ChainMapper: <Flatten>-<FeatureSlice>-<PolyDetrend: ord=1>>

``detrended_fds`` is easily identifiable as a dataset that has been
flattened, sliced, and linearily detrended.


Normalization
-------------

While this will hopefully have solved the problem of temporal drifts in the
data, we still have inhomogeneous voxel intensities, but there are many
possible approaches to fix it. For this tutorial we are again following a
simple one, and perform a feature-wise, chunk-wise Z-scoring of the data.  This
has many advantages. First it is going to scale all features into approximately
the same range, and also remove their mean.  The latter is quite important,
since some classifiers cannot deal with not demeaned data. However, we are not
going to perform a very simple Z-scoring removing the global mean, but use the
*rest* condition samples of the data to estimate mean and standard deviation.
Scaling features using these parameters yields a score corresponding to the
per-timepoint voxel intensity difference from the *rest* average.

This type of data :term:`normalization` is, you guessed it, also
implemented as a mapper:

>>> zscorer = ZScoreMapper(param_est=('targets', ['rest']))

This configures to perform a chunk-wise (the default) Z-scoring, while
estimating mean and standard deviation from samples targets with 'rest' in
the respective chunk of data.

Remember, all mappers return new datasets that only have copies of what has
been modified. However, both detrending and Z-scoring have or will modify
the samples themselves. That means that the memory consumption will triple!
We will have the original data, the detrended data, and the Z-scored data,
but typically we are only interested in the final processing stage. The
reduce the memory footprint, both mappers have siblings that perform the
same processing, but without copying the data. For
`~mvpa.mappers.detrend.PolyDetrendMapper` this is
`~mvpa.mappers.detrend.poly_detrend()`, and for
`~mvpa.mappers.zscore.ZScoreMapper` this is
`~mvpa.mappers.zscore.zscore()`. The following call will do the same as the
mapper we have created above, but using less memory:

>>> zscore(detrended_fds, param_est=('targets', ['rest']))
>>> fds = detrended_fds
>>> print fds.a.mapper
<ChainMapper: <Flatten>-<FeatureSlice>-<PolyDetrend: ord=1>-<ZScore>>

.. exercise::

   Look at the :ref:`example_smellit` example. Using the techniques from
   this example, explore the dataset we have just created and look at the
   effect of detrending and Z-scoring.

The resulting dataset is now both detrended and normalized. The information
is nicely presented in the mapper. From this point on we have no use for
the samples of the *rest* category anymore, hence we remove them from the
dataset:

>>> fds = fds[fds.sa.targets != 'rest']
>>> print fds.shape
(864, 577)


Computing *Patterns Of Activiation*
-----------------------------------

The last preprocessing step, we need to replicate, is computing the
actual *patterns of activation*. In the original study Haxby and colleagues
performed a GLM-analysis of odd vs. even runs of the data respectively and
used the corresponding contrast statistics (stimulus category vs. rest) as
classifier input. In this tutorial, we will use a much simpler shortcut and
just compute *mean* samples per condition for both odd and even
independently.

To achieve this, we first add a new sample attribute to assign a
corresponding label to each sample in the dataset, indication to which of
both run-types is belongs to:

>>> rnames = {0: 'even', 1: 'odd'}
>>> fds.sa['runtype'] = [rnames[c % 2] for c in fds.sa.chunks]

The rest is trivial. For cases like this -- applying a function (i.e. mean)
to a set of groups of samples (all combinations of stimulus category and
run-type) -- PyMVPA has `~mvpa.mappers.fx.FxMapper`. it comes with a number
of convenience functions. The one we need here is
`~mvpa.mappers.fx.mean_group_sample()`. It takes a list of sample attributes,
determines all possible combinations of its unique values, selects dataset
samples corresponding to these combinations, and averages them. Finally,
since this is also a mapper, a new dataset with mean samples is returned:

>>> averager = mean_group_sample(['targets', 'runtype'])
>>> type(averager)
<class 'mvpa.mappers.fx.FxMapper'>
>>> fds = fds.get_mapped(averager)
>>> fds.shape
(16, 577)
>>> print fds.sa.targets
['bottle' 'cat' 'chair' 'face' 'house' 'scissors' 'scrambledpix' 'shoe'
 'bottle' 'cat' 'chair' 'face' 'house' 'scissors' 'scrambledpix' 'shoe']

Here we go! We now have a fully-preprocessed dataset: detrended, normalized,
with one sample per stimulus condition that is an average for odd and even runs
respectively. Now we could do some serious classification, and we will do it
:ref:`part four of the tutorial <chap_tutorial_classifiers>`, but there is still an
important aspect of mappers we have to look at first.


There and back again -- a Mapper's tale
=======================================

Let's take a look back at the simple datasets from the start of the tutorial
part.

>>> print ds
<Dataset: 5x12@float64, <a: mapper>>
>>> print ds.a.mapper
<FlattenMapper>

A very important feature of mappers is that they allow to reverse a
transformation, if that is possible. In case of the simple dataset we can
ask the mapper to undo the flattening and to put our samples back into the
original 3D shape.

>>> orig_data = ds.a.mapper.reverse(ds.samples)
>>> orig_data.shape
(5, 4, 3)

In interactive scripting sessions this is would be a relatively bulky command to
type, although it might be quite frequently used. To make ones fingers suffer
less there is a little shortcut that does exactly the same:

>>> orig_data = ds.O
>>> orig_data.shape
(5, 4, 3)

It is important to realize that reverse-mapping not only works with a single
mapper, but also with a `~mvpa.mappers.base.ChainMapper`. Going back to our demo
dataset from the beginning we can see how it works:

>>> print subds
<Dataset: 5x4@float64, <a: mapper>>
>>> print subds.a.mapper
<ChainMapper: <Flatten>-<FeatureSlice>>
>>> subds.nfeatures
4
>>> revtest = np.arange(subds.nfeatures) + 10
>>> print revtest
[10 11 12 13]
>>> rmapped = subds.a.mapper.reverse1(revtest)
>>> rmapped.shape
(4, 3)
>>> print rmapped
[[ 0 10 11]
 [ 0  0  0]
 [ 0  0 12]
 [ 0 13  0]]

Reverse mapping of a single sample (one-dimensional feature vector) through the
mapper chain created a 4x3 array that corresponds to the dimensions of a sample
in our original data space. Moreover, we see that each feature value is
precisely placed into the position that corresponds to the features selected
in the previous dataset slicing operation.

But now let's look at our fMRI dataset again. Here the mapper chain is a little
more complex:

>>> print fds.a.mapper
<ChainMapper: <Flatten>-<FeatureSlice>-<PolyDetrend: ord=1>-<ZScore>-<Fx: fx=mean>>

Initial flattening followed by mask, detrending, Z-scoring and finally
averaging. We would reverse mapping do in this case? Let's test:

>>> fds.nfeatures
577
>>> revtest = np.arange(100, 100 + fds.nfeatures)
>>> rmapped = fds.a.mapper.reverse1(revtest)
>>> rmapped.shape
(40, 64, 64)

What happens is excatly what we expect: The initial one-dimensional vector
is passed backwards through the mapper chain. Reverting a group-based
averaging doesn't make much sense for a single vector, hence it is ignored.
Same happens for Z-Scoring and temporal detrending. However, for all
remaining mappers the transformations are reverse. First un-masked, and
then reshaped into the original dimensionality -- the brain volume.

We can check that this is really the case by only reverse-mapping through
the first two mappers in the chain and compare the result:

>>> rmapped_partial = fds.a.mapper[:2].reverse1(revtest)
>>> (rmapped == rmapped_partial).all()
True

In case you are wondering: The `~mvpa.mappers.base.ChainMapper` behaves
like a regular Python list. We have just selected the first two mappers in
the list as another `~mvpa.mappers.base.ChainMapper` and used that one for
reverse-mapping.


Back To NIfTI
-------------

One last interesting aspect in the context of reverse mapping: Whenever it
is necessary to export data from PyMVPA, such as results, dataset mappers
also play a critical role. For example we can easily export the ``revtest``
vector into a NIfTI brain volume image. This is possible because the mapper
can put it back into 3D space, and because the dataset also stores
information about the original source NIfTI image.

>>> 'imghdr' in fds.a
True

PyMVPA offers `~mvpa.datasets.mri.map2nifti()`, a function to combine these
two thing and convert any vector into the corresponding NIfTI image:

>>> nimg = map2nifti(fds, revtest)

This image can now be safed to a file (e.g. ``nimg.save('mytest.nii.gz')``).
In this format it is now compatible with the vast majority of neuroimaging
software.

.. exercise::

   Save the NIfTI image to some file, and use an MRI viewer to overlay it
   on top of the anatomical image in the demo dataset. Does it match our
   original mask image of ventral temporal cortex?

There are much more mappers in PyMVPA than we could cover in the tutorial
part. Some more will be used in other parts, but even more can be found the
:mod:`~mvpa.mappers` module. Even though the all implement different
transformations, they can all be used in the same way, and can all be
combined into a chain.

Now we are really ready for :ref:`part four of the tutorial <chap_tutorial_classifiers>`.



.. only:: html

  References
  ==========

  .. autosummary::
     :toctree: generated

     ~mvpa.mappers
     ~mvpa.mappers.base.Mapper
     ~mvpa.mappers.base.FeatureSliceMapper
     ~mvpa.mappers.flatten.FlattenMapper
     ~mvpa.mappers.fx.FxMapper
     ~mvpa.mappers.base.ChainMapper
