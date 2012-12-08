import maya.cmds as cmds
import maya.mel as mm
from math import sqrt
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
    count = cmds.polyEvaluate(model, uv=True)
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

    def GetUVNameList(self, pref='.uv'):
        uv_count = cmds.polyEvaluate(self.model, uv=True)
        uv_name_list = []
        for i in range(uv_count):
            uv_name_list += [self.model + pref + '[' + str(i) + ']']
        return uv_name_list
        
    def GetUVMapList(self):
        return self.GetUVNameList(pref='.map')

#------------------------------------------------
# Vertex Class
#------------------------------------------------
class Vertex(BaseStructure):
    def __init__(self, model):
        BaseStructure.__init__(self, model)
        
        print '-------------------'
        print 'importing Vertex'
        
        self.vtx_names = GetVerticesList(model)
        self.uv_names = self.GetUVNameList()
        self.uv_maps = self.GetUVMapList()
        self.uv_count = len(self.uv_names)
        self.vertex_count = cmds.polyEvaluate(model, v=True)
        
        print 'vertex count: ', self.vertex_count
        
        self.uvs = self.ToUVs()
        self.map_to_vtx = self.BuildVertexIndicesFromMaps()
        self.vtx_to_map= self.BuildMapIndicesFromVertexNames()
        
        #self.indices = self.ToIndices()
        self.positions = self.ToPositions()
        self.normals = self.ToNormals()
        print 'normal count: ', len(self.normals)
        
        self.bone_weights = self.InitBoneWeight()
        self.bone_num = self.InitBoneNum()
        self.edge_flag = self.InitEdgeFlag()
        
        self.count = len(self.positions)
    
    def BuildMapIndicesFromVertexNames(self):
        vtx_to_map = {}
        for i in range(self.vertex_count):
            vtx_to_map[self.vtx_names[i]] = cmds.polyListComponentConversion(self.vtx_names[i], tuv=True)
        return vtx_to_map
    
    def BuildVertexIndicesFromMaps(self):
        map_to_vtx = {}
        except_count = 0
        for i in range(self.uv_count):
            try:
                to_vtx_name = cmds.polyListComponentConversion(self.uv_maps[i], tv=True)
                map_to_vtx[self.uv_maps[i]] = to_vtx_name[0]
            except:
                print 'no exist uv: ', self.uv_maps[i]
                map_to_vtx[self.uv_maps[i]] = map_to_vtx.values()[0]
        return map_to_vtx
    
    # parameter of joints is Hash<Int->String>
    def SetupBoneWeight(self, skin_cluster, joints):
        weights = [None] * self.uv_count
        bone_num = [None] * self.uv_count
        for map,vtx in self.map_to_vtx.items():
            joint_weights = []
            for j in range(len(joints)):
                weight = cmds.skinPercent(skin_cluster, vtx, transform=joints[j], q=True)
                joint_weights += [[j, weight]]
            
            joint_weights = sorted(joint_weights, key=lambda x:x[1], reverse=True)
            num = []
            index = GetIndex(map)
            if len(joint_weights) > 0:
                weights[index] = joint_weights[0][1]
                num += [joint_weights[0][0]]
                if len(joint_weights) > 1:
                    num += [joint_weights[1][0]]
            else:
                weights[index] = 1
                num += [0,0]
            bone_num[index] = num
        self.bone_weights = weights
        self.bone_num = bone_num
    
    def InitEdgeFlag(self):
        flag = []
        for i in range(self.uv_count): flag += [0]
        return flag
    
    def InitBoneNum(self):
        bone_num = []
        for i in range(self.uv_count):
            bone_num += [[0,0]]
        return bone_num        
    
    def InitBoneWeight(self):
        weight = []
        for i in range(self.uv_count):
            weight = [1]
        return weight
    
    def ToIndices(self):
        indices = []
        for name in self.vtx_names:
            indices.append(GetIndex(name))
        return indices

    def ToPositions(self):
        pos = [None] * self.uv_count
        for map,vtx in self.map_to_vtx.items():
            index = GetIndex(map)
            pos[index] = GetVertexPosition(vtx)
        return pos
            
    def ToNormals(self):
        nrm = [None] * self.uv_count
        for map,vtx in self.map_to_vtx.items():
            index = GetIndex(map)
            nrm[index] = GetVertexNormal(vtx)
        return nrm

    def ToUVs(self):
        uvs = []
        for name in self.uv_names:
            uvs += [GetUVCoordinate(name)]
        return uvs

