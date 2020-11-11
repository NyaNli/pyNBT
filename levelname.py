import pynbt as nbt

level = nbt.readFile('level.dat')
print(level['Data']['LevelName'])
level['Data']['LevelName'] += 'EX'
nbt.writeFile('level2.dat', level)