import io
p = r'C:\\Users\\laiki\\.dsh\\workspace\\tackshot\\docs\\VERIFY.md'
v = io.open(p, encoding='utf-8').read()
add = io.open(r'C:\\Users\\laiki\\.dsh\\workspace\\tackshot\\tools\\doc_v24.txt', encoding='utf-8').read()
if '## 24.' not in v:
    io.open(p, 'w', encoding='utf-8').write(v + add)
print('verify updated')