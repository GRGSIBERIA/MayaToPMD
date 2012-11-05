import maya.cmds as cmds
import re

#-----------------------------------------------
# Util Script
#-----------------------------------------------
def GetUVCoordinate(uv):
    cmds.select(uv)
    return cmds.polyEditUV(q=True)

def GetVertexNormal(vtx):
    cmds.select(vtx)
    count = len(cmds.polyNormalPerVertex(q=True, x=True))
    x = cmds.polyNormalPerVertex(q=True, x=True)
    y = cmds.polyNormalPerVertex(q=True, y=True)
    z = cmds.polyNormalPerVertex(q=True, z=True)
    avg = [0, 0, 0]
    dif = 1.0 / count
    for cnt in range(count):
        avg[0] += x[cnt]
        avg[1] += y[cnt]
        avg[2] += z[cnt]
    for cnt in range(3):
        avg[cnt] *= dif
    return avg

def GetVertexPosition(vtx):
    return cmds.pointPosition(vtx)

def GetIndex(name):
    m = re.search('\[\w+\]', name)
    index = m.group().lstrip('[').rstrip(']')
    return int(index)

def GetIndices(name):
    indices = name.split('     ')[2:]
    indices[len(indices)-1] = indices[len(indices)-1].split(' ')[0]
    for i in range(len(indices)):
        indices[i] = int(indices[i])
    return indices

def GetVertexIndicesFromTriangle(f):
    vtxs = cmds.polyInfo(fv=True)
    indices = []
    for vtx in vtxs:
        indices += GetIndices(vtx)
    return indices

def GetVerticesList(model):
    count = cmds.polyEvaluate(model, v=True)
    return GetPolyElementNameList(model, count, 'vtx')

def GetFacesList(model):
    count = cmds.polyEvaluate(model, f=True)
    return GetPolyElementNameList(model, count, 'f')
    
def GetUVList(model):
    count = cmds.polyEvaluate(model, v=True)
    return GetPolyElementNameList(model, count, 'uv')

def GetPolyElementNameList(model, count, attr_name):
    attr = []
    for c in range(count):
        attr.append(model + '.' + attr_name + '[' + str(c) + ']')
    return attr


#------------------------------------------------
# Structure Base
#------------------------------------------------
class BaseStructure:
    def __init__(self, model):
        self.model = model
        self.names = None

#------------------------------------------------
# Vertex Class
#------------------------------------------------
class Vertex(BaseStructure):
    def __init__(self, model):
        BaseStructure.__init__(self, model)
        self.names = GetVerticesList(model)
        self.uv_names = GetUVList(model)
        self.indices = self.ToIndices()
        self.positions = self.ToPositions()
        self.normals = self.ToNormals()
        self.uvs = self.ToUVs()
        self.bone_weights = self.InitBoneWeight()
        self.bone_num = self.InitBoneNum()
        self.count = len(self.positions)
    
    # parameter of joints is Hash<Int->String>
    def SetupBoneWeight(self, skin_cluster, joints):
        weights = []
        bone_num = []
        for vtx in self.names:
            joint_weights = []
            for j in range(len(joints)):
                weight = cmds.skinPercent(skin_cluster, vtx, transform=joints[j], q=True)
                joint_weights += [[j, weight]]
            #joint_weights.sort()
            #joint_weights.reverse()
            joint_weights = sorted(joint_weights, key=lambda x:x[1], reverse=True)
            num = []
            if len(joint_weights) > 0:
                weights += [joint_weights[0][1]]
                num += [joint_weights[0][0]]
                if len(joint_weights) > 1:
                    num += [joint_weights[1][0]]
            else:
                weights += [1]
                num += [0,0]
            bone_num += [num]
        self.bone_weights = weights
        self.bone_num = bone_num
    
    def InitBoneNum(self):
        bone_num = []
        for i in range(len(self.positions)):
            bone_num.append([0,0])
        return bone_num        
    
    def InitBoneWeight(self):
        weight = []
        for i in range(len(self.positions)):
            weight.append(100)
        return weight
    
    def ToIndices(self):
        indices = []
        for name in self.names:
            indices.append(GetIndex(name))
        return indices

    def ToPositions(self):
        pos = []
        for name in self.names:
            pos.append(GetVertexPosition(name))
        return pos
            
    def ToNormals(self):
        nrm = []
        for name in self.names:
            nrm.append(GetVertexNormal(name))
        return nrm

    def ToUVs(self):
        uvs = []
        for name in self.uv_names:
            uvs.append(GetUVCoordinate(name))
        return uvs

#------------------------------------------------
# Face Class
#------------------------------------------------
class Face(BaseStructure):
    def __init__(self, model, vertex):
        BaseStructure.__init__(self, model)
        self.names = GetFaceList(model)
        self.vtx_indices = BuildTriangleIntoIndices(vertex)
        self.count = len(self.vtx_indices)
        
    def BuildTriangleIntoIndices(self, vertex):
        indices = []
        for name in self.names:
            indices += [GetVertexIndicesFromTriangle(name)]
        return indices

s = cmds.ls(sl=True)
v = Vertex(s[0])
v.SetupBoneWeight('skinCluster1', ['joint1', 'joint2', 'joint3'])
print v.bone_weights

#get selecting uv coordinate
#print cmds.polyEditUV(q=True)

#get vertex position
#print cmds.pointPosition(s[0])

#get polygon count of vertex and face.
#print cmds.polyEvaluate(s[0], v=True)
#print cmds.polyEvaluate(s[0], f=True)

#check object type from joint
#print cmds.objectType(s[0], isType='joint')

#check object type from skinCluster
#print cmds.objectType(s[0], isType='skinCluster')

#get target history from list.
#print cmds.listHistory(s[0])

#get target weight
#print cmds.skinPercent('skinCluster1', s[0]+'.vtx[0]', transform='joint1', q=True)