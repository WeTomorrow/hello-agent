import sys

if len(sys.argv)<2:
    print("没传参")
    sys.exit(1)

name = sys.argv[1]      # ← 就是这一行
print(name)


try:
    with open(name,"r",encoding="utf-8") as f:
        text = f.read()
except:
    print("打开文件失败")
    sys.exit(1)

print("字符数：", len(text))
print("行  数：", len(text.splitlines()))
print("词  数：", len(text.split()))

counts = {}
for w in text.lower().split():
    if w in counts:
        counts[w] = counts[w]+1
    else:
        counts[w] = 1

items = sorted(counts.items(), key=lambda x: x[1], reverse=True)


top10 = items[:10]
max_count = top10[0][1]     # 第一名肯定最大，直接取
for word, count in top10:
    length = int(count / max_count * 30)    # 最长 30 格
    bar = "█" * length
    print(f"  {word:<20} {bar} {count}")

