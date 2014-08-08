import re, math, collections
from omtk.libs import libRigging
from maya import cmds
import pymel.core as pymel
import logging as log

class operator(object):
    @staticmethod
    def can_optimise(*args):
        for arg in args:
            if not isinstance(arg, (int, float, long)):
                return False
        return True
    @staticmethod
    def execute(*args, **kwargs):
        raise NotImplementedError
    @staticmethod
    def create(*args, **kwargs):
        raise NotImplementedError

class addition(operator):
    @staticmethod
    def execute(arg1, arg2):
        return arg1 + arg2
    @staticmethod
    def create(arg1, arg2):
        return libRigging.CreateUtilityNode('plusMinusAverage', operation=1, input1D=[arg1, arg2]).output1D

class substraction(operator):
    @staticmethod
    def execute(arg1, arg2):
        return arg1 - arg2
    @staticmethod
    def create(arg1, arg2):
        return libRigging.CreateUtilityNode('plusMinusAverage', operation=2, input1D=[arg1, arg2]).output1D

class multiplication(operator):
    @staticmethod
    def execute(arg1, arg2):
        return arg1 * arg2;
    @staticmethod
    def create(arg1, arg2):
        return libRigging.CreateUtilityNode('multiplyDivide', operation=1, input1X=arg1, input2X=arg2).outputX

class division(operator):
    @staticmethod
    def execute(arg1, arg2):
        return arg1 / arg2;
    @staticmethod
    def create(arg1, arg2):
        u = libRigging.CreateUtilityNode('multiplyDivide', input1X=arg1, input2X=arg2)
        u.operation.set(2) # HACK: Prevent division by zero by changing the operator at the last second.
        return u.outputX

class pow(operator):
    @staticmethod
    def execute(arg1, arg2):
        try:
            return math.pow(arg1, arg2)
        except Exception, e:
            log.error("Can't execute {0} ^ {1}: {2}".format(arg1, arg2, e)),

        return math.pow(arg1, arg2)
    @staticmethod
    def create(arg1, arg2):
        return libRigging.CreateUtilityNode('multiplyDivide', operation=3, input1X=arg1, input2X=arg2).outputX

class distance(operator):
    @staticmethod
    def execute(arg1, arg2):
        log.debug('[distance:execute] {0} * {1}'.format(arg1, arg2))

        # todo: check for matrix

        return arg1 * arg2;
    @staticmethod
    def create(arg1, arg2):
        log.debug('[distance:create] {0} * {1}'.format(arg1, arg2))
        # todo: check if we want to use inMatrix1 & inMatrix2 or point1 & point2
        kwargs = {}

        if isinstance(arg1, pymel.datatypes.Matrix) or (isinstance(arg1, pymel.Attribute) or arg1.type() == 'matrix'):
            kwargs['inMatrix1'] = arg1
        elif isinstance(arg1, pymel.nodetypes.Transform):
            kwargs['inMatrix1'] = arg1.worldMatrix
        else:
            kwargs['point1'] = arg1

        if isinstance(arg2, pymel.datatypes.Matrix) or (isinstance(arg2, pymel.Attribute) or arg2.type() == 'matrix'):
            kwargs['inMatrix2'] = arg2
        elif isinstance(arg2, pymel.nodetypes.Transform):
            kwargs['inMatrix2'] = arg2.worldMatrix
        else:
            kwargs['point2'] = arg2

        return libRigging.CreateUtilityNode('distanceBetween', **kwargs).distance

class equal(operator):
    @staticmethod
    def execute(arg1, arg2):
        log.execute('[equal:execute] {0} * {1}'.format(arg1, arg2))
        return arg1 == arg2;
    @staticmethod
    def create(arg1, arg2):
        log.debug('[equal:create] {0} * {1}'.format(arg1, arg2))
        return libRigging.CreateUtilityNode('condition', operation=0, colorIfTrue=1.0, colorIfFalse=0.0).outColorR

class not_equal(operator):
    @staticmethod
    def execute(arg1, arg2):
        return arg1 != arg2;
    @staticmethod
    def create(*args, **kwargs):
        return equal(operation=1).outColorR

class bigger(operator):
    @staticmethod
    def execute(arg1, arg2):
        return arg1 > arg2
    @staticmethod
    def create(*args, **kwargs):
        return equal(operation=2, *args, **kwargs).outColorR

class bigger_or_equal(operator):
    @staticmethod
    def execute(arg1, arg2):
        return arg1 >= arg2;
    @staticmethod
    def create(*args, **kwargs):
        return equal(operation=3, *args, **kwargs).outColorR

class smaller(operator):
    @staticmethod
    def execute(arg1, arg2):
        return arg1 < arg2;
    @staticmethod
    def create(*args, **kwargs):
        return equal(operation=4, *args, **kwargs).outColorR

