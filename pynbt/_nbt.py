import gzip
import struct

# (length, format, sign, sign_array)
BYTE = (1, '>b', 'b', 'B')
SHORT = (2, '>h', 's', '')
INT = (4, '>i', '', 'I')
LONG = (8, '>q', 'l', 'L')
FLOAT = (4, '>f', 'f', '')
DOUBLE = (8, '>d', 'd', '')

NBTTypeMap = {}

def typeid(tid):
    def decorator(clazz):
        NBTTypeMap[tid] = clazz
        clazz.TYPEID = tid
        return clazz
    return decorator

class NBTBase:

    @classmethod
    def read(cls, fr):
        raise NotImplementedError

    def write(self, fw):
        raise NotImplementedError

    def toSNBT(self):
        raise NotImplementedError

    def __repr__(self):
        return self.toSNBT()

@typeid(0)
class NBTEnd(NBTBase):
    
    @classmethod
    def read(cls, fr):
        return None
    
    def write(self, fw):
        fw(b'\x00')

    def toSNBT(self):
        raise Exception('Cannot convert TAG_END to SNBT')

@typeid(1)
class NBTByte(NBTBase, int):
    MAINTYPE = BYTE

    def __new__(cls, *args, **kwargs):
        inst = super().__new__(cls, *args, **kwargs)
        MIN = -1 << 8 * cls.MAINTYPE[0] - 1
        MAX = (1 << 8 * cls.MAINTYPE[0] - 1) - 1
        if inst < MIN or inst > MAX:
            raise Exception('Wrong number: %d, %s format requires %d <= number <= %d' % (inst, cls.__name__, MIN, MAX))
        return inst

    @classmethod
    def read(cls, fr):
        value, = struct.unpack(cls.MAINTYPE[1], fr(cls.MAINTYPE[0]))
        return cls(value)

    def write(self, fw):
        fw(struct.pack(self.MAINTYPE[1], self))

    def toSNBT(self):
        return '%d%s' % (self, self.MAINTYPE[2])

@typeid(2)
class NBTShort(NBTByte):
    MAINTYPE = SHORT

@typeid(3)
class NBTInt(NBTByte):
    MAINTYPE = INT

@typeid(4)
class NBTLong(NBTByte):
    MAINTYPE = LONG

@typeid(5)
class NBTFloat(NBTBase, float):
    MAINTYPE = FLOAT

    @classmethod
    def read(cls, fr):
        value, = struct.unpack(cls.MAINTYPE[1], fr(cls.MAINTYPE[0]))
        return cls(value)

    def write(self, fw):
        fw(struct.pack(self.MAINTYPE[1], self))

    def toSNBT(self):
        s = ('%f' % self).rstrip('0')
        if s.endswith('.'):
            s += '0'
        return '%s%s' % (s, self.MAINTYPE[2])

@typeid(6)
class NBTDouble(NBTFloat):
    MAINTYPE = DOUBLE
    def toSNBT(self):
        return '%s%s' % (str(float(self)), self.MAINTYPE[2])

@typeid(7)
class NBTByteArray(NBTBase, list):
    MAINTYPE = BYTE

    def __new__(cls, *args, **kwargs):
        inst = super().__new__(cls, *args, **kwargs)
        for i, j in enumerate(inst):
            if not isinstance(j, int):
                j = int(j)
                inst[i] = j
            cls.checkrange(j)
        return inst

    @classmethod
    def checkrange(cls, value):
        MIN = -1 << 8 * cls.MAINTYPE[0] - 1
        MAX = (1 << 8 * cls.MAINTYPE[0] - 1) - 1
        if value < MIN or value > MAX:
            raise Exception('Wrong number: %d, %s format requires %d <= number <= %d' % (value, cls.__name__, MIN, MAX))

    @classmethod
    def read(cls, fr):
        l = NBTInt.read(fr)
        if l < 0:
            raise Exception('The length of %s cannot be negetive: %d' % (cls.__name__, l))
        values = [0] * l
        for i in range(l):
            values[i], = struct.unpack(cls.MAINTYPE[1], fr(cls.MAINTYPE[0]))
        return cls(values)

    def write(self, fw):
        l = len(self)
        MAX = (1 << 8 * INT[0] - 1) - 1
        if l > MAX:
            raise Exception('Overflow! The max length of array is %d.' % MAX)
        NBTInt(l).write(fw)
        for i in self:
            fw(struct.pack(self.MAINTYPE[1], i))

    def toSNBT(self):
        s = ''
        if self:
            for i in self:
                s += '%d, ' % i
            s = s[:-2]
        return '[%s; %s]' % (self.MAINTYPE[3], s)

    def copy(self):
        inst = super().copy()
        return self.__class__(inst)

    def append(self, obj):
        if not isinstance(obj, int):
            obj = int(obj)
        self.checkrange(obj)
        super().append(obj)

    def insert(self, index, obj):
        if not isinstance(obj, int):
            obj = int(obj)
        self.checkrange(obj)
        super().insert(index, obj)

    def __setitem__(self, index, obj):
        if not isinstance(obj, int):
            obj = int(obj)
        self.checkrange(obj)
        super().__setitem__(index, obj)

