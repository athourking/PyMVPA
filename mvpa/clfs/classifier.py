#emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Base classes for all classifiers."""

__docformat__ = 'restructuredtext'

import operator
import numpy as N

from copy import deepcopy
from sets import Set

from mvpa.datasets.maskmapper import MaskMapper
from mvpa.datasets.splitter import NoneSplitter
from mvpa.misc.state import State

if __debug__:
    from mvpa.misc import debug

class Classifier(State):
    """Abstract classifier class to be inherited by all classifiers

    Required behavior:

    For every classifier is has to be possible to be instanciated without
    having to specify the training pattern.

    Repeated calls to the train() method with different training data have to
    result in a valid classifier, trained for the particular dataset.

    It must be possible to specify all classifier parameters as keyword
    arguments to the constructor.

    Recommended behavior:

    Derived classifiers should provide access to *values* -- i.e. that
    information that is finally used to determine the predicted class label.

    Michael: Maybe it works well if each classifier provides a 'values'
             state member. This variable is a list as long as and in same order
             as Dataset.uniquelabels (training data). Each item in the list
             corresponds to the likelyhood of a sample to belong to the
             respective class. However the sematics might differ between
             classifiers, e.g. kNN would probably store distances to class-
             neighbours, where PLF would store the raw function value of the
             logistic function. So in the case of kNN low is predictive and for
             PLF high is predictive. Don't know if there is the need to unify
             that.

             As the storage and/or computation of this information might be
             demanding its collection should be switchable and off be default.

    Nomenclature
     * predictions  : corresponds to the quantized labels if classifier spits
                      out labels by .predict()
     * values : might be different from predictions if a classifier's predict()
                   makes a decision based on some internal value such as
                   probability or a distance.
    """
    # Dict that contains the parameters of a classifier.
    # This shall provide an interface to plug generic parameter optimizer
    # on all classifiers (e.g. grid- or line-search optimizer)
    # A dictionary is used because Michael thinks that access by name is nicer.
    # Additonally Michael thinks ATM that additonal information might be
    # necessary in some situations (e.g. reasonably predefined parameter range,
    # minimal iteration stepsize, ...), therefore the value to each key should
    # also be a dict or we should use mvpa.misc.param.Parameter'...
    params = {}

    def __init__(self, **kwargs):
        """Cheap initialization.
        """
        State.__init__(self, **kwargs)

        # TODO: It is often as important to know how well we fit the
        # training data, thus we should enabled states below, and
        # provide proper assignment in the derived classes. Also think if we need
        # "training_error" or such...
        self._registerState('trained_values', enabled=False,
                            doc="Internal values for the trained values seen by the classifier")
        self._registerState('trained_predictions', enabled=False,
                            doc="Internal values for the trained predictions seen by the classifier")
        self._registerState('values', enabled=False,
                            doc="Internal values seen by the classifier")
        self._registerState('predictions', enabled=True,
                            doc="Reported predicted values")


    def __str__(self):
        return "%s\n %s" % (`self`, State.__str__(self))

    def train(self, data):
        """
        """
        raise NotImplementedError


    def predict(self, data):
        """
        """
        raise NotImplementedError

#
# Base classifiers of various kinds
#

class BoostedClassifier(Classifier):
    """Classifier containing the farm of other classifiers.

    Should rarely be used directly. Use one of its childs instead
    """

    def __init__(self, clfs=[], **kwargs):
        """Initialize the instance.

        :Parameters:
          `clfs` : list
            list of classifier instances to use
          **kargs : dict
            dict of keyworded arguments which might get used
            by State or Classifier
        """
        Classifier.__init__(self, **kwargs)

        self._setClassifiers(clfs)
        """Store the list of classifiers"""

        # should not be needed if we have prediction_values upstairs
        self._registerState("raw_predictions", enabled=False,
                            doc="Predictions obtained from each classifier")


    def __repr__(self):
        return "<%s with %d classifiers>" \
               % (self.__class__, len(self.clfs))


    def train(self, data):
        """
        """
        for clf in self.__clfs:
            clf.train(data)


    def predict(self, data):
        """
        """
        raw_predictions = [ clf.predict(data) for clf in self.__clfs ]
        if clf.isStateEnabled("values") and self.isStateEnabled("values"):
            values = [ clf["values"] for clf in self.__clfs ]
            self["raw_values"] = values

        self["raw_predictions"] = raw_predictions

        return raw_predictions


    def _setClassifiers(self, clfs):
        """Set the classifiers used by the boosted classifier

        We have to allow to set list of classifiers after the object
        was actually created. It will be used by
        BoostedMulticlassClassifier
        """
        self.__clfs = clfs
        """Classifiers to use"""

    clfs = property(fget=lambda x:x.__clfs,
                    fset=_setClassifiers,
                    doc="Used classifiers")


