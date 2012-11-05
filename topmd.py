import maya.cmds as cmds
from struct import *
import re

#-----------------------------------------------
# Util Script
#-----------------------------------------------
def GetAssinedMaterialNodeFromModel(model):
    cmds.select(model)
    cmds.hyperShade(smn=True)
    return cmds.ls(sl=True)

def GetUVCoordinate(uv):
    cmds.select(uv)
#    return cmds.polyEditUV(q=True)
    return cmds.getAttr(uv)[0]

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
    r = re.compile('\d+')
    vtx_list = r.findall(name)[1:]
    for i in range(len(vtx_list)):
        vtx_list[i] = int(vtx_list[i])
    return vtx_list

def GetVertexIndicesFromTriangle(f):
    cmds.select(f)
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
        self.edge_flag = self.InitEdgeFlag()
    
    def InitEdgeFlag(self):
        flag = []
        for i in range(self.count): flag += [1]
        return flag
    
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
        self.names = GetFacesList(model)
        self.vtx_indices = self.BuildTriangleIntoIndices(vertex)
        self.count = len(self.vtx_indices)
        self.materials_from_face = self.ToMaterialFromFace()
        self.vtx_indices = self.SortingFaceByMaterial(self.materials_from_face)
        
    def BuildTriangleIntoIndices(self, vertex):
        indices = []
        for name in self.names:
            indices += [GetVertexIndicesFromTriangle(name)]
        return indices
        
    def ToMaterialFromFace(self):
        materials = []
        for name in self.names:
            cmds.select(name)
            cmds.hyperShade(smn=True)
            materials += cmds.ls(sl=True)
        return materials
    
    def SortingFaceByMaterial(self, materials):
        mhash = {}
        for i in range(len(materials)):
            mhash[i] = materials[i]
        sorted_mesh = []
        for k,v in sorted(mhash.items(), key=lambda x:x[1]):
            sorted_mesh += [[k,v]]
        result = []
        for smesh in sorted_mesh:    # sorting mesh by material
            result += [self.vtx_indices[smesh[0]]]
        return result

#------------------------------------------------
# Material Class
#------------------------------------------------
class Material(BaseStructure):
    def __init__(self, model, face):
        BaseStructure.__init__(self, model)
        self.materials = sorted(GetAssinedMaterialNodeFromModel(model))
        self.diffuse = self.ToDiffuse()
        self.transparent = self.ToTransparent()
        self.face_count = self.CountFaceByMaterial(face)
        self.ambient = self.InitAmbient()
        self.specular = self.ToSpecular()
        self.specularity = self.ToSpecularity()
        self.toon_index = self.InitToonIndex()
        self.edge_flag = self.InitEdgeFlag()
        self.file_name = self.ToFileName()
        self.count = len(self.materials)
        
    def ToFileName(self):
        files = []
        for mat in self.materials:
            node = cmds.listConnections(mat, d=False, t='file')
            if node != None:
                files += [cmds.getAttr(node[0]+'.fileTextureName')]
            else:
                files += [u""]
        return files
        
    def InitEdgeFlag(self):
        flag = []
        for mat in self.materials:
            flag += [1]
        return flag
        
    def InitToonIndex(self):
        toon = []
        for mat in self.materials:
            toon += [0xFF]
        return toon
        
    def ToSpecularity(self):
        spec = []
        for mat in self.materials:
            try:
                cmds.select(mat)
                spec += [cmds.getAttr(mat + '.eccentricity')]
            except ValueError:
                spec += [0.0]
        return spec
        
    def ToSpecular(self):
        spec = []
        for mat in self.materials:
            try:
                cmds.select(mat)
                spec += cmds.getAttr(mat + '.specularColor')
            except ValueError:
                spec += [(0.0, 0.0, 0.0)]
        return spec
        
    def InitAmbient(self):
        amb = []
        for i in self.materials:
            amb += [[1.0, 1.0, 1.0]]
        return amb
        
    def ToDiffuse(self):
        diffuse = []
        for mat in self.materials:
            diffuse += cmds.getAttr(mat + '.color')
        return diffuse
        
    def ToTransparent(self):
        transp = []
        for mat in self.materials:
            t = cmds.getAttr(mat + '.transparency')[0]
            transp += [0.298912 * t[0] + 0.586611 * t[1] + 0.114478 * t[2]]
        return transp
    
    def CountFaceByMaterial(self, face):
        faces = face.materials_from_face
        count = []
        for mat in self.materials:
            count += [faces.count(mat)]
        return count