class smaller_or_equal(operator):
    @staticmethod
    def execute(arg1, arg2):
        return arg1 <= arg2;
    @staticmethod
    def create(*args, **kwargs):
        return equal(operation=5, *args, **kwargs).outColorR

# src: http://www.mathcentre.ac.uk/resources/workbooks/mathcentre/rules.pdf
_sorted_operators = [
    {
        '~'  : distance,
    },
    {
        '^'  : pow,
    },
    {
        '*'  : multiplication,
        '/'  : division,
    },
    {
        '+'  : addition,
        '-'  : substraction,
    },
    {
        '='  : equal,
        '!=' : not_equal,
        '>'  : bigger,
        '>=' : bigger_or_equal,
        '<'  : smaller,
        '<=' : smaller_or_equal
    }
]

_all_operators = {}
for operators in _sorted_operators: _all_operators.update(operators)
_varDelimiters = ['0','1','2','3','4','5','6','7','8','9','(',')', '.'] + _all_operators.keys()
_regex_splitVariables = '|'.join(re.escape(str) for str in _varDelimiters)

_variables = {}

def basic_cast(str):
    # try float conversion
    try:
        return float(str)
    except: pass

    # try int conversion
    try:
        return int(str)
    except: pass

    return str

def convert_basic_value(str):
    # handle parenthesis
    if isinstance(str, list):
        return _create_nodes(*str)

    return basic_cast(str)

def rlen(L):
    i = 0
    for l in L:
        if isinstance(l, list):
            i += rlen(l)
        else:
            i += 1
    return i

def optimise_replaceVariables(args):
    global _variables
    fnIsVariable = lambda x: isinstance(x, basestring) and x in _variables

    out = []
    for arg in args:
        if fnIsVariable(arg):
            arg = basic_cast(_variables[arg])
        elif isinstance(arg, list):
            arg = optimise_replaceVariables(arg)
        else:
            arg = basic_cast(arg)
        out.append(arg)
    return out

def _optimise_formula_remove_prefix(args):
    import logging; log = logging.getLogger(__name__)

    print '_optimise_formula_remove_prefix', args
    if len(args) < 2:
        raise Exception("A minimum of 2 arguments are necessary! Got: {0}".format(args))
    fnRecursive_call = lambda x: _optimise_formula_remove_prefix(x) if isinstance(x, list) else x
    #args[0] = fnRecursive_call(args[0])
    pos=0
    imax=len(args)
    print len(args)
    while pos < imax-1:
        log.debug('| current position: {0}'.format(pos))
        log.debug('| current operator: {0}'.format(args[0]))
        log.debug('| memory: {0} {1} {2}'.format((args[pos-1] if pos != 0 else None), args[pos], args[pos+1]))
        log.debug('| memory (all): {0}'.format(args))
        preArg = args[pos-1] if pos > 0 else None
        args[pos]   = perArg = fnRecursive_call(args[pos])
        args[pos+1] = posArg = fnRecursive_call(args[pos+1])
        if perArg == '-':
            if preArg is None or preArg in _all_operators: # If the formula start with '-' or '-' is prefixed by an operator
                del args[pos]

                if isinstance(posArg, (int, float, long)):
                    args[pos] = -1 * posArg
                else:
                    args[pos] = [-1, '*', posArg]
                imax=len(args)
            pos += 1
        else:
            pos += 1
    log.debug('exiting... {0}'.format(args))
    return args

# Generic method to optimize a formula via a suite of operators
# For now only 'sandwitched' operators are supported
def _optimise_formula_with_operators(args, fnName, fnFilterName=None):
    if len(args) < 3:
        raise Exception("A minimum of 3 arguments are necessary! Got: {0}".format(args))
    fnRecursive_call = lambda x: _optimise_formula_with_operators(x, fnName, fnFilterName=fnFilterName) if isinstance(x, list) else x
    for operators in _sorted_operators:
        args[0] = fnRecursive_call(args[0])
        i=1
        imax = len(args)
        while i < imax-1:
            preArg = args[i-1]
            perArg = args[i]
            posArg = args[i+1] = fnRecursive_call(args[i+1])
            # Ensure we're working with operators
            if not isinstance(perArg, basestring):
                raise IOError("Invalid operator '{0}', expected a string".format(perArg))
            cls = operators.get(perArg, None)
            if cls and (not fnFilterName or getattr(cls, fnFilterName)(preArg, posArg)):
                fn = getattr(cls, fnName)
                result = fn(preArg, posArg)
                # Inject result in args
                args[i-1] = result
                del args[i]
                del args[i]
                imax -= 2
            else:
                i+=2
    return args if len(args) > 1 else args[0] # never return a single array