class ProxyClassifier(Classifier):
    """Classifier which decorates another classifier

    Possible uses:
      modify data somehow prior training/testing:
       normalization
       feature selection
       modification
      optimized classifier? 
    """

    def __init__(self, clf, **kwargs):
        """Initialize the instance

        :Parameters:
          clf : Classifier
            classifier based on which mask classifiers is created
          """
        Classifier.__init__(self, **kwargs)

        self.__clf = clf
        """Store the classifier to use."""


    def train(self, data):
        """
        """
        # base class nothing much -- just proxies requests to underlying classifier
        self.__clf.train(wdata)

        # for the ease of access
        self._copy_states_(self.__clf, deep=False)


    def predict(self, data):
        """
        """
        result = self.__clf.predict(data)
        # for the ease of access
        self._copy_states_(self.__clf, deep=False)
        return result

    clf = property(lambda x:x.__clf, doc="Used `Classifier`")



#
# Various combiners for CombinedClassifier
#

class Combiner(State):
    """Base class for combining decisions of multiple classifiers"""

    def call(self, clfs):
        """Call function

        :Parameters:
          clfs : list of Classifier
            List of classifiers to combine. Has to be classifiers (not
            pure predictions), since combiner might use some other
            state variables (value's) instead of pure prediction's
        """
        raise NotImplementedError


class MaximalVote(Combiner):
    """Provides a decision using maximal vote rule"""

    def __init__(self):
        """XXX Might get a parameter to use raw decision values if
        voting is not unambigous (ie two classes have equal number of
        votes
        """
        Combiner.__init__(self)

        self._registerState("predictions", enabled=True,
                            doc="Voted predictions")
        self._registerState("all_label_counts", enabled=False,
                            doc="Counts across classifiers for each label/sample")


    def __call__(self, clfs):
        """
        Extended functionality which might not be needed actually:
        Since `BinaryClassifier` might return a list of possible
        predictions (not just a single one), we should consider all of those
        """
        if len(clfs)==0:
            return []                   # to don't even bother

        all_label_counts = None
        for clf in clfs:
            # Lets check first if necessary state variable is enabled
            if not clf.isStateEnabled("predictions"):
                raise ValueError, "MaximalVote needs classifiers (such as " + \
                      "%s) with state 'predictions' enabled" % clf
            predictions = clf["predictions"]
            if all_label_counts is None:
                all_label_counts = [ {} for i in xrange(len(predictions)) ]

            # for every sample
            for i in xrange(len(predictions)):
                prediction = predictions[i]
                if not operator.isSequenceType(prediction):
                    prediction = (prediction,)
                for label in prediction: # for every label
                    # we might have multiple labels assigned XXX
                    # but might not -- don't remember now
                    if not all_label_counts[i].has_key(label):
                        all_label_counts[i][label] = 0
                    all_label_counts[i][label] += 1

        predictions = []
        # select maximal vote now for each sample
        for i in xrange(len(all_label_counts)):
            label_counts = all_label_counts[i]
            # lets do explicit search for max so we know
            # if it is unique
            maxk = []                   # labels of elements with max vote
            maxv = -1
            for k,v in label_counts.iteritems():
                if v>maxv:
                    maxk = [k]
                    maxv = v
                elif v==maxv:
                    maxk.append(k)

            assert len(maxk)>=1, \
                   "We should have obtained at least a single key of max label"

            if len(maxk)>1:
                warning("We got multiple labels %s which have the " % maxk +
                        "same maximal vote %d. XXX disambiguate" % maxv)
            predictions.append(maxk[0])

        self["all_label_counts"] = all_label_counts
        self["predictions"] = predictions
        return predictions