#------------------------------------------------
# Bone Class
#------------------------------------------------
class Bone(BaseStructure):
    def __init__(self, model, root):
        BaseStructure.__init__(self, model)
        cmds.select(root)
        cmds.select(hierarchy=True)
        self.names = cmds.ls(sl=True, l=True)
        self.short = cmds.ls(sl=True)
        self.parent = self.BuildRelative()
        self.tail_pos_index = self.InitTailPosIndex()
        self.bone_type = self.InitBoneType()
        self.ik_parent_bone_index = self.InitIKParentBone()
        self.bone_pos = self.ToBonePosition()
        self.count = len(self.names)
        
    def InitIKParentBone(self):
        ik = []
        for bone in self.names:
            ik += [0]
        return ik
        
    def ToBonePosition(self):
        pos = []
        for bone in self.names:
            pos += cmds.getAttr(bone + '.translate')
        return pos
        
    def InitBoneType(self):
        types = []
        for bone in self.names:
            types = [0]
        return types
        
    def InitTailPosIndex(self):
        indices = []
        for bone in self.names:
            indices += [0xFFFF]
        return indices

    def BuildRelative(self):
        rel = []
        for i,bone in enumerate(self.names):
            r = cmds.listRelatives(bone, p=True, f=True)
            if r != None:
                r = i
            else:
                r = 0xFFFF
            rel += [r]
        return rel

#------------------------------------------------
# Skin Class
#------------------------------------------------
class Skin(BaseStructure):
    def __init__(self, model, skins):
        BaseStructure.__init__(self, model)
        self.names = skins
        self.skin_vertex = self.SetupSkinPositions()
        self.skin_count = len(self.skin_vertex)
        
        # [0] -> index, [1] -> vector
        self.skin_indices_vertices = self.InvestigateIndicesFromVertices()        
        self.vert_count = self.CountVertexFromSkin()

        # [0] -> index, [1] -> position
        self.base_indices_vertices = self.BuildBaseIndicesVertices()
        self.base_count = len(self.base_indices_vertices)

        self.skin_indices_vertices = self.RebuildIndicesVerticesByBase()
        
    def RebuildIndicesVerticesByBase(self):
        base_iv = self.base_indices_vertices
        skin_iv = self.skin_indices_vertices
        
        for skin in skin_iv:
            indices = []
            for ivs in skin:
                for bi, bv in enumerate(base_iv):
                    if bv[0] == ivs[0]:
                        ivs[0] = bi
        return skin_iv
        
    def GetModelVertices(self):
        model_vtx_name = GetVerticesList(self.model)
        model_vtx = []
        for vtx in model_vtx_name:
            model_vtx += [list(GetVertexPosition(vtx))]
        return model_vtx
        
    def BuildBaseIndicesVertices(self):
        model_vtx = self.GetModelVertices()
        skin_ivs = self.skin_indices_vertices
        
        index_flag = {}
        for skin in skin_ivs:
            for ivs in skin:
                index_flag[ivs[0]] = True
        
        sorted_indices = []
        for k,v in sorted(index_flag.items(), key=lambda x:x[0]):
            sorted_indices += [k]
        
        base_ivs = []
        for index in sorted_indices:
            base_ivs += [[index, model_vtx[index]]]
        return base_ivs
        
    # return [0] is index, [1] is vector
    def InvestigateIndicesFromVertices(self):
        model_vtx = self.GetModelVertices()
        
        skin_vtx = self.skin_vertex
        result_vec = []
        for i in range(len(skin_vtx)):    # unit from skin
            index_vec = {}
            sorted_vec = []
            for j in range(len(skin_vtx[i])):    # unit from vertices
                vec = [0, 0, 0]
                for k in range(3): vec[k] = skin_vtx[i][j][k] - model_vtx[j][k]
            
                move_count = 0
                for k in range(3):
                    if vec[k] > 0.00001:
                        move_count += 1
                if move_count > 0:
                    index_vec[j] = vec
                
            for k,v in sorted(index_vec.items(), key=lambda x:x[0]):
                sorted_vec += [[k,v]]
            result_vec += [sorted_vec]
        return result_vec
        
    def CountVertexFromSkin(self):
        count = []
        for iv in self.skin_indices_vertices:
            count += [len(iv)]
        return count
        
    def SetupSkinPositions(self):
        skin_pos = []
        for name in self.names:
            base_pos = cmds.getAttr(name + '.translate')
            vtx_name_list = GetVerticesList(name)
            vtx_pos = []
            for vtx in vtx_name_list:
                pos = list(GetVertexPosition(vtx))
                for i in range(3): pos[i] -= float(base_pos[0][i])
                vtx_pos += [pos]
            skin_pos += [vtx_pos]
        return skin_pos

