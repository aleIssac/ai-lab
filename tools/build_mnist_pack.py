"""把 MNIST parquet 转成 ConvNetJS demo 需要的数据包格式。

ConvNetJS 的 mnist/autoencoder demo 期望：
    demo/mnist/mnist_batch_0.png .. mnist_batch_19.png   训练集，每张 3000 个样本
    demo/mnist/mnist_batch_20.png                        测试集，10000 个样本
    demo/mnist/mnist_labels.js                           var labels=[...]

拼图规则（见 demo/js/autoencoder.js）：
    图片宽 784、高 N，每个样本占一整行（784 个像素按行优先展开）

用法：
    python tools/build_mnist_pack.py
"""

import io
import os

import numpy as np
import pyarrow.parquet as pq
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "data", "_mnist_src")
OUT_DIR = r"D:\Environment\Server\apps\convnetjs\demo\mnist"

BATCH = 3000
DIM = 28
W = DIM * DIM


def load_parquet(path):
    table = pq.read_table(path)
    n = table.num_rows
    arr = np.zeros((n, W), dtype=np.uint8)
    labels = [0] * n

    images = table.column("image").to_pylist()
    labs = table.column("label").to_pylist()

    for i in range(n):
        raw = images[i]["bytes"]
        img = Image.open(io.BytesIO(raw)).convert("L")
        arr[i] = np.asarray(img, dtype=np.uint8).reshape(-1)
        labels[i] = int(labs[i])

    print(f"  读取 {os.path.basename(path)}: {n} 张")
    return arr, labels


def save_batch(arr, path):
    """arr: (N, 784) -> 保存为 宽784 高N 的灰度 PNG"""
    Image.fromarray(arr, mode="L").save(path, optimize=True)
    size = os.path.getsize(path) / 1024 / 1024
    print(f"  {os.path.basename(path)}  {arr.shape[0]} 样本  {size:.1f} MB")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("[1/3] 读取训练集")
    train_x, train_y = load_parquet(os.path.join(SRC_DIR, "train.parquet"))
    print("[2/3] 读取测试集")
    test_x, test_y = load_parquet(os.path.join(SRC_DIR, "test.parquet"))

    print("[3/3] 生成拼图")
    n_train = train_x.shape[0]
    n_batch = n_train // BATCH

    for b in range(n_batch):
        chunk = train_x[b * BATCH:(b + 1) * BATCH]
        save_batch(chunk, os.path.join(OUT_DIR, f"mnist_batch_{b}.png"))

    save_batch(test_x, os.path.join(OUT_DIR, f"mnist_batch_{n_batch}.png"))

    labels = train_y + test_y
    label_path = os.path.join(OUT_DIR, "mnist_labels.js")
    with open(label_path, "w", encoding="utf-8") as f:
        f.write("var labels=[" + ",".join(str(v) for v in labels) + "];")

    print(f"\n完成：{n_batch} 个训练 batch + 1 个测试 batch")
    print(f"标签文件：{label_path}（{len(labels)} 个）")


if __name__ == "__main__":
    main()
