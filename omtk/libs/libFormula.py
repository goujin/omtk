"""
A module that convert mathematical formulas to utility nodes.

A lightweight programming language that parse math formulas to utility nodes.
This is done by defining lots of new operators.
Currently, supported operators are: add (+), substract (-), multiply (*), divide (/), pow (^), distance (~), equal (=), not_equal (!=), bigger (>), bigger_or_equal (>=), smaller (<) and smaller_or_equal (<=).

ex01 :creating a bell-curve type squash
import math
from omtk.rigging import libFormula
loc, locs = pymel.polysphere()
stretch = loc.sy
squash = libFormula.parse("1 / (e^(x^2))", e=math.e, x=stretch)
pymel.connectAttr(squash, loc.sx)
pymel.connectAttr(squash, loc.sz)

ex02:
    from omtk.rigging import libFormula
    grp = pymel.createNode('transform')
    libFormula.parse('(tx*rx)+(ty*ry)+(tz*rz)', tx=loc.tx, ty=loc.ty, tz=loc.tz, rx=loc.rx, ry=loc.ry, rz=loc.rz)
"""

# TODO: Implement operators priotity

import re, math, collections
from omtk.libs import libRigging
import pymel.core as pymel
import logging as log

class operator(object):
    @staticmethod
    def can_optimise(*args):
        for arg in args:
            if isinstance(arg, pymel.Attribute):
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
        log.debug('[add:execute] {0} + {1}'.format(arg1, arg2))
        return arg1 + arg2
    @staticmethod
    def create(arg1, arg2):
        log.debug('[add:create] {0} + {1}'.format(arg1, arg2))
        return libRigging.CreateUtilityNode('plusMinusAverage', operation=1, input1D=[arg1, arg2]).output1D

class substraction(operator):
    @staticmethod
    def execute(arg1, arg2):
        log.debug('[substract:execute] {0} - {1}'.format(arg1, arg2))
        return arg1 - arg2
    @staticmethod
    def create(arg1, arg2):
        log.debug('[substract:create] {0} - {1}'.format(arg1, arg2))
        return libRigging.CreateUtilityNode('plusMinusAverage', operation=2, input1D=[arg1, arg2]).output1D

class multiplication(operator):
    @staticmethod
    def execute(arg1, arg2):
        log.debug('[multiply:execute] {0} * {1}'.format(arg1, arg2))
        return arg1 * arg2;
    @staticmethod
    def create(arg1, arg2):
        log.debug('[multiply:create] {0} * {1}'.format(arg1, arg2))
        return libRigging.CreateUtilityNode('multiplyDivide', operation=1, input1X=arg1, input2X=arg2).outputX

class division(operator):
    @staticmethod
    def execute(arg1, arg2):
        log.debug('[divide:execute] {0} * {1}'.format(arg1, arg2))
        return arg1 / arg2;
    @staticmethod
    def create(arg1, arg2):
        log.debug('[divide:create] {0} * {1}'.format(arg1, arg2))
        u = libRigging.CreateUtilityNode('multiplyDivide', input1X=arg1, input2X=arg2)
        u.operation.set(2) # HACK: Prevent division by zero by changing the operator at the last second.
        return u.outputX

class pow(operator):
    @staticmethod
    def execute(arg1, arg2):
        log.debug('[pow:execute] {0} * {1}'.format(arg1, arg2))
        return math.pow(arg1, arg2);
    @staticmethod
    def create(arg1, arg2):
        log.debug('[pow:create] {0} * {1}'.format(arg1, arg2))
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
        else:
            kwargs['point1'] = arg1

        if isinstance(arg2, pymel.datatypes.Matrix) or (isinstance(arg2, pymel.Attribute) or arg2.type() == 'matrix'):
            kwargs['inMatrix2'] = arg2
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

_operators = {
    '+'  : addition,
    '-'  : substraction,
    '*'  : multiplication,
    '/'  : division,
    '^'  : pow,
    '~'  : distance,
    '='  : equal,
    '!=' : not_equal,
    '>'  : bigger,
    '>=' : bigger_or_equal,
    '<'  : smaller,
    '<=' : smaller_or_equal
}
'''
1   ()   []   ->   .   ::	Grouping, scope, array/member access
2	 !   ~   -   +   *   &   sizeof   type cast ++x   --x  	(most) unary operations, sizeof and type casts
3	*   /   % MOD	Multiplication, division, modulo
4	+   -	Addition and subtraction
5	<<   >>	Bitwise shift left and right
6	<   <=   >   >=	Comparisons: less-than, ...
7	==   !=	Comparisons: equal and not equal
8	&	Bitwise AND
9	^	Bitwise exclusive OR
10	|	Bitwise inclusive (normal) OR
11	&&	Logical AND
12	||	Logical OR
13	 ?:   =   +=   -=   *=   /=   %=   &=   |=   ^=   <<=   >>=	Conditional expression (ternary) and assignment operators
14	,	Comma operator
'''
__operators = [
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


    ('*', multiplication),
    ('/', division),
    ('+', addition),
    ('-', substraction)
]