#------------------------------------------------
# Structure Window Class
#------------------------------------------------
class StructureWindow:
    def __init__(self):
        self.InitNames()
        self.vertex = Vertex(self.model)
        self.face = Face(self.model, self.vertex)
        self.material = Material(self.model, self.face)
        self.bone = Bone(self.model, self.root_bone)
        self.skin = Skin(self.model, self.skin_names)
        
        self.skin_cluster = self.GetSkinCluster()
        self.vertex.SetupBoneWeight(self.skin_cluster, self.bone.names)
        
    def GetSkinCluster(self):
        history = cmds.listHistory(self.model)
        for h in history:
            if cmds.objectType(h, isType='skinCluster'):
                return h
        return None
        
    def InitNames(self):
        self.selected = cmds.ls(sl=True)
        try:
            self.model = self.selected[0]
        except IndexError:
            raise "do not select objects"
        try:
            self.root_bone = self.selected[1]
        except IndexError:
            pass
        try:
            self.skin_names = self.selected[2:]
        except IndexError:
            pass
            
#------------------------------------------------
# Exporter Base Class
#------------------------------------------------
class ExporterBase:
    def __init__(self, bin, data):
        self.bin = bin
        self.data = data
        
    def Float(self, d):
        self.bin.write(pack('<f', d))
    
    def UInt(self, d):
        self.bin.write(pack('<I', d))
        
    def Int(self, d):
        self.bin.write(pack('<i', d))
        
    def Word(self, d):
        self.bin.write(pack('<H', d))
        
    def Words(self, arr):
        for d in arr: self.Word(d)
    
    def Byte(self, d):
        self.bin.write(pack('<B', d))
        
    def DWord(self, d):
        self.UInt(d)
        
    def Char(self, d):
        try:
            d = ord(d)
        except TypeError:
            d = d
        self.bin.write(pack('<b', d))
        
    def Floats(self, arr):
        for d in arr: self.Float(d)
        
    def Chars(self, arr):
        for d in arr: self.Char(d)
        
    def Export(self):
        pass
        
#------------------------------------------------
# Export Header Class
#------------------------------------------------
class ExportHeader(ExporterBase):
    def __init__(self, bin):
        ExporterBase.__init__(self, bin, None)
        
    def Export(self):
        magic = 'Pmd'
        for c in magic: self.Char(c)
        version = 1.00
        self.Float(version)
        for i in range(19): self.Char(0xFD)
        self.Char(0x00)
        for i in range(255): self.Char(0xFD)
        self.Char(0x00)
        print 'export Header'

#------------------------------------------------
# Export Vertices Class
#------------------------------------------------
class ExportVertices(ExporterBase):
    def __init__(self, bin, data):
        ExporterBase.__init__(self, bin, data)

    def Export(self):
        self.DWord(self.data.count)
        for i in range(self.data.count):
            self.Floats(self.data.positions[i])
            self.Floats(self.data.normals[i])
            self.Floats(self.data.uvs[i])
            self.Words(self.data.bone_num[i])
            self.Byte(int(self.data.bone_weights[i] * 100))
            self.Byte(self.data.edge_flag[i])
        print 'export Vertex'
            
#------------------------------------------------
# Export Faces Class
#------------------------------------------------
class ExportFaces(ExporterBase):
    def __init__(self, bin, data):
        ExporterBase.__init__(self, bin, data)

    def Export(self):
        self.DWord(self.data.count)
        for triangle in self.data.vtx_indices:
            self.Words(triangle)
        print 'export Face'
        
