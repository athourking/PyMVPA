#emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""PyMVPA: Dataset container"""

import numpy as N
import operator
import random

# TODO? yoh: There is too much in common between chunks and labels....

class Dataset(object):
    """ This class provides a container to store all necessary data to perform
    MVPA analyses. These are the data samples, as well as the labels
    associated with these patterns. Additionally samples can be grouped into
    chunks.
    """

    # Common parameters for all subclasses. To don't replicate, __init__.__doc__
    # has to be extended with them after it is defined
    # TODO: discard such way or accept and introduce to derived methods...
    __initparams__ = \
        """
        samples -
        labels  -
        chunks  -
        dtype   - if None -- do not change data type if samples
                  is an ndarray. Otherwise convert samples to dtype"""

    def __init__(self, samples, labels, chunks, dtype=None ):
        """ Initialize the Dataset.

        Parameters:
        """
        # initialize containers
        self.__samples = None
        self.__labels = None
        self.__chunks = None
        self.__origlabels = None
        self.__uniqueLabels = None
        self.__uniqueChunks = None

        # 1d arrays or simple sequences are assumed to be a single pattern
        if (not isinstance(samples, N.ndarray)):
            samples = N.array(samples, ndmin=2)
        else:
            if samples.ndim < 2 \
                   or (not dtype is None and dtype != samples.dtype):
                if dtype is None:
                    dtype = samples.dtype
                samples = N.array(samples, ndmin=2, dtype=dtype)

        # only samples x features matrices are supported
        if len(samples.shape) > 2:
            raise ValueError, "Only (samples x features) -> 2d sample " \
                            + "are supported. Consider MappedDataset if " \
                            + "applicable."

        # done -> store
        self.__samples = samples

        # check if labels is supplied as a sequence
        try:
            if len(labels) != len(self.samples):
                raise ValueError, "Length of 'labels' [%d]" % len(labels)\
                      + " has to match the number of patterns" \
                      + " [%d]." % len(self.samples)
            # store the sequence as array
            labels = N.array(labels)

        except TypeError:
            # make sequence of identical value matching the number of patterns
            labels = N.repeat( labels, len( self.samples ) )

        # done -> store
        self._setLabels(labels)

        # if no chunk information is given assume that every pattern is its
        # own chunk
        if chunks == None:
            chunks = N.arange( len( self.samples ) )
        else:
            try:
                if len( chunks ) != len( self.samples ):
                    raise ValueError, "Length of 'chunks' has to match the" \
                                      " number of samples."
                # store the sequence as array
                chunks = N.array( chunks )

            except TypeError:
                # make sequence of identical value matching the number of
                # patterns
                chunks = N.repeat( chunks, len( self.samples ) )

        # done -> store
        self._setChunks(chunks)

    __init__.__doc__ += __initparams__


    def __repr__(self):
        """ String summary over the object
        """
        return """Dataset / %d x %d""" % \
               (self.nsamples, self.nfeatures)


    def __iadd__( self, other ):
        """ Merge the samples of one Dataset object to another (in-place).

        Please note that the samples, labels and chunks are simply
        concatenated to create a Dataset object that contains the patterns of
        both objects. No further processing is done. In particular the chunk
        values are not modified: Samples with the same origin from both
        Datasets will still share the same chunk.
        """
        if not self.nfeatures == other.nfeatures:
            raise ValueError, "Cannot add Dataset, because the number of " \
                              "feature do not match."

        self.__samples = \
            N.concatenate( ( self.samples, other.samples ), axis=0)
        self._setLabels( N.concatenate( ( self.labels, other.labels ), axis=0) )
        self._setChunks( N.concatenate( ( self.chunks, other.chunks ), axis=0) )

        return self


    def __add__( self, other ):
        """ Merge the samples two Dataset objects.

        Please note that the samples, labels and chunks are simply
        concatenated to create a Dataset object that contains the patterns of
        both objects. No further processing is done. In particular the chunk
        values are not modified: Samples with the same origin from both
        Datasets will still share the same chunk.
        """
        out = Dataset( self.__samples,
                       self.__labels,
                       self.__chunks )

        out += other

        return out


    def selectFeatures( self, ids ):
        """ Select a number of features from the current set.

        'ids' is a list of feature IDs

        Returns a new Dataset object with a view of the original samples
        array (no copying is performed).
        """
        return Dataset( self.__samples[:, ids],
                        self.__labels,
                        self.__chunks )


    def selectSamples( self, mask ):
        """ Choose a subset of samples.

        Returns a new Dataset object containing the selected sample
        subset.
        """
        # without having a sequence a index the masked sample array would
        # loose its 2d layout
        if not operator.isSequenceType( mask ):
            mask = [mask]

        return Dataset( self.samples[mask, ],
                        self.labels[mask, ],
                        self.chunks[mask, ] )


    def permutedRegressors( self, status, perchunk = True ):
        """ Permute the labels.

        Calling this method with 'status' set to True, the labels are
        permuted among all samples.

        If 'perorigin' is True permutation is limited to samples sharing the
        same chunk value. Therefore only the association of a certain sample
        with a label is permuted while keeping the absolute number of
        occurences of each label value within a certain chunk constant.

        If 'status' is False the original labels are restored.
        """
        if not status:
            # restore originals
            if self.__origlabels == None:
                raise RuntimeError, 'Cannot restore labels. ' \
                                    'randomizedRegressors() has never been ' \
                                    'called with status == True.'
            self._setLabels(self.__origlabels)
            self.__origlabels = None
        else:
            # permute labels per origin

            # make a backup of the original labels
            self.__origlabels = self.__labels.copy()

            # now scramble the rest
            if perchunk:
                for o in self.uniquechunks:
                    self.__labels[self.chunks == o ] = \
                        N.random.permutation( self.labels[ self.chunks == o ] )
                self._setLabels(self.__labels) # to recompute uniquelabels
            else:
                self._setLabels(N.random.permutation(self.__labels))


    def getRandomSamples( self, nperlabel ):
        """ Select a random set of samples.

        If 'nperlabel' is an integer value, the specified number of samples is
        randomly choosen from the group of samples sharing a unique label
        value ( total number of selected samples: nperlabel x len(uniquelabels).

        If 'nperlabel' is a list which's length has to match the number of
        unique label values. In this case 'nperlabel' specifies the number of
        samples that shall be selected from the samples with the corresponding
        label.

        The method returns a Dataset object containing the selected
        samples.
        """
        # if interger is given take this value for all classes
        if isinstance(nperlabel, int):
            nperlabel = [ nperlabel for i in self.uniquelabels ]

        sample = []
        # for each available class
        for i, r in enumerate(self.uniquelabels):
            # get the list of pattern ids for this class
            sample += random.sample( (self.labels == r).nonzero()[0],
                                     nperlabel[i] )

        return self.selectSamples( sample )


    def _setLabels(self, labels):
        """ Sets labels and recomputes uniquelabels
        """
        self.__labels = labels
        self.__uniqueLabels = None # None!since we might not need them


    def _setChunks(self, chunks):
        """ Sets chunks and recomputes uniquechunks
        """
        self.__chunks = chunks
        self.__uniqueChunks = None # None!since we might not need them


    def getNSamples( self ):
        """ Currently available number of patterns.
        """
        return self.samples.shape[0]


    def getNFeatures( self ):
        """ Number of features per pattern.
        """
        return self.samples.shape[1]


    def getSamples( self ):
        """ Returns the sample matrix.
        """
        return self.__samples


    def getLabels( self ):
        """ Returns the label vector.
        """
        return self.__labels


    def getChunks( self ):
        """ Returns the sample chunking vector.

        Each unique value in this vector defines a group of samples.
        """
        return self.__chunks


    def getUniqueLabels(self):
        """ Returns an array with all unique class labels in the labels vector.

        Late evaluation for speedup in cases when uniquelabels is not needed
        """
        if self.__uniqueLabels is None:
            self.__uniqueLabels = N.unique( self.labels )
            assert(not self.__uniqueLabels is None)
        return self.__uniqueLabels


    def getUniqueChunks( self ):
        """ Returns an array with all unique labels in the chunk vector.

        Late evaluation for speedup in cases when uniquechunks is not needed
        """
        if self.__uniqueChunks is None:
            self.__uniqueChunks = N.unique( self.chunks )
            assert(not self.__uniqueChunks is None)
        return self.__uniqueChunks


    def getNSamplesPerLabel( self ):
        """ Returns the number of samples per unique label.
        """
        return [ len(self.samples[self.labels == l]) \
                    for l in self.uniquelabels ]


    def getNSamplesPerChunk( self ):
        """ Returns the number of samples per unique chunk value.
        """
        return [ len(self.samples[self.chunks == c]) \
                    for c in self.uniquechunks ]


    # read-only class properties
    samples         = property( fget=getSamples )
    labels          = property( fget=getLabels )
    chunks          = property( fget=getChunks )
    nsamples        = property( fget=getNSamples )
    nfeatures       = property( fget=getNFeatures )
    uniquelabels    = property( fget=getUniqueLabels )
    uniquechunks    = property( fget=getUniqueChunks )
    samplesperlabel = property( fget=getNSamplesPerLabel )
    samplesperchunk = property( fget=getNSamplesPerChunk )
