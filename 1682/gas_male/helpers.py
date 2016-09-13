from gpkit import ConstraintSet, Variable

class SummingConstraintSet(ConstraintSet):
    def __init__(self, lhs, varname, models=[], variables=[], **kwargs):
        summedvars = set([v.key for v in variables])
        alreadysummed = set()
        for model in models:
            mvars = model[varname]
            if not hasattr(mvars, "__len__"):
                mvars = [mvars]
            # next line makes the recursion stop at depth one
            # for safety to avoid double counting
            mvars = [v for v in mvars if v.key.models[0] == model.name]
            assert len(mvars) == 1
            summedvars = summedvars.union([v.key for v in mvars])
            for constraint in model.flat():
                if hasattr(constraint, "summedvars"):
                    alreadysummed = alreadysummed.union(constraint.summedvars)
        summedvars = summedvars.difference(alreadysummed)
        ConstraintSet.__init__(self, [lhs >= sum(Variable(**vk.descr)
                                                 for vk in summedvars)],
                               **kwargs)
    @property
    def summedvars(self):
        return set(self[0].p_lt.varkeys)