#------------------------------------------------
# Export Materials Class
#------------------------------------------------
class ExportMaterials(ExporterBase):
    def __init__(self, bin, data):
        ExporterBase.__init__(self, bin, data)

    def Export(self):
        self.DWord(self.data.count)
        for i in range(self.data.count):
            self.Floats(self.data.diffuse[i])
            self.Float(self.data.transparent[i])
            self.Float(self.data.specularity[i])
            self.Floats(self.data.specular[i])
            self.Floats(self.data.ambient[i])
            self.Byte(self.data.toon_index[i])
            self.Byte(self.data.edge_flag[i])
            self.DWord(self.data.face_count[i])
            self.Chars(self.data.file_name[i])
            for i in range(20-len(self.data.file_name[i])):
                self.Char(0)
        print 'export Material'
                
#------------------------------------------------
# Export Bones Class
#------------------------------------------------
class ExportBones(ExporterBase):
    def __init__(self, bin, data):
        ExporterBase.__init__(self, bin, data)

    def Export(self):
        self.Word(self.data.count)
        null_words = []
        for i in range(20): null_words += [0]
        
        for i in range(self.data.count):
            self.Chars(null_words)
            self.Word(self.data.parent[i])
            self.Word(0xFFFF)
            self.Byte(0)
            self.Word(0)
            self.Floats(self.data.bone_pos[i])
        print 'export Bone'

#------------------------------------------------
# Export IK Class
#------------------------------------------------
class ExportIKs(ExporterBase):
    def __init__(self, bin):
        ExporterBase.__init__(self, bin, None)

    def Export(self):
        self.Word(0)
        print 'export IK'
        
#------------------------------------------------
# Export Skins Class
#------------------------------------------------
class ExportSkins(ExporterBase):
    def __init__(self, bin, data):
        ExporterBase.__init__(self, bin, data)

    def WriteSkin(self, word, count, type, iv):
        self.Chars(word)
        self.Word(count)
        self.Byte(type)
        self.WriteVertex(count, iv)
        
    def WriteVertex(self, count, vertex):
        for j in range(count):
            self.DWord(vertex[j][0])
            self.Floats(vertex[j][1])

    def Export(self):
        null_word = []
        for i in range(20): null_word += [0]
        
        self.Word(self.data.skin_count)
        
        # base
        self.WriteSkin(null_word, self.data.base_count, 0, self.data.base_indices_vertices)
        
        # skin
        for i in range(self.data.skin_count):
            self.WriteSkin(null_word, self.data.vert_count[i], 1, self.data.skin_indices_vertices[i])
        print 'export Skin'

#------------------------------------------------
# Export Platform Class
#------------------------------------------------
class ExportPlatform:
    def __init__(self, fname, dwindow):
        bin = open(fname, 'wb')
        self.bin = bin
        self.fname = fname
        self.list = [ExportHeader(bin),
            ExportVertices(bin, dwindow.vertex),
            ExportFaces(bin, dwindow.face),
            ExportMaterials(bin, dwindow.material),
            ExportBones(bin, dwindow.bone),
            ExportIKs(bin),
            ExportSkins(bin, dwindow.skin)]
        bin.close

    def Export(self):
        self.bin = open(self.fname, 'wb')
        for l in self.list: l.Export()
        self.bin.write(pack('<B', 0))
        self.bin.write(pack('<B', 0))
        self.bin.write(pack('<B', 0))
        self.bin.close

cmds.select('pCube1')
cmds.select('joint1', tgl=True)
cmds.select('pCube2', tgl=True)
cmds.select('pCube3', tgl=True)
w = StructureWindow()
e = ExportPlatform('C:/export.pmd', w)
e.Export()

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

#get assined material node from object
#cmds.select('pCube1')
#cmds.hyperShade(smn=True)
#m = cmds.ls(sl=True)
#print m

#print cmds.listConnections(m[0], d=False, type='file')
#print cmds.getAttr(m[2] + '.specularColor')

#get target weight
#print cmds.skinPercent('skinCluster1', s[0]+'.vtx[0]', transform='joint1', q=True)