class CombinedClassifier(BoostedClassifier):
    """`BoostedClassifier` which combines predictions using some combine functor

    """

    def __init__(self, clfs=[], combiner=MaximalVote(), **kwargs):
        """Initialize the instance.

        :Parameters:
          `clfs` : list
            list of classifier instances to use
          `combiner`
            callable which takes care about combining multiple
            results into a single one (e.g. maximal vote)
          **kargs : dict
            dict of keyworded arguments which might get used
            by State or Classifier

        NB: `combiner` might need to operate not on 'predict' descrete
            labels but rather on raw 'class' values classifiers
            estimate (which is pretty much what is stored under
            `decision_values`
        """
        BoostedClassifier.__init__(self, clfs, **kwargs)

        self.__combiner = combiner
        """Functor destined to combine results of multiple classifiers"""


    def __repr__(self):
        return "<%s with %d classifiers and combiner %s>" \
               % (self.__class__.__name_, len(self.__clfs), `combiner`)


    def predict(self, data):
        """
        """
        raw_predictions = super(CombinedClassifier, self).predict(data)
        predictions = self.__combiner(self.clfs)
        self["predictions"] = predictions

        if self.isStateEnabled("values"):
            if self.__combiner.isStateEnabled("values"):
                # XXX or may be we could leave simply up to accessing .combiner?
                self["values"] = self.__combiner["values"]
            else:
                if __debug__:
                    warning("Boosted classifier %s has 'values' state" % self +
                            " enabled, but combiner has it disabled, thus no" +

                            " values could be provided")
        return predictions


    combiner = property(fget=lambda x:x.__combiner,
                        doc="Used combiner to derive a single result")


class BinaryClassifier(ProxyClassifier):
    """`ProxyClassifier` which maps set of two labels into +1 and -1
    """

    def __init__(self, clf, poslabels, neglabels, **kwargs):
        """
        :Parameters:
          clf : Classifier
            classifier to use
          poslabels : list
            list of labels which are treated as +1 category
          neglabels : list
            list of labels which are treated as -1 category
        """
        ProxyClassifier.__init__(self, clf, **kwargs)

        # Handle labels
        sposlabels = Set(poslabels) # so to remove duplicates
        sneglabels = Set(neglabels) # so to remove duplicates

        # check if there is no overlap
        overlap = sposlabels.intersection(sneglabels)
        if len(overlap)>0:
            raise ValueError("Sets of positive and negative labels for " +
                "BinaryClassifier must not overlap. Got overlap " %
                overlap)

        self.__poslabels = list(sposlabels)
        self.__neglabels = list(sneglabels)

        # define what values will be returned by predict: if there is
        # a single label - return just it alone, otherwise - whole
        # list
        # Such approach might come useful if we use some classifiers
        # over different subsets of data with some voting later on
        # (1-vs-therest?)

        if len(self.__poslabels)>1:
            self.__predictpos = self.__poslabels
        else:
            self.__predictpos = self.__poslabels[0]

        if len(self.__neglabels)>1:
            self.__predictneg = self.__neglabels
        else:
            self.__predictneg = self.__neglabels[0]


        def __str__(self):
            return "BinaryClassifier +1: %s -1: %s" % (
                `self.__poslabels`, `self.__neglabels`)


    def train(self, data):
        ids = data.idsbylabels(self.__poslabels + self.__neglabels)

        idlabels = zip(ids, [+1]*len(self.__poslabels) + [-1]*len(self.__neglabels))
        # XXX we have to sort ids since at the moment Dataset.selectSamples
        #     doesn't take care about order
        idlabels.sort()
        if __debug__:
            debug('CLF', "Selecting %d samples out of %d samples for binary " %
                  (len(ids), data.nsamples) +
                  " classification among labels %s/+1 and %s/-1" %
                  (self.__poslabels, self.__neglabels))
        # select the samples
        dataselected = data.selectSamples([ x[0] for x in idlabels ])
        # adjust the labels
        dataselected.labels = [ x[1] for x in idlabels ]
        # now we got a dataset with only 2 labels
        if __debug__:
            assert(dataselected.uniquelabels == [-1, 1])
        self.__clf.train(dataselected)


    def predict(self, data):
        """Predict the labels for a given `data`

        Predicts using binary classifier and spits out list (for each sample)
        where with either poslabels or neglabels as the "label" for the sample.
        If there was just a single label within pos or neg labels then it would
        return not a list but just that single label.
        """
        binary_predictions = ProxyClassifier.predict(self, data)
        self['values'] = binary_predictions
        predictions = map(lambda x: {-1: self.__predictneg,
                                     +1: self.__predictpos}[x], binary_predictions)
        self['predictions'] = predictions
        return predictions


