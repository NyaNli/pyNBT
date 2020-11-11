import pynbt as nbt

ItemNoSlot = nbt.NBTCompound()
ItemNoSlot['Count'] = nbt.NBTByte()
ItemNoSlot['id'] = nbt.NBTString()
ItemNoSlot['tag'] = nbt.NBTCompound({
    'Damage': nbt.NBTInt(),
    'Unbreakable': nbt.NBTByte(),
    'CanDestroy': nbt.NBTList(nbt.NBTString)
})

item1 = ItemNoSlot.copy()
item1['Count'] = 64
item1['id'] = 'minecraft:stick'

item2 = ItemNoSlot.copy()
item2['Count'] = 1
item2['id'] = 'minecraft:diamond_sword'
item2['tag']['Unbreakable'] = 1

comp = nbt.NBTCompound({'from': item1, 'to': item2})
print(comp)
# Output: {from: {Count: 64b, id: 'minecraft:stick', tag: {Damage: 0, Unbreakable: 1b, CanDestroy: []}}, to: {Count: 1b, id: 'minecraft:diamond_sword', tag: {Damage: 0, Unbreakable: 1b, CanDestroy: []}}}

nbt.writeFile('trade.dat', comp, compress=False)