#------------------------------------------------
# Face Class
#------------------------------------------------
class Face(BaseStructure):
    def __init__(self, model, vertex):
        BaseStructure.__init__(self, model)
        
        print '-------------------'
        print 'importing Face'
        
        self.names = GetFacesList(model)
        print 'name count: ', len(self.names)
        
        self.vtx_indices = self.BuildTriangleIntoIndices()
        print 'vtx indices count: ', len(self.vtx_indices)
        
        self.count = len(self.vtx_indices)
        
        self.materials_from_face = self.ToMaterialFromFace()
        print 'materials from face: ', len(self.materials_from_face)
        
        self.vtx_indices = self.SortingFaceByMaterial(self.materials_from_face)
        print 'sorted vtx indices count: ', len(self.vtx_indices)
        
        self.ResortTriangleForFaceNormal(vertex)
        print 'resorted'
        
    def ResortTriangleForFaceNormal(self, vertex):
        for fi in range(len(self.vtx_indices)):
            vis = self.vtx_indices[fi]
            if len(vis) <= 0: continue
            vtx_pos = []
            vtx_nrm = []
            for vtx_ind in vis:
                vtx_nrm += [vertex.normals[vtx_ind]]
                vtx_pos += [vertex.positions[vtx_ind]]
            v1 = self.SubPosition(vtx_pos[1], vtx_pos[0])
            v2 = self.SubPosition(vtx_pos[2], vtx_pos[1])
            cross = self.CrossVectors(v1, v2)
            cross = self.NormalizeVector(cross)
            dot_val = 0.0
            for i in range(3): dot_val += self.DotNormalAndCross(vtx_nrm[i], cross)
            if dot_val < 0:    # swap indices
                tmp = self.vtx_indices[fi][0]
                self.vtx_indices[fi][0] = self.vtx_indices[fi][2]
                self.vtx_indices[fi][2] = tmp
                
    
    def DotNormalAndCross(self, n, c):
        return mm.eval('float $b = <<%f, %f, %f>> * <<%f, %f, %f>>' % (n[0], n[1], n[2], c[0], c[1], c[2]))
    
    def NormalizeVector(self, v):
        length = 0
        try:
            length = 1.0 / sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])
        except ZeroDivisionError, E:
            print 'raise ZeroDivisionError!?: ', v
            return (1.0, 0.0, 0.0)
        return (length*v[0], length*v[1], length*v[2])
    
    def CrossVectors(self, v1, v2):
        return mm.eval('$a = <<%f, %f, %f>> ^ <<%f, %f, %f>>' % (v1[0], v1[1], v1[2], v2[0], v2[1], v2[2]))
    
    def SubPosition(self, p1, p2):
        sub_p = []
        for i in range(3):
            sub_p += [p1[i] - p2[i]]
        return tuple(sub_p)
        
    def CreateIndicesFromFaceNameToUVNames(self, uv):
        uv_indices = re.search('\[(\d+|\d+:\d+)\]', uv)
        uv_indices = uv_indices.group().rstrip(']').lstrip('[').split(':')
        for i, uv in enumerate(uv_indices):
            uv_indices[i] = int(uv_indices[i])
        if len(uv_indices) > 1:
            diff = uv_indices[1] - uv_indices[0] - 1
            tmp = uv_indices[1]
            del uv_indices[1]
            for i in range(diff):
                uv_indices += [uv_indices[0] + i + 1]
            uv_indices += [tmp]
        return uv_indices
    
    def SearchFaceToUVForUVIndices(self, face_name):
        face_to_uvs_name = cmds.polyListComponentConversion(face_name, tuv=True)
        face_to_uvs = []
        for uv in face_to_uvs_name:    # search maps
            face_to_uvs += self.CreateIndicesFromFaceNameToUVNames(uv)
        return face_to_uvs
    
    def BuildTriangleIntoIndices(self):
        indices = []
        for face_name in self.names:
            triangle = self.SearchFaceToUVForUVIndices(face_name)
            if len(triangle) > 3:
                raise StandardError, "do not triangulate your model."
            indices += [triangle]
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
        
        print '-------------------'
        print 'importing Material'
        
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
        
        print '-------------------'
        print 'importing Bone'
        
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
            xfm = cmds.xform(bone, q=True, ws=True, t=True)
            pos += [xfm]
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
                for j,p in enumerate(self.names):
                    if r[0] == p:
                        r = j
                        break
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
        
        print '-------------------'
        print 'importing Skin'
        
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
        print 'selected: ', self.selected
        try:
            self.model = self.selected[0]
        except IndexError:
            print "do not select objects."
            raise "do not select objects."
        try:
            self.root_bone = self.selected[1]
        except IndexError:
            self.root_bone = None
        try:
            self.skin_names = self.selected[2:]
        except IndexError:
            pass
            