@typeid(8)
class NBTString(NBTBase, str):

    @classmethod
    def read(cls, fr):
        l = NBTShort.read(fr)
        return cls(fr(l).decode('utf-8'))

    def write(self, fw):
        data = self.encode('utf-8')
        try:
            l = NBTShort(len(data))
        except:
            raise Exception('The string %s is too large' % repr(self[:16] + '...'))
        l.write(fw)
        fw(data)

    def toSNBT(self):
        return repr(str(self))

@typeid(9)
class NBTList(NBTBase, list):
    
    def __init__(self, typeid, items = []):
        if type(typeid).__name__ == 'type' and 'TYPEID' in dir(typeid):
            self.type = NBTByte(typeid.TYPEID)
        elif typeid in NBTTypeMap:
            self.type = NBTByte(typeid)
        else:
            raise Exception('Unknown type: ' + str(typeid))
        for i in range(len(items)):
            if not isinstance(items[i], NBTTypeMap[self.type]):
                try:
                    items[i] = NBTTypeMap[self.type](items[i])
                except:
                    raise Exception('The type %s is not equals to %s' % (i.__class__.__name__, NBTTypeMap[self.type].__name__))
        super().__init__(items)

    @classmethod
    def read(cls, fr):
        t = NBTByte.read(fr)
        if t not in NBTTypeMap:
            raise Exception('Unknown type id: %d' % t)
        l = NBTInt.read(fr)
        if l < 0:
            raise Exception('The length of %s cannot be negetive: %d' % (cls.__name__, l))
        values = [None] * l
        for i in range(l):
            values[i] = NBTTypeMap[t].read(fr)
        return cls(t, values)

    def write(self, fw):
        t = self.type
        l = len(self)
        MAX = (1 << 8 * INT[0] - 1) - 1
        if l > MAX:
            raise Exception('Overflow! The max length of list is %d.' % MAX)
        t.write(fw)
        NBTInt(l).write(fw)
        for i in self:
            i.write(fw)

    def copy(self):
        inst = super().copy()
        return self.__class__(self.type, inst)

    def append(self, obj):
        if not isinstance(obj, NBTTypeMap[self.type]):
            obj = NBTTypeMap[self.type](obj)
        super().append(obj)

    def insert(self, index, obj):
        if not isinstance(obj, NBTTypeMap[self.type]):
            obj = NBTTypeMap[self.type](obj)
        super().insert(index, obj)

    def __setitem__(self, index, obj):
        if not isinstance(obj, NBTTypeMap[self.type]):
            obj = NBTTypeMap[self.type](obj)
        super().__setitem__(index, obj)

    def toSNBT(self):
        s = ''
        if self:
            for i in self:
                s += '%s, ' % i.toSNBT()
            s = s[:-2]
        return '[%s]' % s

    def __str__(self):
        return self.toSNBT()

@typeid(10)
class NBTCompound(NBTBase, dict):

    def __new__(cls, *args, **kwargs):
        inst = super().__new__(cls, *args, **kwargs)
        for i in inst:
            if not isinstance(inst[i], NBTBase):
                raise Exception('This item must be a NBT type: (%s: %s(%s))' % (i, str(inst[i]), inst[i].__class__.__name__))
        return inst

    @staticmethod
    def readRoot(fr):
        typeid = NBTByte.read(fr)
        if NBTTypeMap[typeid] != NBTCompound:
            raise Exception('Unknown NBT file header: 0x%X' % typeid)
        nbtname = NBTString.read(fr)
        if nbtname != '':
            print('Warning: The name of root compound should to be empty, but it\'s %s' % nbtname)
        return NBTTypeMap[typeid].read(fr)

    @staticmethod
    def writeRoot(fw, root):
        NBTByte(NBTCompound.TYPEID).write(fw)
        NBTString().write(fw)
        root.write(fw)

    @classmethod
    def read(cls, fr):
        values = {}
        while 1:
            typeid = NBTByte.read(fr)
            nbttype = NBTTypeMap[typeid]
            if nbttype == NBTEnd:
                break
            nbtname = NBTString.read(fr)
            nbt = nbttype.read(fr)
            values[nbtname] = nbt
        return cls(values)

    def write(self, fw):
        for i in self:
            typeid = self[i].TYPEID
            NBTByte(typeid).write(fw)
            NBTString(i).write(fw)
            self[i].write(fw)
        NBTEnd().write(fw)

    def toSNBT(self):
        s = ''
        if self:
            for i in self:
                s += '%s: %s, ' % (i, self[i].toSNBT())
            s = s[:-2]
        return '{%s}' % s
        
    def copy(self):
        inst = super().copy()
        return self.__class__(inst)

    def __setitem__(self, index, obj):
        if index in self:
            obj = self[index].__class__(obj)
        elif not isinstance(obj, NBTBase):
            raise Exception('The new item "%s" must be of NBT type.' % index)
        super().__setitem__(index, obj)

    def __str__(self):
        return self.toSNBT()

@typeid(11)
class NBTIntArray(NBTByteArray):
    MAINTYPE = INT

@typeid(12)
class NBTLongArray(NBTByteArray):
    MAINTYPE = LONG

def readFile(path : str, compress = True) -> NBTCompound:
    with gzip.open(path, 'rb') if compress else open(path, 'rb') as fd:
        fr = fd.read
        return NBTCompound.readRoot(fr)

def writeFile(path : str, nbt : NBTCompound, compress = True):
    with gzip.open(path, 'wb') if compress else open(path, 'wb') as fd:
        fw = fd.write
        NBTCompound.writeRoot(fw, nbt)