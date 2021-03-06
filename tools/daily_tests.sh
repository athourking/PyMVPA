#!/bin/bash
# emacs: -*- mode: shell-script; indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=sh sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#                 Helper to run all the tests daily at night
#

set -e

# Not yet can do fine scale unittest separation since maint/0.4, nor
# master have it that way... leaving it for future.
#MAKE_TESTS="unittest unittest-optimization unittest-debug unittest-badexternals
#MAKE_TESTS="unittests testmanual testsuite testapiref testdatadb testsphinx testexamples testcfg"

# Unittests to run in all branches
TESTS_COMMON="unittests testmanual testsuite testsphinx testexamples testcfg"

# Associative array with tests lists per branch
declare -A TESTS_BRANCHES
# stable branches
for b in maint/0.4; do
    #have no datadb and still use epydoc
    TESTS_BRANCHES["$b"]="$TESTS_COMMON testapiref"
done
# development branches
for b in master yoh/master; do
    TESTS_BRANCHES["$b"]="$TESTS_COMMON testdatadb testourcfg testdocstrings"
done
# all known tests
TESTS_ALL=`echo "${TESTS_BRANCHES[*]}" | tr ' ' '\n' | sort | uniq`

# what branches to test
BRANCHES="${!TESTS_BRANCHES[*]}"
# where to send reports
EMAILS='yoh@onerussian.com,michael.hanke@gmail.com'

precmd=
#precmd="echo  C: "
# XXX
repo="git://git.debian.org/git/pkg-exppsy/pymvpa.git"

ds=`date +"20%y%m%d_%H%M%S"`
topdir=$HOME/proj/pymvpa
datadbdir=$topdir/pymvpa/datadb
logdir="$topdir/logs/daily/pymvpa_tests-$ds"
tmpfile="$logdir/tmp.log"
logfile="$logdir/all.log"

# Remove
trap "rm -fr $logdir/pymvpa $logdir/tmp.log;" EXIT

mkdir -p "$logdir"

indent() {
    sed -e 's/^/  /g'
}

do_checkout() {
    $precmd git clean -df | indent
    $precmd git reset --hard
    #if [ ! $branch = 'master' ]; then
    $precmd git checkout -b $branch origin/$branch || :
    #fi
    $precmd git checkout $branch
    # Clean up again since we might have some directories
    $precmd git clean -df | indent
    #provide datadb
    [ -e "datadb" ] || $precmd ln -s "$datadbdir" .
}

do_build() {
    $precmd make clean
    $precmd make
}

do_clean() {
    # verify that cleaning works as desired
    $precmd make clean
    $precmd git clean -n | grep -q . \
        && { git clean -n; return 1; } \
        || return 0
}

for c in $TESTS_ALL; do
    eval "do_$c() { $precmd make $c; }"
done

# need to override some so they are ran with -k
# so we see all that fail
for c in testexamples unittests; do
    eval "do_$c() { $precmd make -k $c; }"
done

# Counters
failed=0
succeeded=0

# skip the tests we can't fully trust to sleep well
export MVPA_TESTS_LABILE=no
# Lets use backend allowing to draw without DISPLAY
export MVPA_MATPLOTLIB_BACKEND=agg

# need to be a function to share global failed/succeded
sweep()
{
    cd $logdir

    echo "I:" $(date)

    # checkout the repository
    echo "I: Cloning repository"
    $precmd git clone -q $repo 2>&1 | indent
    $precmd cd pymvpa
    # no need to check here since checkout would fail below otherwise

    #
    # Sweep through the branches and actionsto test
    #
    branches_with_problems=
    for branch in $BRANCHES; do
        branch_has_problems=
        echo
        echo "I: ---------------{ Branch $branch }--------------"
        for action in checkout build ${TESTS_BRANCHES["$branch"]} clean; do
            echo -n "I: $action "
            cmd="do_$action"
            if $cmd >| $tmpfile 2>&1 ; then
                echo " ok"
                succeeded=$(($succeeded+1))
            else
                branch_has_problems+=" $action"
                failed=$(($failed+1))
                echo " ! FAILED ! Output was:"
                cat $tmpfile | indent
            fi
            # provide information in the log about what was current position
            # in the branch
            [ "$action" = "checkout" ] && echo "I: current position $(git describe)"
        done
        if [ "x$branch_has_problems" != x ]; then
            branches_with_problems+="\n  $branch: $branch_has_problems"
            echo " D: Reporting WTF due to errors:"
            $precmd python -c 'import mvpa; print mvpa.wtf()'
        fi
    done
    echo "I: Succeeded $succeeded actions, failed $failed actions."
    if [ "x$branches_with_problems" != x ]; then
        echo -e "I: Branches which experienced problems: $branches_with_problems"
    fi

    echo
    echo "I:" $(date)
    echo "I: Exiting. Logfile $logfile"
}

sweep >| $logfile 2>&1

# Email only if any test has failed
#[ ! $failed = 0 ] && \
# Email always since it is better to see that indeed everything is smooth
# and to confirm that it is tested daily
cat $logfile | mail -s "PyMVPA: daily testing: +$succeeded/-$failed" $EMAILS