#------------------------------------------------
# Exporter Base Class
#------------------------------------------------
class ExporterBase:
    def __init__(self, data):
        self.data = data
        
    def Float(self, bin, d):
        bin.write(pack('<f', d))
    
    def UInt(self, bin, d):
        bin.write(pack('<I', d))
        
    def Int(self, bin, d):
        bin.write(pack('<i', d))
        
    def Word(self, bin, d):
        bin.write(pack('<H', d))
        
    def Words(self, bin, arr):
        for d in arr: self.Word(bin, d)
    
    def Byte(self, bin, d):
        bin.write(pack('<B', d))
        
    def DWord(self, bin, d):
        self.UInt(bin, d)
        
    def Char(self, bin, d):
        try:
            d = ord(d)
        except TypeError:
            d = d
        bin.write(pack('<b', d))
        
    def Floats(self, bin, arr):
        for d in arr: self.Float(bin, d)
        
    def Chars(self, bin, arr):
        for d in arr: self.Char(bin, d)
        
    def ConvertStringIntoArray(self, data, max_length):
        name = []
        for i in range(len(data)):
            pusher = ord(data[i])
            name += [int(pusher)]
        name += [0]
        
        if len(name) > max_length:
            name = name[:max_length-1]
        
        length = len(name)
        for j in range(max_length-length):
            name += [0xFD]
        return name
        
    def Export(self, bin):
        pass
        
    def Close(self):
        self.bin.close
        
    def ReverseVector(self, v):
        vec = list(v)
        vec[2] = -vec[2]
        return vec
        
#------------------------------------------------
# Export Header Class
#------------------------------------------------
class ExportHeader(ExporterBase):
    def __init__(self, model):
        ExporterBase.__init__(self, None)
        self.model = model
        
    def Export(self, bin):
        print '-------------------'
        print 'exporting Header'
        magic = 'Pmd'
        for c in magic: self.Char(bin, c)
        self.Float(bin, 1.00)
        
        model_name = self.ConvertStringIntoArray(self.model, 20)
        self.Chars(bin, model_name)
        caption = self.ConvertStringIntoArray('Exported by MayaToPMD', 256)
        self.Chars(bin, caption)

#------------------------------------------------
# Export Vertices Class
#------------------------------------------------
class ExportVertices(ExporterBase):
    def __init__(self, data):
        ExporterBase.__init__(self, data)

    def Export(self, bin):
        print '-------------------'
        print 'exporting Vertices'
        print 'vertices count: ', self.data.count
        self.DWord(bin, self.data.count)
        for v,i in enumerate(range(self.data.count)):
            pos = self.ReverseVector(self.data.positions[i])
            self.Floats(bin, pos)
            
            self.Floats(bin, self.data.normals[i])
            
            uvs = list(self.data.uvs[i])
            uvs[1] = 1.0-uvs[1]
            self.Floats(bin, uvs)
            
            self.Words(bin, self.data.bone_num[i])
            self.Byte(bin, int(self.data.bone_weights[i] * 100))
            self.Byte(bin, self.data.edge_flag[i])
            
#------------------------------------------------
# Export Faces Class
#------------------------------------------------
class ExportFaces(ExporterBase):
    def __init__(self, data):
        ExporterBase.__init__(self, data)

    def Export(self, bin):
        print '-------------------'
        print 'exporting Face'
        print 'faces count: ', self.data.count
        self.DWord(bin, self.data.count * 3)
        for triangle in self.data.vtx_indices:
            # swap triangle order, it's different from MMD.
            if len(triangle) <= 0: self.Words(bin, [0, 0, 0])    # counter zero polygon
            self.Words(bin, self.Swap(triangle))
            #self.Words(bin, triangle)

    def Swap(self, triangle):
        tri = list(triangle)
        tmp = tri[0]
        tri[0] = tri[2]
        tri[2] = tmp
        return tri
        
#------------------------------------------------
# Export Materials Class
#------------------------------------------------
class ExportMaterials(ExporterBase):
    def __init__(self, data):
        ExporterBase.__init__(self, data)

    def Export(self, bin):
        print '-------------------'
        print 'exporting Material'
        print 'materials count: ', self.data.count
        self.DWord(bin, self.data.count)
        for i in range(self.data.count):
            self.Floats(bin, self.data.diffuse[i])
            print 1.0-self.data.transparent[i]
            self.Float(bin, 1.0-self.data.transparent[i])
            self.Float(bin, self.data.specularity[i])
            self.Floats(bin, self.data.specular[i])
            #self.Floats(self.data.ambient[i])
            self.Floats(bin, [0.0,0.0,0.0])    # best
            #self.Byte(self.data.toon_index[i])
            self.Byte(bin, 0xFF)
            self.Byte(bin, self.data.edge_flag[i])
            self.DWord(bin, self.data.face_count[i]*3)
            
            length = len(self.data.file_name[i])
            length = 20 if length > 20 else length
            print length
            for j in range(length):
                self.Char(bin, self.data.file_name[i][j])
            for j in range(20-length):
                self.Char(bin, 0)
                
