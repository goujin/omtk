from omtk.modules import rigFaceAvarGrps
from omtk.modules import rigFaceAvar
from omtk.libs import libRigging
import pymel.core as pymel


class CtrlNose(rigFaceAvar.CtrlFaceMicro):
    pass


class FaceNose(rigFaceAvarGrps.AvarGrpOnSurface):
    """
    The Nose is composed of two zones. The uppernose and the lower nose.
    The uppernose is user specifically for it's yaw and pitch rotation.
    Everything under is considered a nostril.

    Note that this was done reallllly quickly and cleanup may be needed in the future.
    """
    #_DEFORMATION_ORDER = 'post'
    #_CLS_AVAR = AvarJaw
    SHOW_IN_UI = True
    IS_SIDE_SPECIFIC = False
    _CLS_CTRL = CtrlNose

    def __init__(self, *args, **kwargs):
        super(FaceNose, self).__init__(*args, **kwargs)
        self.avar_main = None

    @property
    def inf_nose_upp(self):
        # TODO: FIX ME
        return pymel.PyNode('NoseBend_Jnt')

    @property
    def inf_nose_low(self):
        # TODO: FIX ME
        return pymel.PyNode('Nose_Jnt')

    @property
    def influences_snear(self):
        return [jnt for jnt in self.jnts if 'snear' in jnt.name().lower()]

    @property
    def avar_nose_upp(self):
        for avar in self.avars:
            if avar.jnt == self.inf_nose_upp:
                return avar

    @property
    def avar_nose_low(self):
        for avar in self.avars:
            if avar.jnt == self.inf_nose_low:
                return avar

    @property
    def avars_snear(self):
        return [avar for avar in self.avars if avar.jnt in self.influences_snear]

    @property
    def inf_nostrils(self):
        raise NotImplementedError

    def connect_global_avars(self):
        for avar in self.avars:
            # HACK: Ignore nose bend pivot
            if avar == self.avar_nose_upp:
                continue

            libRigging.connectAttr_withBlendWeighted(self.attr_ud, avar.attr_ud)
            libRigging.connectAttr_withBlendWeighted(self.attr_lr, avar.attr_lr)
            libRigging.connectAttr_withBlendWeighted(self.attr_fb, avar.attr_fb)
            libRigging.connectAttr_withBlendWeighted(self.attr_yw, avar.attr_yw)
            libRigging.connectAttr_withBlendWeighted(self.attr_pt, avar.attr_pt)
            libRigging.connectAttr_withBlendWeighted(self.attr_rl, avar.attr_rl)

    def build(self, rig, **kwargs):
        super(FaceNose, self).build(rig, **kwargs)
        nomenclature_anm = self.get_nomenclature_anm(rig)

        # Create a ctrl that will control the whole nose
        ref = self.inf_nose_low
        if not self.avar_main:
            self.avar_main = self.create_abstract_avar(rig, self._CLS_CTRL, ref, name=self.name)
        self.build_abstract_avar(rig, self._CLS_CTRL, self.avar_main)

        '''
        ctrl_upp_name = nomenclature_anm.resolve()
        if not isinstance(self.ctrl_main, self._CLS_CTRL):
            self.ctrl_main = self._CLS_CTRL()
        self.ctrl_main.build(rig, self.inf_nose_low, name=ctrl_upp_name)
        #self.create_ctrl_macro(rig, self.ctrl_main, self.inf_nose_low)
        '''

        for avar in self.avars:
            libRigging.connectAttr_withLinearDrivenKeys(self.avar_main.attr_ud, avar.attr_ud)
            libRigging.connectAttr_withLinearDrivenKeys(self.avar_main.attr_lr, avar.attr_lr)
            libRigging.connectAttr_withLinearDrivenKeys(self.avar_main.attr_fb, avar.attr_fb)

        if self.avar_nose_upp:
            libRigging.connectAttr_withLinearDrivenKeys(self.avar_main.attr_pt, self.avar_nose_upp.attr_pt)
            libRigging.connectAttr_withLinearDrivenKeys(self.avar_main.attr_rl, self.avar_nose_upp.attr_rl)

        if self.avar_nose_low:
            libRigging.connectAttr_withLinearDrivenKeys(self.avar_main.attr_yw, self.avar_nose_low.attr_yw)

        self.avar_main.calibrate()

        if self.parent:
            pymel.parentConstraint(self.parent, self.avar_nose_upp._stack._layers[0], maintainOffset=True)

        nose_upp_out = self.avar_nose_upp._stack.node
        for avar in self.avars:
            if avar is self.avar_nose_upp:
                continue

            avar_inn = avar._stack._layers[0]
            pymel.parentConstraint(nose_upp_out, avar_inn, maintainOffset=True)

    def unbuild(self):
        super(FaceNose, self).unbuild()
        self.ctrl_main = None

