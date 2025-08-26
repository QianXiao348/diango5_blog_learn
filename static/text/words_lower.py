inputfile= r'E:\Vscode_code\Py_Backend_Development\django5_blog\static\text\Sensitive_words_lower.txt'
outputfile=r'E:\Vscode_code\Py_Backend_Development\django5_blog\static\text\Sensitive_words_merge.txt'

with open(inputfile, 'r', encoding='utf-8', errors='ignore') as f:
    words = [line.strip() for line in f if line.strip()]

word_lower = sorted(set(w.lower() for w in words))

with open(outputfile, 'w', encoding='utf-8') as f:
    f.write('\n'.join(word_lower))