class MulticlassClassifier(BoostedClassifier):
    """BoostedClassifier to perform multiclass using a set of `BinaryClassifier`s

    such as 1-vs-1 (ie in pairs like libsvm doesn) or 1-vs-all (which
    is yet to think about)
    """

    def __init__(self, clf, bclf=BoostedClassifier(),
                 bclf_type="1-vs-1", **kwargs):
        """Initialize the instance

        :Parameters:
          clf : Classifier
            classifier based on which multiple classifiers are created
            for multiclass
          boostedclf : BoostedClassifier
            classifier used to aggregate "pairClassifier"s
          bclf_type
            "1-vs-1" or "1-vs-all", determines the way to generate binary
            classifiers
          """
        Classifier.__init__(self, **kwargs)
        self.__clf = clf
        """Store sample instance of basic classifier"""
        self.__bclf = bclf
        """Store sample instance of boosted classifier to construct based on clf's"""

        # generate simpler classifiers
        #
        # create a mapping between original labels and labels in
        # simpler classifiers
        #
        # clfs= ...

        # XXX such logic below might go under train....
        if bclf_type == "1-vs-1":
            pass
        elif bclf_type == "1-vs-all":
            raise NotImplementedError
        else:
            raise ValueError, \
                  "Unknown type of classifier %s for " % bclf_type + \
                  "BoostedMulticlassClassifier"
        self.__bclf_type = bclf_type



    def train(self, data):
        """
        """
        # construct binary classifiers
        ulabels = data.uniquelabels

        if self.__bclf_type == "1-vs-1":
            # generate pairs and corresponding classifiers
            biclfs = []
            for i in xrange(len(ulabels)):
                for j in xrange(i+1, len(ulabels)):
                    clf = deepcopy(self.__clf)
                    biclfs.append(
                        BinaryClassifier(
                        copy.deepcopy(clf),
                        poslabels=[ulabels[i]], neglabels=[ulabels[j]]))
            if __debug__:
                debug("CLF", "Created %d binary classifiers for %d labels" %
                      (len(biclfs), len(ulabels)))

            self.__bclf.clfs = biclfs

        elif self.__bclf_type == "1-vs-all":
            raise NotImplementedError

        self.__bclf.train(data)


    def predict(self, data):
        """
        """
        # XXX might need to copy states off bclf
        return self.__bclf.predict(data)

    clfs = property(lambda x:x.__bclf.clfs, doc="Used classifiers")


class SplitClassifier(BoostedClassifier):
    """`BoostedClassifier` to work on splits of the data

    TODO: SplitClassifier and MulticlassClassifier have too much
          in common -- need to refactor: just need a splitter which would split
          dataset in pairs of class labels
    """

    def __init__(self, clf, bclf=CombinedClassifier(),
                 splitter=NoneSplitter(), **kwargs):
        """Initialize the instance

        :Parameters:
          clf : Classifier
            classifier based on which multiple classifiers are created
            for multiclass
          boostedclf : BoostedClassifier
            classifier used to aggregate "pairClassifier"s
          splitter : Splitter
            `Splitter` to use to split the dataset prior training
          """
        Classifier.__init__(self, **kwargs)
        self.__clf = clf
        """Store sample instance of basic classifier"""
        self.__bclf = bclf
        """Store sample instance of boosted classifier to construct based on clf's"""
        self.__splitter = splitter

        self.__clfs = None


    def train(self, data):
        """
        """
        # generate pairs and corresponding classifiers
        bclfs = []
        i = 0
        for split in self.__splitter(data):
            clf = deepcopy(self.__clf)
            clf.train(split)
            bclfs.append(clf)
            if __debug__:
                debug("CLF", "Created and trained classifier for split %d" % (i))
            i += 1

        self.__bclf.clfs = bclfs


    def predict(self, data):
        """
        """
        # XXX might need to copy states off bclf
        return self.__bclf.predict(data)

    clfs = property(lambda x:x.__bclf.clfs, doc="Used classifiers")


