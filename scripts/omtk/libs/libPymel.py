import logging

import pymel.core as pymel
from maya import OpenMaya


#
# A PyNodeChain is a special pymel-related object that act exactly like a standard array.
# However it allow us to have more bells and whistles.
#

def is_valid_PyNode(val):
    return (val and hasattr(val, 'exists') and val.exists()) if val else None


def distance_between_nodes(x, y):
    """
    Return the distance between two pynodes.
    """
    ax, ay, az = x.getTranslation(space="world")
    bx, b, bz = y.getTranslation(space="world")
    return ((ax - bx) ** 2 + (ay - b) ** 2 + (az - bz) ** 2) ** 0.5

def distance_between_vectors(a, b):
    """
    http://darkvertex.com/wp/2010/06/05/python-distance-between-2-vectors/
    """
    return (  (a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2  ) **0.5

def is_child_of(node, potential_parent):
    while node:
        if node == potential_parent:
            return True
        node = node.getParent()
    return False

class PyNodeChain(list):
    """A container for manipulating lists of hosts"""
    @property
    def start(self):
        return next(iter(self), None)

    @property
    def end(self):
        return self[-1] if len(self) > 0 else None

    @property
    def chain(self):
        return self

    def setParent(self, new_parent, **kwargs):
        for node in self:
            if node != new_parent and node.getParent() != new_parent:
                node.setParent(new_parent, **kwargs)

    # todo: convert to property?
    def length(self):
        length = 0
        for i in range(len(self) - 1):
            head = self[i]
            tail = self[i + 1]
            length += distance_between_nodes(head, tail)
        return length

    # get the first pynode that have the attr
    def __getattr__(self, key):
        logging.warning("Searching unknow attribute {key} in {self}", key=key, self=self)
        first_node = next((node for node in self.__dict__['_list'] if hasattr(node, key)), None)
        if first_node is not None:
            return getattr(first_node, key)
        raise AttributeError

    # set all the pynodes that have the attr
    def __setattr__(self, key, value):
        for node in self:
            try:
                setattr(node, key, value)
            except Exception, e:
                logging.error(str(e))


def duplicate_chain(chain):
    new_chain = pymel.duplicate(chain, renameChildren=True, parentOnly=True)
    return PyNodeChain(new_chain)


def get_num_parents(obj):
    num_parents = -1
    while obj is not None:
        obj = obj.getParent()
        num_parents += 1
    return num_parents


def get_chains_from_objs(objs):
    """
    Take an arbitraty collection of joints and sort them in hyerarchies represented by lists.
    """
    chains = []
    objs = sorted(objs, key=get_num_parents)
    for obj in objs:
        parent = obj.getParent()
        if parent not in objs:
            chains.append([obj])
        else:
            for chain in chains:
                if parent in chain:
                    chain.append(obj)
    return [PyNodeChain(chain) for chain in chains]

def get_parents(obj):
    parents = []
    while obj.getParent() is not None:
        parent = obj.getParent()
        parents.append(parent)
        obj = parent
    return parents

def get_tree_from_objs(objs, sort=False):
    """
    Sort all provided objects in a tree fashion.
    Each elements is a tuple of size 2, containing the object and it's children.
    Support missing objects between hierarchy.
    Note that to help recursive functions, the first entry is always None, representing the root node.
    ex:
    (None,
        [
            ('parent1',
                [
                    ('child1', [])
                ]
            )
        ]
    )
    """
    data_by_obj = {}
    ischild_by_obj = {}
    for obj in objs:
        data_by_obj[obj] = (obj, [])
        ischild_by_obj[obj] = False

    for obj in objs:
        parents = get_parents(obj)

        for parent in parents:
            if parent in objs:
                data_by_obj[parent][1].append(data_by_obj[obj])
                ischild_by_obj[obj] = True
                break

    if sort:
        for obj, data in data_by_obj.iteritems():
            data_by_obj[obj] = sorted(data)

    tree = []
    for obj, ischild in sorted(ischild_by_obj.iteritems()):
        if not ischild:
            tree.append(data_by_obj[obj])

    return (None, tree)


#
# ls() reimplementations
#

def ls(*args, **kwargs):
    return PyNodeChain(pymel.ls(*args, **kwargs))


# Wrapper for pymel.ls that return only objects without parents.
def ls_root(*args, **kwargs):
    return PyNodeChain(filter(lambda x: x.getParent() is None, iter(pymel.ls(*args, **kwargs))))


def ls_root_anms(**kwargs):
    return ls_root('anm*', type='transform', **kwargs)


def ls_root_geos(**kwargs):
    return ls_root('geo*', type='transform', **kwargs)


def ls_root_rigs(**kwargs):
    return ls_root('rig*', type='transform', **kwargs)


def ls_root_jnts(**kwargs):
    return ls_root('jnt*', type='transform', **kwargs)


#
# isinstance() reimplementation
#

# Class check for transform PyNodes
def isinstance_of_transform(obj, cls=pymel.nodetypes.Transform):
    return isinstance(obj, cls)


# Class check for shape PyNodes
def isinstance_of_shape(obj, cls=pymel.nodetypes.Shape):
    if isinstance(obj, pymel.nodetypes.Transform):
        return any((shape for shape in obj.getShapes() if isinstance(shape, cls)))

def create_zero_grp(obj):
    zero_grp = pymel.createNode('transform')
    new_name = obj.name() + '_' + 'zero_grp'
    zero_grp.rename(new_name)

    # Note: Removed for performance
    zero_grp.setMatrix(obj.getMatrix(worldSpace=True))

    parent = obj.getParent()
    if parent:
        zero_grp.setParent(parent)

    obj.setParent(zero_grp)

    return zero_grp

def zero_out_objs(objs):
    for o in objs:
        create_zero_grp(o)

#
# pymel.datatypes extensions.
#

class Segment(object):
    """
    In Maya there's no class to represent a segment.
    This is the pymel.datatypes.Segment I've always wanted.
    """
    def __init__(self, pos_s, pos_e):
        self.pos_s = pos_s
        self.pos_e = pos_e

        #self.pos_s = numpy.array(pos_s.x, pos_s.y, pos_s.z)
        #self.pos_e = numpy.array(pos_e.x, pos_e.y, pos_e.z)

    def closest_point(self, p):
        """
        http://stackoverflow.com/questions/3120357/get-closest-point-to-a-line
        """
        a = self.pos_s
        b = self.pos_e
        a_to_p = p - a
        a_to_b = b - a
        ab_length = a_to_b.length()
        ap_length = a_to_p.length()
        a_to_p_norm = a_to_p.normal()
        a_to_b_norm = a_to_b.normal()
        atp_dot_atb = a_to_p_norm * (a_to_b_norm)  # dot product
        dist_norm = atp_dot_atb * ap_length / ab_length
        return pymel.datatypes.Vector(
            a.x + a_to_b.x * dist_norm,
            a.y + a_to_b.y * dist_norm,
            a.z + a_to_b.z * dist_norm
        )

    def closest_point_normalized_distance(self, p):
        """
        Same things as .closest_point but only return the distance relative from the length of a to b.
        Available for optimisation purpose.
        """
        a = self.pos_s
        b = self.pos_e
        a_to_p = p - a
        a_to_b = b - a
        ab_length = a_to_b.length()
        ap_length = a_to_p.length()
        a_to_p_norm = a_to_p.normal()
        a_to_b_norm = a_to_b.normal()
        atp_dot_atb = a_to_p_norm * a_to_b_norm
        return (atp_dot_atb * ap_length / ab_length) if ab_length > 0.001  else 0.0


class SegmentCollection(object):
    def __init__(self, segments=None):
        if segments is None:
            segments = []
        self.segments = segments

        self.knots = [segment.pos_s for segment in self.segments]
        self.knots.append(self.segments[-1].pos_e)

    def closest_segment(self, pos):
        bound_min = -0.999999999999  # Damn float imprecision
        bound_max = 1.0000000000001  # Damn float imprecision
        num_segments = len(self.segments)
        for i, segment in enumerate(self.segments):
            distance_normalized = segment.closest_point_normalized_distance(pos)
            if distance_normalized >= bound_min and distance_normalized <= bound_max:
                return segment, distance_normalized
            elif i == 0 and distance_normalized < bound_min:  # Handle out-of-bound
                return segment, 0.0
            elif i == (num_segments-1) and distance_normalized > bound_max:  # Handle out-of-bound
                return segment, 1.0
        raise Exception("Can't resolve segment for {0}".format(pos))

    def closest_segment_index(self, pos):
        closest_segment, ratio = self.closest_segment(pos)
        index = self.segments.index(closest_segment)
        return index, ratio

    def get_knot_weights(self, dropoff=1.0, normalize=True):
        num_knots = len(self.knots)
        knots_weights = []
        for i, knot in enumerate(self.knots):
            if i == 0:
                weights = [0] * num_knots
                weights[0] = 1.0
            elif i == (num_knots-1):
                weights = [0] * num_knots
                weights[-1] = 1.0
            else:
                weights = []
                total_weight = 0.0
                for j in range(num_knots):
                    distance = abs(j-i)
                    weight = max(0, 1.0-(distance/dropoff))
                    total_weight += weight
                    weights.append(weight)
                weights = [weight / total_weight for weight in weights]
            knots_weights.append(weights)
        return knots_weights

    '''
    def get_weights(self, pos, dropoff=1.0, normalize=True):
        # Compute the 'SegmentCollection' relative ratio and return the weight for each knots.
        closest_segment, relative_ratio = self.closest_segment(pos)


        index = self.segments.index(closest_segment)
        absolute_ratio = relative_ratio + index

        weights = []
        total_weights = 0.0
        for segment_ratio in range(len(self.knots)):
            #segment_ratio += 0.5 # center of the joint
            #print segment_ratio, absolute_ratio
            distance = abs(segment_ratio - absolute_ratio)
            weight = max(0, 1.0-(distance/dropoff))

            # Apply cubic interpolation for greater results.
            #weight = interp_cubic(weight)

            total_weights += weight
            weights.append(weight)

        if normalize:
            weights = [weight / total_weights for weight in weights]

        return weights
    '''

    @classmethod
    def from_transforms(cls, objs):
        segments = []
        num_objs = len(objs)
        for i in range(num_objs-1):
            obj_s = objs[i]
            obj_e = objs[i+1]
            mfn_transform_s = obj_s.__apimfn__()
            mfn_transform_e = obj_e.__apimfn__()
            pos_s = OpenMaya.MVector(mfn_transform_s.getTranslation(OpenMaya.MSpace.kWorld))
            pos_e = OpenMaya.MVector(mfn_transform_e.getTranslation(OpenMaya.MSpace.kWorld))
            segment = Segment(pos_s, pos_e)
            segments.append(segment)
        return cls(segments)