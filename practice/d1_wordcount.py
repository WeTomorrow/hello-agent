text = "the cat and the dog and the bird"
words = text.split()
print(words)
counts = {}
print(counts)
for w in words:
    if w in counts:
        counts[w] = counts[w]+1
    else:
        counts[w] =1
print(counts)

items = sorted(counts.items(), key=lambda x: x[1], reverse=True)

for word, cnt in items[:5]:
    print(f"{word}: {cnt}")