# This minimise the weight of the formula, we make sure we're not applying operator on constants.
# ex: "2 + 3 * a"   ->   "5 * a"
# ex: "a ^ (2 + 3)" ->   "a ^ 5"
def _optimise_cleanConstants(args):
    return _optimise_formula_with_operators(args, 'execute', 'can_optimise')

def _create_nodes(args):
    return _optimise_formula_with_operators(args, 'create')

def parse(str, **inkwargs):
    log.debug("--------------------")
    log.debug("PARSING: {0}".format(str))
    # step 1: identify variables
    vars = (var.strip() for var in re.split(_regex_splitVariables, str))
    vars = filter(lambda x: x, vars)
    #print 'found vars:', vars

    # hack: add mathematical constants in variables
    kwargs = {
        'e':math.e,
        'pi':math.pi
    }
    kwargs.update(inkwargs)

    # step 2: ensure all variables are defined
    # todo: validate vars types
    global _variables
    _variables = {}
    for var in vars:
        if not var in kwargs:
            raise KeyError("Variable '{0}' is not defined".format(var))
        _variables[var] = kwargs[var]
        log.debug('\t{0} = {1}'.format(var, kwargs[var]))
    #print 'defined variables are:', dicVariables

    # Convert parenthesis and operators to nested string lists
    # src: http://stackoverflow.com/questions/5454322/python-how-to-match-nested-parentheses-with-regex
    from omtk.deps import pyparsing # make sure you have this installed
    content = pyparsing.Word(pyparsing.alphanums + '.')
    for op in _all_operators.keys(): content |= op # defined operators
    nestedExpr = pyparsing.nestedExpr( opener='(', closer=')', content=content)
    res = nestedExpr.parseString('({0})'.format(str)) # wrap all string in parenthesis, or it won't work
    args = res.asList()[0]

    num_args = len(args)
    if num_args == 0:
        raise IOError("Expected at least 1 argument!")



    # Replace variables by their real value
    # We're only iterating on every operators (ex: range(1,4,2)
    args = optimise_replaceVariables(args)
    if not isinstance(args, list): return args
    log.debug("\tWithout variables ({0} calls) : {1}".format(rlen(args), args))

    # Hack: Convert '-' prefix before a variable to a multiply operator
    # ex: x*-3 -> x * (3 * -1)
    args = _optimise_formula_remove_prefix(args)
    if not isinstance(args, list): return args
    log.debug("\tWithout '-' prefix ({0} calls): {1}".format(rlen(args), args))

    # Calculate out the constants
    args = _optimise_cleanConstants(args)
    if not isinstance(args, list): return args
    log.debug("\tWithout constants ({0} calls) : {1}".format(rlen(args),args))

    # Create nodes
    #log.debug("Creating nodes...")
    return _create_nodes(args)
    #log.debug("ALL DONE!")

    return None

def parseToVar(name, formula, vars):
    attr = parse(formula, **vars)
    attr.node().rename(name)
    vars[name] = attr

def _test_squash():
    # ex:creating a bell-curve type squash
    cmds.file(new=True, f=True)
    transform, shape = pymel.sphere()
    stretch = transform.sy
    squash = parse("1 / (e^(x^2))", x=stretch)
    pymel.connectAttr(squash, transform.sx)
    pymel.connectAttr(squash, transform.sz)
    return True

def _test_squash2(step_size=2):
    cmds.file(new=True, f=True)
    root = pymel.createNode('transform', name='root')
    pymel.addAttr(root, longName='amount', defaultValue=1.0, k=True)
    pymel.addAttr(root, longName='shape', defaultValue=math.e, k=True)
    pymel.addAttr(root, longName='offset', defaultValue=0.0, k=True)
    attAmount = root.attr('amount')
    attShape = root.attr('shape')
    attOffset = root.attr('offset')
    attInput = parse("amount^2", amount=attAmount)
    for i in range(0, 100, step_size):
        cyl, make = pymel.cylinder()
        cyl.rz.set(90)
        cyl.ty.set(i+step_size/2)
        make.heightRatio.set(step_size)
        attSquash = parse("amount^(1/(shape^((x+offset)^2)))", x=(i-50)/50.0, amount=attInput, shape=attShape, offset=attOffset)
        pymel.connectAttr(attSquash, cyl.sy)
        pymel.connectAttr(attSquash, cyl.sz)
    return True

def test():
    assert(parse("2+2") == 4)
    assert(parse("a+3*(6+(3*b))", a=4, b=7) == 85)
    assert(parse("-2^1.0*-1.0+3.3")) # '-' fix
    assert(parse("-2*(1.0-(3^(3*-1.0)))")) # '-' prefix

    assert(_test_squash())
    assert(_test_squash2())
