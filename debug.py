import subprocess

p = subprocess.Popen(
    ['./xiangqi_ai.exe'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    text=True, encoding='utf-8'
)
p.stdin.write('setboard 2bakab1r/4c4/2n3nc1/p1p1p1p1p/3r5/P1P6/4P1P1P/RC2B1N2/2C6/1N1AKAB1R w\n')
p.stdin.write('side black\n')
p.stdin.write('search\n')
p.stdin.flush()
for line in p.stdout:
    print(line.strip())

"""
side black
setboard 2bakab1r/4c4/2n3nc1/p1p1p1p1p/3r5/P1P6/4P1P1P/RC2B1N2/2C6/1N1AKAB1R w
search
和
side black
move 9 2 7 4
move 2 1 2 4
move 6 0 5 0
move 0 1 2 2
move 9 7 7 6
move 0 0 0 1
move 9 0 7 0
move 0 7 2 6
move 7 7 8 7
move 0 1 4 1
move 6 2 5 2
move 4 1 4 3
move 8 7 8 2
move 2 4 1 4
search

的区别是历史记录，导致少了好多多搜几层看出来好，
"""