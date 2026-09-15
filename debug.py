import glob
for fname in glob.glob('*.py'):
    try:
        open(fname, encoding='utf-8').read()
    except UnicodeDecodeError as e:
        print(fname, '->', e)