class MappedClassifier(ProxyClassifier):
    """`ProxyClassifier` which uses some mapper prior training/testing.

    `MaskMapper` can be used just a subset of features to
    train/classify.
    Having such classifier we can easily create a set of classifiers
    for BoostedClassifier, where each classifier operates on some set
    of features, e.g. set of best spheres from SearchLight, set of
    ROIs selected elsewhere. It would be different from simply
    applying whole mask over the dataset, since here initial decision
    is made by each classifier and then later on they vote for the
    final decision across the set of classifiers.
    """

    def __init__(self, clf, mapper, **kwargs):
        """Initialize the instance

        :Parameters:
          clf : Classifier
            classifier based on which mask classifiers is created
          mapper
            whatever `Mapper` comes handy
          """
        ProxyClassifier.__init__(self, clf, **kwargs)

        self.__mapper = mapper
        """mapper to help us our with prepping data to training/classification"""


    def train(self, data):
        """
        """
        ProxyClassifier.train(self, self.__mapper.forward(data.samples))


    def predict(self, data):
        """
        """
        return ProxyClassifier.predict(self, self.__mapper.forward(data.samples))


    mapper = property(lambda x:x.__mapper, doc="Used mapper")



class FeatureSelectionClassifier(ProxyClassifier):
    """`ProxyClassifier` which uses some `FeatureSelection` prior training.

    `FeatureSelection` is used first to select features for the classifier to use
    for prediction. Internally it would rely on MappedClassifier which would use
    created MaskMapper.
    TODO: think about removing overhead of retraining the same classifier if
          feature selection was carried out with the same classifier already
    """

    def __init__(self, clf, feature_selection, **kwargs):
        """Initialize the instance

        :Parameters:
          clf : Classifier
            classifier based on which mask classifiers is created
          feature_selection
            whatever `FeatureSelection` comes handy
          """
        ProxyClassifier.__init__(self, clf, **kwargs)

        self.__maskclf = None
        """Should become MappedClassifier later on.
        May be it better be a state variable but... TODO"""

        self.__feature_selection = feature_selection
        """FeatureSelection to select the features prior training"""


    def train(self, data):
        """
        """
        # temporarily enable selected_ids
        self.__feature_selection._enableStatesTemporarily(["selected_ids"])

        (wdata, tdata) = self.__feature_selection(data)
        if __debug__:
            debug("CLF", "FeatureSelectionClassifier: {%s} selected %d out of %d features" %
                  (self.__feature_selection, data.nfeatures, wdata.nfeatures))

        # create a mask to devise a mapper
        # TODO -- think about making selected_ids a MaskMapper
        mappermask = N.zeros(data.nfeatures)
        mappermask[self.__feature_selection["selected_ids"]] = 1
        mapper = MaskMapper(mappermask)

        self.__feature_selection._resetEnabledTemporarily()

        # create and assign `MappedClassifier`
        self.__maskclf = MappedClassifier(self.clf, mapper)
        # we could have called self.__clf.train(data), but it would
        # cause unnecessary masking
        self.__maskclf.clf.train(wdata)

        # for the ease of access
        self._copy_states_(self.__maskclf, deep=False)


    def predict(self, data):
        """
        """
        result = self.__maskclf.predict(data)
        # for the ease of access
        self._copy_states_(self.__maskclf, deep=False)
        return result


    maskclf = property(lambda x:x.__maskclf, doc="Used `MappedClassifier`")
    feature_selection = property(lambda x:x.__feature_selection, doc="Used `FeatureSelection`")