#------------------------------------------------
# Export Bones Class
#------------------------------------------------
class ExportBones(ExporterBase):
    def __init__(self, data):
        ExporterBase.__init__(self, data)

    def Export(self, bin):
        print '-------------------'
        print 'exporting Bone'
        
        if self.data != None:
            print 'bone count: ', self.data.count
            self.Word(bin, self.data.count)
            
            for i in range(self.data.count):
                print self.data.short[i]
                short_name = self.ConvertStringIntoArray(self.data.short[i], 20)
                
                length = len(short_name)
                length = 20 if length > 20 else length
                for j in range(length):
                    self.Char(bin, short_name[j])
                    
                self.Word(bin, self.data.parent[i])
                self.Word(bin, 0xFFFF)
                self.Byte(bin, 0)
                self.Word(bin, 0)
                
                pos = self.ReverseVector(self.data.bone_pos[i])
                self.Floats(bin, pos)
        else:
            print 'do not have bones.'

#------------------------------------------------
# Export IK Class
#------------------------------------------------
class ExportIKs(ExporterBase):
    def __init__(self):
        ExporterBase.__init__(self, None)

    def Export(self, bin):
        print '-------------------'
        print 'exporting IK'
        self.Word(bin, 0)
        
#------------------------------------------------
# Export Skins Class
#------------------------------------------------
class ExportSkins(ExporterBase):
    def __init__(self, data):
        ExporterBase.__init__(self, data)

    def WriteSkin(self, bin, word, count, type, iv):
        print '----'
        print 'name: ', word
        print 'count: ', count
        print 'type: ', type
        self.Chars(bin, word)
        self.DWord(bin, count)
        self.Byte(bin, type)
        self.WriteVertex(bin, count, iv)
        
    def WriteVertex(self, bin, count, vertex):
        for j in range(count):
            self.DWord(bin, vertex[j][0])
            self.Floats(bin, vertex[j][1])
            #print 'iv: ', vertex[j][0], vertex[j][1]

    def Export(self, bin):
        print '-------------------'
        print 'exporting Skin'
        print 'skin count: ', self.data.skin_count
        
        if self.data.skin_count > 0:
            self.Word(bin, self.data.skin_count+1)
        
            # base
            base_name = self.ConvertStringIntoArray('base', 20)
            self.WriteSkin(bin, base_name, self.data.base_count, 0, self.data.base_indices_vertices)
        else:
            self.Word(bin, 0)    # not have skin
        
        # skin
        for i in range(self.data.skin_count):
            skin_name = self.ConvertStringIntoArray(self.data.names[i], 20)
            self.WriteSkin(bin, skin_name, self.data.vert_count[i], 1, self.data.skin_indices_vertices[i])

#------------------------------------------------
# Export Display List for Skin Frame
#------------------------------------------------
class ExportSkinFrameForDisplayList(ExporterBase):
    # data is Skin
    def __init__(self, data):
        ExporterBase.__init__(self, data)
        
    def Export(self, bin):
        print '-------------------'
        print 'exporting Display List for Skin Frame'
        length = len(self.data.names)
        self.Byte(bin, length)
        print 'count: ', length
        
        for i in range(length):
            self.Word(bin, i)
            print 'index: ', i

#------------------------------------------------
# Export Platform Class
#------------------------------------------------
class ExportPlatform:
    def __init__(self, dwindow):
        self.list = [ExportHeader(dwindow.model),
            ExportVertices(dwindow.vertex),
            ExportFaces(dwindow.face),
            ExportMaterials(dwindow.material),
            ExportBones(dwindow.bone),
            ExportIKs(),
            ExportSkins(dwindow.skin),
            ExportSkinFrameForDisplayList(dwindow.skin)]

    def Export(self, bin):
        for l in self.list: l.Export(bin)
        
        print '-------------------'
        print 'exporting Window'
        bin.write(pack('<B', 0))
        bin.write(pack('<B', 0))
        bin.write(pack('<B', 0))
        
        print '-------------------'
        print 'end'

"""
cmds.select('pCube1')
cmds.select('joint1', tgl=True)
cmds.select('pCube2', tgl=True)
cmds.select('pCube3', tgl=True)
"""

w = StructureWindow()


bin = open('C:/export.pmd', 'wb')
e = ExportPlatform(w)
try:
    e.Export(bin)
except Exception, inst:
    print type(inst)
    print inst
    raise Exception(type(inst))
bin.close


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