_varDelimiters = ['0','1','2','3','4','5','6','7','8','9','(',')', '.'] + _operators.keys()
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

def _optimise_removePrefixes(inn):
    global _operators
    fnIsOperator = lambda x: isinstance(x, collections.Hashable) and x in _operators
    num_args = len(inn)

    out = []

    first = inn[0]
    if isinstance(first, list):
        first = _optimise_removePrefixes(first)
    out.append(first)

    # todo: handle cases where the formula start with '-'
    i = 1
    while i < num_args-1:
        perArg = inn[i]
        posArg = inn[i+1]
        if fnIsOperator(perArg) and posArg == '-':
            out.append(perArg)

            next_arg = inn[i+2]

            if isinstance(next_arg, basestring) and next_arg.isdigit():
                perArg = -1 * float(next_arg) # todo: prevent int to float conversion
            else:
                perArg = [-1, '*', next_arg]

            i += 2 # skip the next iteration
            #num_args -= 1
        elif isinstance(perArg, list):
            perArg = _optimise_removePrefixes(perArg)
        out.append(perArg)

        i += 1

    last = inn[-1]
    if isinstance(last, list):
        last = _optimise_removePrefixes(last)
    out.append(last)

    return out

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

# This minimise the weight of the formula, we make sure we're not applying operator on constants.
# ex: "2 + 3 * a"   ->   "5 * a"
# ex: "a ^ (2 + 3)" ->   "a ^ 5"
def _optimise_cleanConstants(args):
    fnRecursive_call = lambda x: _optimise_cleanConstants(x) if isinstance(x, list) else x

    args[0] = fnRecursive_call(args[0])
    i=1
    imax = len(args)
    while i < imax-1:
        preArg = args[i-1]
        perArg = args[i]
        posArg = fnRecursive_call(args[i+1])

        # Ensure we're working with operators
        if not perArg in _operators:
            raise IOError("Expected operator in formula, got {0}. {1}".format(perArg, args))

        cls = _operators.get(perArg)

        if cls.can_optimise(preArg, posArg):
            result = cls.execute(preArg, posArg)

            # Inject result in args
            args[i-1] = result
            del args[i]
            del args[i]
            imax -= 2
        else:
            i+=2

    return args if len(args) > 1 else args[0] # never return a single array

def _create_nodes(args):
    log.debug('[create_nodes] {0}'.format(args))
    num_args = len(args)
    if num_args < 3:
        raise Exception("A minimum of 3 arguments are necessary! Got: {0}".format(args))

    for i in range(1, num_args-1, 2):

        perArg = args[i]
        if not isinstance(perArg, basestring) or not perArg in _operators:
            raise Exception("Unexpected operator: {0}".format(perArg))

        preArg = args[i-1]
        if isinstance(preArg, list):
            preArg = _create_nodes(preArg)
        else:
            preArg = basic_cast(preArg)

        posArg = args[i+1]
        if isinstance(posArg, list):
            posArg = _create_nodes(posArg)
        else:
            preArg = basic_cast(preArg)

        cls = _operators[perArg]

        fn = cls.execute if cls.can_optimise(preArg, posArg) else cls.create
        log.debug("Proceeding with formula {0} {1} {2}".format(preArg, perArg, posArg))
        return_val = args[i+1] = fn(preArg, posArg)

    return return_val

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
    for op in _operators.keys(): content |= op # defined operators
    nestedExpr = pyparsing.nestedExpr( opener='(', closer=')', content=content)
    res = nestedExpr.parseString('({0})'.format(str)) # wrap all string in parenthesis, or it won't work
    args = res.asList()[0]

    num_args = len(args)
    if num_args == 0:
        raise IOError("Expected at least 1 argument!")

    # Replace variables by their real value
    # We're only iterating on every operators (ex: range(1,4,2)
    args = optimise_replaceVariables(args)
    log.debug("\tWithout variables ({0} calls): {1}".format(rlen(args), args))
    if not isinstance(args, list): return args

    # Hack: Convert '-' prefix before a variable to a multiply operator
    # ex: x*-3 -> x * (3 * -1)
    args = _optimise_removePrefixes(args)
    log.debug("\tWithout '-' prefix ({0} calls): {1}".format(rlen(args), args))
    if not isinstance(args, list): return args

    # Calculate out the constants
    args = _optimise_cleanConstants(args)
    log.debug("\tWithout constants: {0}".format(args))
    if not isinstance(args, list): return args

    # Create nodes
    #log.debug("Creating nodes...")
    #return _create_nodes(args)
    #log.debug("ALL DONE!")

    return None

def parseToVar(name, formula, vars):
    attr = parse(formula, **vars)
    attr.node().rename(name)
    vars[name] = attr




'''
ex: basic_squash
parse("1 / stretch", stretch=xstretch)

ex: complex squash (f=[0.0-1.0])
parse("1 / stretch ^ (1 / (e^(x^2)))", e=math.e, x=f, stretch=stretch)

'''